#!/usr/bin/env python3
"""Единая обвязка платформы: адреса, токен, запрос, разбор ответа и потока.

ЗАЧЕМ ОТДЕЛЬНЫМ МОДУЛЕМ. Этот код жил внутри `deploy_edition.py`, и когда издания
удалили (17.08.2026), сломался живой инструмент выкладки страничных продуктов — он
импортировал транспорт оттуда. Общая обвязка не должна жить внутри частного
инструмента: удаление продукта не имеет права ломать чужую выкладку.

Что здесь:
  ОС, ЯДРО   — адреса; путей в единственном числе, как требует канон
  токен()    — из ~/.extella/*.txt или config.json; в лог не печатается
  запрос()   — json или multipart, ошибку возвращает кодом, а не исключением
  как_json() — разбор с honest-отказом вместо загадочного stacktrace
  из_потока() — SSE: событие done; код != 200 — это ОТВЕТ, а не обрыв

    python3 tools/platform_client.py --selftest
"""

import json
import pathlib
import urllib.error
import urllib.request
import uuid


ОС = "https://os.extella.ai"
ЯДРО = "https://api.extella.ai"
КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent


class Отказ(Exception):
    """Отказ, который называет причину и что делать дальше."""


# --- доступ -----------------------------------------------------------------

def токен() -> str:
    for путь, поле in ((pathlib.Path.home() / ".extella" / "os_token.txt", None),
                       (pathlib.Path.home() / ".extella" / "api_token.txt", None),
                       (pathlib.Path.home() / "extella_wizard" / "app" / "config.json", "json")):
        if not путь.exists():
            continue
        текст = путь.read_text().strip()
        if поле == "json":
            d = json.loads(текст)
            for k in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
                if d.get(k):
                    return str(d[k])
        elif текст:
            return текст
    raise Отказ(
        "нет токена Extella на этой машине: не нашёл ни ~/.extella/os_token.txt, ни "
        "~/.extella/api_token.txt, ни extella_wizard/app/config.json. На macOS файл "
        "пишет само приложение при входе — если оно открыто, а файла нет, проверь, "
        "что вошёл под нужным аккаунтом. На Windows нынешняя сборка токен на диск НЕ "
        "пишет (кладёт только device.txt) — файл нужно засеять один раз; «открой "
        "приложение» тут не поможет, оно уже открыто. Значение токена в лог не "
        "печатать.")


def запрос(база, путь, *, тело=None, поля=None, файлы=None, заголовки=None, метод=None, таймаут=180):
    з = {"X-Extella-Token": токен()}
    з.update(заголовки or {})
    данные = None
    if тело is not None:
        данные = json.dumps(тело).encode()
        з["Content-Type"] = "application/json"
    elif поля is not None or файлы is not None:
        граница = uuid.uuid4().hex
        куски = []
        for k, v in (поля or {}).items():
            куски.append(f"--{граница}\r\nContent-Disposition: form-data; "
                         f'name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, п in (файлы or {}).items():
            п = pathlib.Path(п)
            куски.append(f"--{граница}\r\nContent-Disposition: form-data; "
                         f'name="{k}"; filename="{п.name}"\r\n'
                         f"Content-Type: application/octet-stream\r\n\r\n".encode()
                         + п.read_bytes() + b"\r\n")
        куски.append(f"--{граница}--\r\n".encode())
        данные = b"".join(куски)
        з["Content-Type"] = f"multipart/form-data; boundary={граница}"
    r = urllib.request.Request(база + путь, data=данные, headers=з,
                               method=метод or ("POST" if данные else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=таймаут) as о:
            текст = о.read().decode()
            return о.status, текст
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        raise Отказ(f"не дошёл до платформы ({e}). Проверь сеть и повтори")


def как_json(текст, что="ответ"):
    try:
        return json.loads(текст)
    except Exception:
        raise Отказ(f"{что} пришёл не в JSON: {текст[:160]}")


def из_потока(текст, что="публикация", код=200):
    """SSE-поток: берём событие done, а на error честно падаем.

    Отказ платформы (код != 200) приходит сюда обычным телом и раньше терялся:
    поток без «done» мы объясняли обрывом, а на деле это был честный ответ
    «At least one tag is required». Причину теперь видно сразу.
    """
    if код != 200:
        raise Отказ(f"{что}: платформа отказала ({код}) — {текст[:200]}")
    итог = None
    for строка in текст.split("\n"):
        строка = строка.strip()
        if not строка.startswith("data:"):
            continue
        с = как_json(строка[5:].strip(), что)
        if с.get("type") == "error":
            raise Отказ(f"{что} не прошла: {с.get('message') or с}")
        if с.get("type") == "done":
            итог = с
    if итог is None:
        raise Отказ(f"{что}: платформа не прислала завершение. Проверь состояние чтением, "
                    f"прежде чем повторять — повтор создаст дубль")
    return итог


def _selftest() -> int:
    """Проверяем разбор ответов: сеть не нужна, а именно тут были дорогие ошибки."""
    провалы = []

    def случай(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка platform_client:")

    # 1. Поток с событием done разбирается.
    поток = 'data: {"type":"progress"}\n\ndata: {"type":"done","listing_id":"L"}\n'
    случай("событие done находится", из_потока(поток)["listing_id"] == "L")

    # 2. Обрыв без done — отказ, а не успех.
    try:
        из_потока('data: {"type":"progress"}\n')
        случай("обрыв потока не считается успехом", False)
    except Отказ:
        случай("обрыв потока не считается успехом", True)

    # 3. Код != 200 — это ОТВЕТ платформы, и причина обязана быть в тексте отказа.
    #    Раньше он терялся: обёртка объясняла отказ обрывом, и четыре продукта
    #    молча перестали обновляться (H23).
    try:
        из_потока('{"detail":"At least one tag is required"}', "проба", 400)
        случай("отказ платформы называет причину", False)
    except Отказ as e:
        случай("отказ платформы называет причину", "tag is required" in str(e))

    # 4. Не-JSON не роняет стеком, а объясняет.
    try:
        как_json("<html>502</html>", "ответ витрины")
        случай("не-JSON отвергается понятно", False)
    except Отказ as e:
        случай("не-JSON отвергается понятно", "не в JSON" in str(e))

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
