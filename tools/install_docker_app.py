#!/usr/bin/env python3
"""Docker-трек установщика: серверное приложение → контейнер → окно ОС.

ЗАЧЕМ ВТОРОЙ ТРЕК. Добыча спроса 19.08.2026 показала: по звёздной массе ≈65%
желанных приложений — серверный docker-класс (Immich, Vaultwarden, Jellyfin,
Stirling-PDF), браузерная статика — ≈6%. Браузерный конвейер ловит хвост спроса;
этот трек открывает голову. Решение Анвара 19.08, первый пациент — Uptime Kuma.

Чем docker-приложение отличается от браузерного В НАШИХ ПРАВИЛАХ:
  * слушает ТОЛЬКО 127.0.0.1 — compose пишется так, что порт наружу не торчит;
  * данные живут В ТОМЕ рядом с compose (~/extella-cabinet/docker/<slug>/данные) —
    видны как файлы, попадают в бэкап, переживают пересоздание контейнера;
  * перезапуск — не обещание, а ШАГ УСТАНОВКИ: контейнер перезапускается и
    обязан ответить снова, иначе установка не считается состоявшейся;
  * подмену хранилища не вставляем — страницы отдаёт контейнер, мы их не трогаем.
    Отсюда честная граница: в песочнице окна ОС серверное приложение может не
    работать; полоска окна предложит «Открыть отдельным окном» — для серверного
    класса это штатный путь, а не костыль;
  * первичную настройку (пароль администратора) делает ВЛАДЕЛЕЦ: агент не
    заводит аккаунты и не выбирает пароли даже в локальном контейнере.

    python3 tools/install_docker_app.py --образ louislam/uptime-kuma:1 \\
        --slug uptime-kuma --имя "Сторож" --порт-внутри 3001 --том /app/data \\
        --лицензия https://raw.githubusercontent.com/louislam/uptime-kuma/master/LICENSE
    python3 tools/install_docker_app.py --selftest
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from install_github_app import (Отказ, КОРЕНЬ, шаг, свободный_порт,  # noqa: E402
                                взять_лицензию, прогнать)

ДОМ = pathlib.Path.home()
КАБИНЕТ = ДОМ / "extella-cabinet"
ГНЕЗДО = КАБИНЕТ / "docker"


def plist_прокси(slug: str, порт: int, внутренний: int) -> str:
    """Автозапуск прокси-раздачи. Окно ОС — песочница: страницы контейнера без
    шима умирают о запертое хранилище (белый Сторож, 20.08.2026), а «отдельное
    окно» Электрона наследует ту же песочницу. Поэтому наружу смотрит НАШ
    сервер: проксирует контейнер и вшивает шим в HTML на лету."""
    питон = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    арг = "".join(f"<string>{x}</string>" for x in (
        питон, str(КАБИНЕТ / "cabinet_server.py"),
        "--папка", str(ГНЕЗДО / slug), "--порт", str(порт),
        "--имя", slug, "--данные", str(КАБИНЕТ / "данные"),
        "--прокси-на", str(внутренний), "--шим", str(КАБИНЕТ / "storage_shim.html")))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
            '"-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f'<plist version="1.0"><dict><key>Label</key><string>ai.extella.{slug}</string>'
            f'<key>ProgramArguments</key><array>{арг}</array>'
            '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>'
            f'<key>StandardErrorPath</key><string>{КАБИНЕТ / (slug + ".log")}</string>'
            '</dict></plist>')


def докер_живой() -> str:
    итог = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                          capture_output=True, text=True)
    if итог.returncode != 0:
        raise Отказ("docker-демон не отвечает. Открыть Docker Desktop: open -a Docker "
                    "— и повторить через полминуты")
    return итог.stdout.strip()


def собрать_compose(образ: str, slug: str, порт: int, порт_внутри: int,
                    тома: list[str] | None, среда: list[str] | None = None) -> str:
    """Compose-файл. Каждая строка здесь — правило, а не вкус.

    127.0.0.1 в ports: контейнер, торчащий на 0.0.0.0, раздаёт приложение всей
    сети вокруг — у чужого ноутбука в том же кафе появляется ваш сторож.
    restart: unless-stopped: переживает ребут Мака вместе с Docker Desktop —
    LaunchAgent этому классу не нужен.
    Томов может быть несколько (tududi: БД и вложения раздельно) — каждый
    ложится подпапкой ./данные/<имя последнего колена пути>.
    Среда пишется в отдельный файл .env, не в compose: там живут секреты
    (session-ключи) и ПАРОЛЬ ВЛАДЕЛЬЦА, который владелец вписывает сам —
    агент паролей не выбирает. Compose ссылается на .env через env_file.
    """
    строки = [
        "# Собрано установщиком Extella. Править можно; переустановка перепишет.",
        "services:",
        f"  {slug}:",
        f"    image: {образ}",
        f"    container_name: extella-{slug}",
        "    restart: unless-stopped",
        "    ports:",
        f"      - \"127.0.0.1:{порт}:{порт_внутри}\"",
    ]
    if тома:
        строки.append("    volumes:")
        for т in тома:
            имя = "данные" if len(тома) == 1 else т.rstrip("/").split("/")[-1] or "данные"
            строки.append(f"      - ./данные/{имя}:{т}" if len(тома) > 1
                          else f"      - ./данные:{т}")
    if среда:
        строки.append("    env_file: [.env]")
    return "\n".join(строки) + "\n"


def компоуз(папка: pathlib.Path, *команда: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *команда], cwd=папка,
                          capture_output=True, text=True, timeout=300)


def ждать_порт(порт: int, секунд: int = 90) -> float:
    """Ждать, пока приложение внутри контейнера действительно поднимется.

    «Контейнер запущен» и «приложение отвечает» — разные события: у Кумы между
    ними миграции базы. Меряем время честно — оно пойдёт в карточку продукта.
    """
    начало = time.time()
    while time.time() - начало < секунд:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{порт}/", timeout=3) as о:
                if о.status < 500:
                    return time.time() - начало
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1.5)
    raise Отказ(f"приложение не ответило на 127.0.0.1:{порт} за {секунд} с — "
                f"смотреть: docker compose logs (в {ГНЕЗДО})")


def работа(образ: str, slug: str, имя: str, порт_внутри: int,
           том: list[str] | None, лицензия: str, порт: int | None, сухой: bool,
           глиф: str = "app-window", среда: list[str] | None = None) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        raise Отказ("slug — только строчная латиница, цифры и дефис")
    порт = порт or свободный_порт()
    папка = ГНЕЗДО / slug
    издание = КОРЕНЬ / "editions" / slug
    print(f"DOCKER-ПРИЛОЖЕНИЕ: {образ}\n  продукт «{имя}» · slug {slug} · порт {порт}")

    шаг(1, "Проверяю докер")
    if сухой:
        print("  спросил бы docker info")
    else:
        print(f"  ✓ демон {докер_живой()}")

    внутренний = порт + 10000       # контейнер живёт на внутреннем, наружу — прокси
    шаг(2, "Пишу compose и поднимаю контейнер (на внутреннем порту, за прокси)")
    compose = собрать_compose(образ, slug, внутренний, порт_внутри, том, среда)
    if сухой:
        print("  " + compose.replace("\n", "\n  "))
    else:
        папка.mkdir(parents=True, exist_ok=True)
        (папка / "compose.yaml").write_text(compose)
        if среда:
            env = папка / ".env"
            # Один раз: в .env живёт пароль, вписанный ВЛАДЕЛЬЦЕМ, —
            # переустановка не имеет права его затирать.
            if env.exists():
                print("  .env уже существует — не трогаю (там ваши значения)")
            else:
                env.write_text("\n".join(среда) + "\n")
                env.chmod(0o600)
                print(f"  .env создан ({len(среда)} переменных, права 600)")
        итог = компоуз(папка, "up", "-d")
        if итог.returncode != 0:
            raise Отказ(f"compose up не прошёл: {(итог.stderr or '').strip()[:300]}")
        сек = ждать_порт(внутренний)
        print(f"  ✓ контейнер отвечает на 127.0.0.1:{внутренний} через {сек:.0f} с")

    шаг(2.5, "Ставлю прокси с шимом — окно ОС иначе белое")
    if сухой:
        print(f"  поднял бы прокси {порт} → {внутренний} с шимом в HTML")
    else:
        import shutil
        shutil.copy(СЮДА / "cabinet_server.py", КАБИНЕТ / "cabinet_server.py")
        shutil.copy(СЮДА.parent / "templates" / "storage_shim.html",
                    КАБИНЕТ / "storage_shim.html")
        plist = ДОМ / "Library" / "LaunchAgents" / f"ai.extella.{slug}.plist"
        plist.write_text(plist_прокси(slug, порт, внутренний))
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
        итог = subprocess.run(["launchctl", "load", str(plist)],
                              capture_output=True, text=True)
        if итог.returncode != 0:
            raise Отказ(f"прокси не поднялся: {итог.stderr[:200]}")
        сек = ждать_порт(порт)
        print(f"  ✓ прокси {порт} → {внутренний} жив, шим вшивается в HTML")

    шаг(3, "Проба перезапуском — установка без неё не считается")
    if сухой:
        print("  перезапустил бы контейнер и дождался ответа")
    else:
        итог = компоуз(папка, "restart")
        if итог.returncode != 0:
            raise Отказ(f"перезапуск не прошёл: {(итог.stderr or '').strip()[:200]}")
        сек = ждать_порт(внутренний)
        print(f"  ✓ пережил перезапуск, снова отвечает через {сек:.0f} с")

    шаг(4, "Собираю лицензию")
    if not лицензия:
        print("  ⚠ адрес лицензии не задан — выкладывать без неё нельзя")
    elif сухой:
        print(f"  взял бы {лицензия}")
    else:
        издание.mkdir(parents=True, exist_ok=True)
        взять_лицензию(лицензия, издание / "ЛИЦЕНЗИЯ_ПРИЛОЖЕНИЯ.txt")
        print(f"  ✓ лицензия сохранена в editions/{slug}/")

    шаг(5, "Иконка, карточка, окно")
    if сухой:
        print(f"  создал бы editions/{slug}/: icon.png, app.json, listing.json, index.html")
    else:
        издание.mkdir(parents=True, exist_ok=True)
        if not (издание / "icon.png").exists():
            print("  " + прогнать("bronze_icon.py", глиф, str(издание / "icon.png")).strip())
        (издание / "app.json").write_text(json.dumps({
            "имя": имя, "порт": порт, "путь": "/", "проба": "/",
            "подпись": f"адрес: localhost:{порт} · серверное приложение в контейнере "
                       f"на вашем компьютере, данные — файлами в томе",
        }, ensure_ascii=False, indent=2) + "\n")
        if not (издание / "listing.json").exists():
            (издание / "listing.json").write_text(json.dumps({
                "name": имя,
                "описание": "ЗАПОЛНИТЬ: что делает и почему у себя лучше, чем в облаке.",
                "теги": ["приложение", "ЗАПОЛНИТЬ"],
                "иконка": "icon.png", "версия": "0.1.0", "цена": 0,
                "состояние": "черновик", "права": [],
                "границы": "ЗАПОЛНИТЬ: что не работает во встроенном окне ОС",
            }, ensure_ascii=False, indent=2) + "\n")
        print("  " + прогнать("make_local_app_page.py", str(издание)).strip())

    print("\n" + "─" * 62)
    if сухой:
        print("СУХОЙ ПРОГОН ОКОНЧЕН — ничего не изменено")
        return 0
    print("ГОТОВО. Дальше — руками, потому что машине это решать нельзя:")
    print(f"  1. открыть http://127.0.0.1:{порт} и пройти первичную настройку —")
    print("     пароль администратора задаёт ВЛАДЕЛЕЦ, не агент")
    print(f"  2. заполнить editions/{slug}/listing.json и выложить предрелизом")
    print("  3. проверить, что Docker Desktop стартует при входе в систему —")
    print("     иначе после ребута контейнер ждёт запуска докера")
    return 0


def selftest() -> int:
    ошибки = []

    п = plist_прокси("проба", 34799, 44799)
    if "--прокси-на" not in п or "44799" not in п or "storage_shim" not in п:
        ошибки.append("plist прокси без шима — окно ОС снова будет белым")
    else:
        print("  ✓ наружу смотрит прокси с шимом: окно ОС получает страницы с подменой")

    c = собрать_compose("пример/образ:1", "проба", 34799, 3001, ["/app/data"])
    if '"127.0.0.1:34799:3001"' not in c:
        ошибки.append("порт не привязан к 127.0.0.1 — контейнер торчал бы в сеть")
    elif "0.0.0.0" in c:
        ошибки.append("в compose пролез 0.0.0.0")
    else:
        print("  ✓ порт слушает только 127.0.0.1 — соседям по сети приложения не видно")

    if "restart: unless-stopped" not in c:
        ошибки.append("нет политики перезапуска — ребут Мака убьёт приложение")
    else:
        print("  ✓ переживает ребут: restart unless-stopped, LaunchAgent не нужен")

    if "./данные:/app/data" not in c:
        ошибки.append("том данных не примонтирован — пересоздание контейнера стёрло бы работу")
    else:
        print("  ✓ данные — файлами рядом с compose, переживают пересоздание")

    без_тома = собрать_compose("пример:1", "проба", 1, 2, None)
    два_тома = собрать_compose("п:1", "проба", 1, 2, ["/app/db", "/app/uploads"])
    if "./данные/db:/app/db" not in два_тома or "./данные/uploads:/app/uploads" not in два_тома:
        ошибки.append("несколько томов не раскладываются подпапками ./данные/")
    else:
        print("  ✓ несколько томов — подпапками ./данные/, ничего не слипается")
    с_средой = собрать_compose("п:1", "проба", 1, 2, None, ["KEY=секрет"])
    if "env_file: [.env]" not in с_средой:
        ошибки.append("среда не подключена через env_file")
    elif "секрет" in с_средой:
        ошибки.append("СЕКРЕТ ПРОЛЕЗ В COMPOSE — секреты живут только в .env (600)")
    else:
        print("  ✓ среда уходит в .env, секреты в compose не пролезают")
    if "volumes" in без_тома:
        ошибки.append("пустой том попал в compose")
    else:
        print("  ✓ приложение без состояния собирается без тома")

    try:
        работа("х:1", "Плохой_Слаг", "х", 1, None, "", None, True)
        ошибки.append("кривой slug прошёл")
    except Отказ:
        print("  ✓ кривой slug отвергается до каких-либо действий")

    for и in ("make_icon.py", "make_local_app_page.py"):
        if not (СЮДА / и).exists():
            ошибки.append(f"нет инструмента {и}")
    if not [о for о in ошибки if "инструмента" in о]:
        print("  ✓ инструменты шагов на месте")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Docker-приложение → контейнер → окно ОС")
    р.add_argument("--образ")
    р.add_argument("--slug")
    р.add_argument("--имя")
    р.add_argument("--порт-внутри", dest="порт_внутри", type=int)
    р.add_argument("--том", action="append", default=None,
                   help="путь тома в контейнере; можно несколько раз")
    р.add_argument("--среда", action="append", default=None,
                   help="KEY=VALUE в .env (секреты и учётка владельца); можно несколько раз")
    р.add_argument("--лицензия", default="")
    р.add_argument("--порт", type=int, default=None)
    р.add_argument("--глиф", default="app-window",
                   help="Lucide-глиф для плитки Bronze Engraved")
    р.add_argument("--сухой", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    if not (а.образ and а.slug and а.имя and а.порт_внутри):
        р.print_help()
        return 1
    try:
        return работа(а.образ, а.slug, а.имя, а.порт_внутри, а.том,
                      а.лицензия, а.порт, а.сухой, а.глиф, а.среда)
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
