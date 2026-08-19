#!/usr/bin/env python3
"""Приложение с GitHub → продукт в магазине ОС, одной командой до предрелиза.

ЗАЧЕМ. Путь из готовой сборки в магазин состоит из десяти шагов, и шесть из них
уже машинные — но их надо помнить и запускать по очереди. Один пропущенный шаг
даёт тихую поломку: приложение теряет работу человека, звонит наружу или выходит
без лицензии. Замер 16.08.2026 на первом приложении (Доска схем): вечер на восемь
классов поломки; всё, что здесь собрано, — цена того вечера.

Что делает по шагам:
  1. выбирает свободный порт и раскладывает раздачу с хранилищем на диске;
  2. снимает чужой перехватчик страниц (он захватывает порт и отдаёт старую копию);
  3. вырезает звонки наружу — счётчики и чужие шрифты;
  4. вставляет подмену хранилища: в окне ОС закрыты хранилище, cookie и базы;
  5. ставит автозапуск при входе и проверяет, что он поднимается;
  6. собирает лицензии (сборки с GitHub приезжают без файла LICENSE);
  7. делает иконку, карточку продукта и страницу-окно;
  8. гоняет гейт витрины и входную проверку.

Выкладку НЕ делает: для неё есть tools/deploy_page_product.py, а Publish жмёт владелец.

    python3 tools/install_github_app.py ~/extella-plugins/приложение \\
        --slug board --имя "Доска схем" \\
        --лицензия https://raw.githubusercontent.com/excalidraw/excalidraw/master/LICENSE \\
        --проект Excalidraw
    python3 tools/install_github_app.py <папка> --slug X --имя "Y" --сухой
    python3 tools/install_github_app.py --selftest

Коды выхода: 0 — готово к выкладке, 1 — отказ с названной причиной.
"""

import argparse
import json
import pathlib
import re
import socket
import subprocess
import sys
import urllib.request

СЮДА = pathlib.Path(__file__).resolve().parent
КОРЕНЬ = СЮДА.parent
ДОМ = pathlib.Path.home()
КАБИНЕТ = ДОМ / "extella-cabinet"
ПОРТ_ОТ, ПОРТ_ДО = 34786, 34850
ФАЙЛЫ_ПЕРЕХВАТЧИКА = ("service-worker.js", "sw.js", "serviceworker.js")

PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.extella.%SLUG%</string>

    <!-- %ИМЯ% в Extella OS: раздача только на 127.0.0.1, работа человека ложится
         файлом на диск.

         ПОЧЕМУ КОПИЯ СЕРВЕРА, А НЕ КАНОН В «ДОКУМЕНТАХ». macOS запрещает фоновым
         службам читать ~/Documents — служба падает с «Operation not permitted».
         Копия сверяется с каноном отпечатком, см. ~/extella-cabinet/ПРОВЕРКА.md

         ПОЧЕМУ ПОЛНЫЙ ПУТЬ К PYTHON. /usr/bin/python3 подменяется на Python из
         Xcode и ведёт себя иначе. -->
    <key>ProgramArguments</key>
    <array>
        <string>%PYTHON%</string>
        <string>%СЕРВЕР%</string>
        <string>--папка</string>
        <string>%ПАПКА%</string>
        <string>--порт</string>
        <string>%ПОРТ%</string>
        <string>--имя</string>
        <string>%SLUG%</string>
        <string>--данные</string>
        <string>%ДАННЫЕ%</string>
    </array>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>%ЖУРНАЛ%</string>
    <key>StandardErrorPath</key>
    <string>%ЖУРНАЛ%</string>
