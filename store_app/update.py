#!/usr/bin/env python3
"""Обновить страницу приложения «Разработка на Extella» на месте.

Зачем: правка гида не должна требовать новой версии и перепокупки. Платформа
принимает замену страницы у существующей версии (`POST /api/edit-version/{vid}`),
и покупатели видят новый текст при следующем открытии окна.

Использование:
    python3 update.py            — заменить страницу текущей версии
    python3 update.py --status   — показать состояние листинга, ничего не менять

Токен берётся из канонических мест устройства и никуда не печатается.
"""

import json
import mimetypes
import pathlib
import re
import sys
import urllib.request
import uuid

ОС = "https://os.extella.ai"
ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
СТРАНИЦА = ЗДЕСЬ / "index.html"
ПАСПОРТ = ЗДЕСЬ / "listing.json"


def токен() -> str:
    """Канон platform_client: сначала файл доступа, потом конфиг визарда."""
    прямой = pathlib.Path.home() / ".extella" / "api_token.txt"
    if прямой.exists():
        значение = прямой.read_text().strip()
        if значение:
            return значение

    конфиг = pathlib.Path.home() / "extella_wizard" / "app" / "config.json"
    if конфиг.exists():
        данные = json.loads(конфиг.read_text())
        for поле in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
            if данные.get(поле):
                return str(данные[поле])

    mcp = pathlib.Path.home() / ".claude" / "extella_mcp_server.py"
    if mcp.exists():
        найдено = re.search(r'AUTH_TOKEN\s*=\s*["\']([^"\']+)', mcp.read_text())
        if найдено:
            return найдено.group(1)

    отказ(
        "не найден доступ к Extella на этом устройстве: нет файла "
        "~/.extella/api_token.txt. Открой Extella на этой машине один раз — "
        "файл появится сам."
    )


def отказ(что_делать: str):
    print(f"Не получилось: {что_делать}", file=sys.stderr)
    sys.exit(1)


def запрос(метод: str, путь: str, файлы=None):
    заголовки = {"X-Extella-Token": токен()}
    данные = None

    if файлы:
        граница = uuid.uuid4().hex
        куски = []
        for имя, путь_файла in файлы.items():
            тип = mimetypes.guess_type(str(путь_файла))[0] or "application/octet-stream"
            куски.append(
                f"--{граница}\r\n"
                f'Content-Disposition: form-data; name="{имя}"; '
                f'filename="{путь_файла.name}"\r\n'
                f"Content-Type: {тип}\r\n\r\n".encode()
                + путь_файла.read_bytes()
                + b"\r\n"
            )
        куски.append(f"--{граница}--\r\n".encode())
        данные = b"".join(куски)
        заголовки["Content-Type"] = f"multipart/form-data; boundary={граница}"

    запрос_ = urllib.request.Request(ОС + путь, data=данные, headers=заголовки, method=метод)
    try:
        with urllib.request.urlopen(запрос_, timeout=120) as ответ:
            тело = ответ.read().decode()
            return ответ.status, тело
    except urllib.error.HTTPError as ошибка:
        return ошибка.code, ошибка.read().decode()
    except Exception as ошибка:  # сеть, таймаут
        отказ(f"не дошёл до Extella ({ошибка}). Проверь сеть и запусти ещё раз.")


def паспорт() -> dict:
    if not ПАСПОРТ.exists():
        отказ(
            f"нет файла {ПАСПОРТ.name} с номерами листинга. Он создаётся при первой "
            "публикации; если потерялся — возьми listing_id и version_id из "
            "GET /api/my-listings и впиши их сюда."
        )
    return json.loads(ПАСПОРТ.read_text())


def состояние():
    свой = паспорт()
    код, тело = запрос("GET", "/api/my-listings")
    if код != 200:
        отказ(f"витрина ответила {код}. Повтори через минуту.")

    for листинг in json.loads(тело).get("listings", []):
        if листинг["id"] != свой["listing_id"]:
            continue
        видно = "в магазине" if листинг.get("published") else "предрелиз (виден только автору)"
        print(f"«{листинг['name']}» — {видно}")
        for версия in листинг.get("versions", []):
            print(f"  версия {версия['version']}, цена {версия['price_credits']}")
        print(f"  открыть: {ОС}/app-page/{свой['listing_id']}")
        return
    отказ("листинг не найден на аккаунте — возможно, номера в listing.json устарели.")


def обновить():
    свой = паспорт()
    if not СТРАНИЦА.exists():
        отказ(f"нет файла {СТРАНИЦА.name} рядом со скриптом.")

    размер = СТРАНИЦА.stat().st_size
    if размер > 3 * 1024 * 1024:
        отказ(
            f"страница выросла до {размер / 1024 / 1024:.1f} МБ, а лимит одиночного "
            "HTML — 3 МБ. Раздели её на zip-бандл с index.html в корне."
        )

    # Проверка ДО отправки: иначе битый файл успевает уехать покупателям, и только
    # потом мы сообщаем о поломке. Ровно это и случилось на первом прогоне.
    свежая = СТРАНИЦА.read_text()
    маркер = "<title>Разработка на Extella</title>"
    беды = []
    if маркер not in свежая:
        беды.append("нет заголовка страницы — это не тот файл")
    if свежая.count("<section") != свежая.count("</section>"):
        беды.append("разделы не закрыты — файл обрезан")
    if "</html>" not in свежая:
        беды.append("файл кончается раньше времени — обрезан")
    if "{" + "{" in свежая:
        беды.append("в тексте осталась метка подстановки — платформа покажет её значением")
    if беды:
        отказ("страницу не отправил, сначала поправь: " + "; ".join(беды))

    код, тело = запрос("POST", f"/api/edit-version/{свой['version_id']}", {"page": СТРАНИЦА})
    if код != 200:
        отказ(f"витрина ответила {код}: {тело[:200]}")

    # Сверка: платформа обязана отдать ровно то, что мы положили.
    код, отдано = запрос("GET", f"/app-page/{свой['listing_id']}")
    if код != 200:
        отказ(f"страница после замены отдаётся с кодом {код}. Проверь листинг в ОС.")

    if маркер not in отдано:
        отказ("отданная страница не похожа на нашу — замена не применилась.")
    if len(отдано) < len(свежая) * 0.9:
        отказ(
            f"отдано {len(отдано)} символов против {len(свежая)} в файле — "
            "похоже, применилась не эта версия. Повтори через минуту."
        )

    print(f"Страница обновлена: {размер} байт, версия та же — перепокупка не нужна.")
    print("Покупатели увидят новый текст при следующем открытии окна.")


if __name__ == "__main__":
    if "--status" in sys.argv:
        состояние()
    else:
        обновить()