</dict>
</plist>
"""


class Отказ(Exception):
    pass


def шаг(n: int, текст: str) -> None:
    print(f"\n[{n}] {текст}")


def свободный_порт() -> int:
    """Первый свободный порт диапазона.

    Порт выбирается заново для каждого приложения не из вежливости: чужой
    перехватчик страниц привязан к адресу ВМЕСТЕ С ПОРТОМ и переживает удаление
    своих файлов. Новый порт — гарантированно чистый лист.
    """
    for порт in range(ПОРТ_ОТ, ПОРТ_ДО):
        with socket.socket() as с:
            с.settimeout(0.25)
            if с.connect_ex(("127.0.0.1", порт)) != 0:
                return порт
    raise Отказ(f"свободных портов в диапазоне {ПОРТ_ОТ}–{ПОРТ_ДО} нет")


def питон() -> str:
    for п in ("/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
              "/usr/local/bin/python3", "/opt/homebrew/bin/python3"):
        if pathlib.Path(п).exists():
            return п
    raise Отказ("не нашёл питон вне Xcode: автозапуск с /usr/bin/python3 ненадёжен")


def прогнать(имя_инструмента: str, *аргументы: str) -> str:
    итог = subprocess.run([sys.executable, str(СЮДА / имя_инструмента), *аргументы],
                          capture_output=True, text=True)
    вывод = (итог.stdout or "") + (итог.stderr or "")
    if итог.returncode != 0:
        raise Отказ(f"{имя_инструмента} отказал:\n{вывод.strip()[:600]}")
    return вывод


def снять_перехватчик(папка: pathlib.Path) -> list[str]:
    снято = []
    for имя in ФАЙЛЫ_ПЕРЕХВАТЧИКА:
        ф = папка / имя
        if ф.exists():
            ф.rename(папка / (имя + ".снято"))
            снято.append(имя)
    return снято


def взять_лицензию(адрес: str, куда: pathlib.Path) -> None:
    """Текст лицензии берём у первоисточника. Угадывать её нельзя."""
    try:
        with urllib.request.urlopen(адрес, timeout=25) as о:
            текст = о.read().decode("utf-8", "replace")
    except OSError as е:
        raise Отказ(f"не смог взять лицензию по адресу {адрес}: {е}")
    if len(текст.strip()) < 200:
        raise Отказ(f"по адресу {адрес} лежит подозрительно короткий текст "
                    f"({len(текст.strip())} знаков) — это не похоже на лицензию")
    куда.write_text(текст)


def автозапуск(slug: str, папка: pathlib.Path, порт: int, сухой: bool) -> pathlib.Path:
    сервер = КАБИНЕТ / "cabinet_server.py"
    plist = ДОМ / "Library/LaunchAgents" / f"ai.extella.{slug}.plist"
    текст = PLIST
    for метка, значение in (("%SLUG%", slug), ("%ИМЯ%", slug), ("%PYTHON%", питон()),
                            ("%СЕРВЕР%", str(сервер)), ("%ПАПКА%", str(папка)),
                            ("%ПОРТ%", str(порт)), ("%ДАННЫЕ%", str(КАБИНЕТ / "данные")),
                            ("%ЖУРНАЛ%", str(КАБИНЕТ / f"{slug}.log"))):
        текст = текст.replace(метка, значение)
    if сухой:
        return plist
    КАБИНЕТ.mkdir(parents=True, exist_ok=True)
    (КАБИНЕТ / "данные").mkdir(parents=True, exist_ok=True)
    if not сервер.exists():
        канон = КОРЕНЬ / "tools" / "cabinet_server.py"
        сервер.write_text(канон.read_text())
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(текст)
    subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
    subprocess.run(["launchctl", "load", str(plist)], capture_output=True)
    return plist


def живой(порт: int) -> bool:
    import time
    for _ in range(10):
        with socket.socket() as с:
            с.settimeout(0.3)
            if с.connect_ex(("127.0.0.1", порт)) == 0:
                return True
        time.sleep(0.4)
    return False


def работа(папка: pathlib.Path, slug: str, имя: str, лицензия: str, проект: str,
           порт: int | None, сухой: bool) -> int:
    if not (папка / "index.html").exists():
        raise Отказ("в папке нет index.html — это не готовая веб-сборка")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        raise Отказ("slug — только строчная латиница, цифры и дефис")

    издание = КОРЕНЬ / "editions" / slug
    порт = порт or свободный_порт()
    print(f"ПРИЛОЖЕНИЕ: {папка}\n  продукт «{имя}» · slug {slug} · порт {порт}")
    if сухой:
        print("\n  СУХОЙ ПРОГОН: ничего не меняю, показываю план")

    шаг(1, "Снимаю чужой перехватчик страниц")
    if сухой:
        есть = [и for и in ФАЙЛЫ_ПЕРЕХВАТЧИКА if (папка / и).exists()]
        print(f"  снял бы: {', '.join(есть) or 'нечего'}")
    else:
        снято = снять_перехватчик(папка)
        print(f"  снято: {', '.join(снято) or 'нечего снимать'}")

    шаг(2, "Вырезаю звонки наружу")
    print("  " + прогнать("cut_outbound.py", str(папка / "index.html"),
                          *(["--показать"] if сухой else [])).strip().replace("\n", "\n  ")[:900])

    шаг(3, "Вставляю подмену хранилища (в песочнице закрыты хранилище, cookie и базы)")
    if сухой:
        print("  вставил бы templates/storage_shim.html после объявления кодировки")
    else:
        прогнать("inject_probe.py", "--снять", str(папка / "index.html"))
        print("  " + прогнать("inject_probe.py", str(папка / "index.html")).strip())

    шаг(4, "Ставлю раздачу и автозапуск при входе")
    plist = автозапуск(slug, папка, порт, сухой)
    if сухой:
        print(f"  создал бы {plist.name} и поднял службу ai.extella.{slug}")
    else:
        if not живой(порт):
            raise Отказ(f"служба не поднялась на порту {порт} — смотреть "
                        f"{КАБИНЕТ / (slug + '.log')}")
        print(f"  ✓ служба ai.extella.{slug} слушает 127.0.0.1:{порт}")

    шаг(5, "Собираю лицензии")
    if not лицензия:
        print("  ⚠ адрес лицензии не задан (--лицензия) — файл ЛИЦЕНЗИИ.md НЕ собран.")
        print("    Почти все свободные лицензии требуют сохранять текст в копиях:")
        print("    без него выкладывать нельзя.")
    elif сухой:
        print(f"  взял бы текст с {лицензия} и собрал ЛИЦЕНЗИИ.md")
    else:
        издание.mkdir(parents=True, exist_ok=True)
        своя = издание / "ЛИЦЕНЗИЯ_ПРИЛОЖЕНИЯ.txt"
        взять_лицензию(лицензия, своя)
        print("  " + прогнать("collect_licenses.py", str(папка), "--основная", str(своя),
                              "--имя", проект or имя).strip().replace("\n", "\n  ")[:700])

    шаг(6, "Делаю иконку, карточку и страницу-окно")
    if сухой:
        print(f"  создал бы editions/{slug}/: icon.png, app.json, listing.json, index.html")
    else:
        издание.mkdir(parents=True, exist_ok=True)
        if not (издание / "icon.png").exists():
            print("  " + прогнать("make_icon.py", "доска", str(издание / "icon.png")).strip())
        (издание / "app.json").write_text(json.dumps({
            "имя": имя, "порт": порт, "путь": "/",
            "проба": "/index.html",
            "подпись": f"адрес: localhost:{порт} · работа хранится файлом на вашем компьютере",
        }, ensure_ascii=False, indent=2) + "\n")
        карточка = издание / "listing.json"
        if not карточка.exists():
            карточка.write_text(json.dumps({
                "name": имя,
                "описание": "ЗАПОЛНИТЬ: что делает, кому и почему это лучше здесь, "
                            "чем в браузере. От 80 знаков, без повтора имени.",
                "теги": ["приложение", "ЗАПОЛНИТЬ"],
                "иконка": "icon.png", "версия": "0.1.0", "цена": 0,
                "состояние": "черновик", "права": [],
                "границы": "ЗАПОЛНИТЬ: чего приложение НЕ умеет в окне ОС",
            }, ensure_ascii=False, indent=2) + "\n")
            print(f"  ✓ карточка-заготовка: editions/{slug}/listing.json — заполнить описание,"
                  f" теги и границы")
        print("  " + прогнать("make_local_app_page.py", str(издание)).strip())

    if not сухой:
        # Приложение само знает, где лежит его работа, — человеку выяснять это
        # незачем. Без этой записи каждое новое приложение пришлось бы
        # регистрировать руками, а при пятистах приложениях ручная регистрация
        # ничем не лучше ручной интеграции.
        реестр = pathlib.Path.home() / "extella-cabinet" / "источники.json"
        реестр.parent.mkdir(parents=True, exist_ok=True)
        д = json.loads(реестр.read_text()) if реестр.exists() else {}
        д[slug] = {"файл": str(pathlib.Path.home() / "extella-cabinet" / "данные"
                               / f"{slug}.json"), "имя": имя, "порт": порт}
        реестр.write_text(json.dumps(д, ensure_ascii=False, indent=2))
        print(f"  ✓ приложение записано в реестр источников как «{slug}» — "
              f"его уже можно звать словами:")
        print(f"      python3 tools/скажи.py \"возьми из {slug} и нарисуй на доске\" --учись")

    шаг(7, "Проверяю: входная проверка и гейт витрины")
    print(прогнать("check_local_app.py", str(папка), "--порт", str(порт)).strip()[:1200])
    if not сухой and (издание / "listing.json").exists():
        итог = subprocess.run([sys.executable, str(СЮДА / "check_listing_meta.py"), str(издание)],
                              capture_output=True, text=True)
        print("\n" + (итог.stdout or итог.stderr).strip()[:600])

    print("\n" + "─" * 62)
    if сухой:
        print("СУХОЙ ПРОГОН ОКОНЧЕН — ничего не изменено")
        return 0
    print("ГОТОВО. Дальше — руками, потому что машине это решать нельзя:")
    print(f"  1. заполнить editions/{slug}/listing.json: описание, теги, границы")
    print(f"  2. ПРИЁМКА ГЛАЗАМИ: открыть http://127.0.0.1:{порт}, поработать,")
    print("     закрыть окно, открыть заново — работа на месте")
    print(f"  3. выложить: python3 tools/deploy_page_product.py editions/{slug}")
    print("  4. Publish в магазине — владелец")
    return 0


def selftest() -> int:
    import tempfile
    ошибки = []
    п = свободный_порт()
    print(f"  ✓ свободный порт находится: {п}")
    try:
        питон()
        print("  ✓ питон вне Xcode найден")
    except Отказ as о:
        ошибки.append(str(о))

    with tempfile.TemporaryDirectory() as врем:
        пап = pathlib.Path(врем)
        (пап / "sw.js").write_text("// перехватчик")
        (пап / "index.html").write_text("<!doctype html><meta charset=utf-8><body>ok")
        снято = снять_перехватчик(пап)
        if снято != ["sw.js"] or not (пап / "sw.js.снято").exists():
            ошибки.append("перехватчик не снят")
        else:
            print("  ✓ перехватчик снимается переименованием")

        try:
            работа(pathlib.Path(врем), "нельзя_так", "Имя", "", "", None, True)
            ошибки.append("кривой slug не отвергнут")
        except Отказ:
            print("  ✓ кривой slug отвергается")

        пусто = pathlib.Path(врем) / "пусто"
        пусто.mkdir()
        try:
            работа(пусто, "ok", "Имя", "", "", None, True)
            ошибки.append("папка без index.html не отвергнута")
        except Отказ:
            print("  ✓ папка без index.html отвергается")

    текст = PLIST.replace("%SLUG%", "x").replace("%ИМЯ%", "x").replace("%PYTHON%", "x")
    if "%" in текст.replace("%ПАПКА%", "").replace("%ПОРТ%", "").replace("%ДАННЫЕ%", "") \
            .replace("%ЖУРНАЛ%", "").replace("%СЕРВЕР%", ""):
        ошибки.append("в шаблоне автозапуска остались незаполненные метки")
    else:
        print("  ✓ шаблон автозапуска заполняется целиком")

    for имя in ("cut_outbound.py", "inject_probe.py", "collect_licenses.py",
                "make_icon.py", "make_local_app_page.py", "check_local_app.py",
                "check_listing_meta.py", "cabinet_server.py"):
        if not (СЮДА / имя).exists():
            ошибки.append(f"нет инструмента шага: {имя}")
    if not ошибки:
        print("  ✓ все инструменты шагов на месте")

    if ошибки:
        for о in ошибки:
            print(f"  ✕ {о}")
        print("ИТОГ САМОПРОВЕРКИ: есть отказы")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("папка", nargs="?")
    р.add_argument("--slug", default="")
    р.add_argument("--имя", dest="имя", default="")
    р.add_argument("--лицензия", default="")
    р.add_argument("--проект", default="")
    р.add_argument("--порт", type=int, default=None)
    р.add_argument("--сухой", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    if not (а.папка and а.slug and а.имя):
        р.print_help()
        print("\nнужны: папка со сборкой, --slug и --имя")
        return 1
    try:
        return работа(pathlib.Path(а.папка).expanduser().resolve(), а.slug, а.имя,
                      а.лицензия, а.проект, а.порт, а.сухой)
    except Отказ as о:
        print(f"\nНе установил: {о}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
