#!/usr/bin/env python3
"""Входная проверка приложения с GitHub — ДО того, как оно попало в магазин ОС.

ЗАЧЕМ. Чужие веб-приложения ломаются не как попало, а конечным числом способов.
Пока каждое проверяли на глаз, один и тот же класс поломки возвращался снова и
снова — тише всего «работа пропадает молча»: приложение открывается, человек
рисует, закрывает окно, и всё исчезает. Коды ответа 200 и наличие файлов этого
не ловят вовсе.

Проверка отвечает на ОДИН вопрос, тот же, что и приёмка человеком:
    переживает ли работа перезагрузку окна — и где она лежит.

Что делает:
  * смотрит на папку приложения БЕЗ запуска (свой обработчик страниц, внешние
    адреса, признаки хранения) — это дёшево и часть ответов даёт сразу;
  * кладёт рядом страницу-проверку, открывает её вместе с приложением и
    доводит до вердикта: годно / нужна подмена хранилища / в магазин нельзя.

    python3 tools/check_local_app.py ~/extella-plugins/gh_excalidraw_excalidraw
    python3 tools/check_local_app.py <папка> --порт 34785     # уже раздаётся
    python3 tools/check_local_app.py <папка> --снять          # убрать страницу
    python3 tools/check_local_app.py --selftest

Коды выхода: 0 — проверка подготовлена (или самопроверка прошла), 1 — отказ.
"""

import argparse
import pathlib
import re
import shutil
import socket
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent
ШАБЛОН = КОРЕНЬ / "templates" / "app_probe_page.html"
# Латиницей намеренно: кириллица в адресе приезжает процентами и не совпадает.
ИМЯ_СТРАНИЦЫ = "_extella_probe.html"

# Свой обработчик страниц (service worker) перехватывает ВЕСЬ порт и отдаёт свою
# копию любого адреса. Пока он жив, правки в index.html до браузера не доходят —
# и проверка показывает вчерашнее состояние.
ФАЙЛЫ_ОБРАБОТЧИКА = ("service-worker.js", "sw.js", "serviceworker.js")

СВОИ = ("localhost", "127.0.0.1", "0.0.0.0")
# Метки вида rel=canonical ничего не загружают; звонком наружу считаем только эти.
ЗАГРУЖАЮЩИЕ = ("preload", "preconnect", "stylesheet", "dns-prefetch",
               "prefetch", "modulepreload")


def найти_страницу(папка: pathlib.Path) -> pathlib.Path | None:
    for имя in ("index.html", "index.htm"):
        если = папка / имя
        if если.exists():
            return если
    return None


def внешние_адреса(папка: pathlib.Path, предел: int = 12) -> list[str]:
    """Куда приложение полезет в интернет. Обещаем «всё локально» — надо проверять."""
    узлы: dict[str, int] = {}
    файлы = [p for p in папка.rglob("*")
             if p.is_file() and p.suffix.lower() in (".html", ".js", ".css", ".json")
             and ".снято" not in p.name and p.name != ИМЯ_СТРАНИЦЫ]
    for ф in файлы[:400]:                     # хватает, чтобы увидеть класс
        try:
            текст = ф.read_text(errors="ignore")
        except OSError:
            continue
        for адрес in re.findall(r"https?://([A-Za-z0-9.\-]+)", текст):
            if any(адрес.startswith(с) for с in СВОИ):
                continue
            узлы[адрес] = узлы.get(адрес, 0) + 1
    порядок = sorted(узлы.items(), key=lambda п: -п[1])
    return [f"{у} ({н})" for у, н in порядок[:предел]]


def звонит_наружу(страница: pathlib.Path) -> list[str]:
    """Что стартовая страница тянет из интернета САМА, при каждом открытии.

    Отличается от «внешние адреса в коде»: там половина — текст лицензий и имена
    пространств имён. Здесь только живые загрузки: <script src>, <link href>.
    Именно они превращают обещание «всё локально, без интернета» в неправду.
    """
    try:
        т = страница.read_text(errors="ignore")
    except OSError:
        return []
    живые: list[str] = []
    for тег in re.findall(r"<(?:script|link|img|iframe)\b[^>]*>", т, re.I):
        адрес = re.search(r'(?:src|href)\s*=\s*["\']?(https?://[^"\'\s>]+)', тег, re.I)
        if not адрес:
            continue
        url = адрес.group(1)
        if any(f"//{с}" in url for с in СВОИ):
            continue
        # <link> бывает и просто меткой (canonical, alternate) — она ничего не
        # загружает. Считать её звонком наружу — врать на пустом месте.
        if тег.lower().lstrip("<").startswith("link"):
            рел = re.search(r'rel\s*=\s*["\']?([^"\'\s>]+)', тег, re.I)
            if (рел.group(1).lower() if рел else "") not in ЗАГРУЖАЮЩИЕ:
                continue
        вид = "аналитика" if re.search(r"analytic|track|metric|telemetr|gtag|plausible",
                                       url, re.I) else "загрузка"
        живые.append(f"{вид}: {url[:96]}")
    return живые


def отказ_во_встроенном_окне(папка: pathlib.Path) -> bool:
    """Приложение отказывается работать, если открыто внутри другого окна?

    Частая защита «от встраивания самого в себя»: приложение сверяет, кто его
    открыл, и вместо работы показывает заглушку. Для окна ОС это важно: там
    приложение как раз живёт внутри страницы.
    """
    for ф in list(папка.rglob("*.js"))[:400]:
        if ".снято" in ф.name:
            continue
        try:
            т = ф.read_text(errors="ignore")
        except OSError:
            continue
        # признак: сверяет «я внутри окна?» И проверяет, кто открыл (referrer)
        if re.search(r"(self|window)\s*!==?\s*(window\.)?top", т) and "referrer" in т:
            return True
    return False


def признаки_хранения(папка: pathlib.Path) -> dict:
    """Умеет ли приложение вообще сохранять и куда метит."""
    итог = {"браузер": 0, "базы": 0}
    for ф in list(папка.rglob("*.js"))[:400]:
        if ".снято" in ф.name:
            continue
        try:
            т = ф.read_text(errors="ignore")
        except OSError:
            continue
        итог["браузер"] += т.count("localStorage.setItem")
        итог["базы"] += т.count("indexedDB.open") + т.count("idb.open")
    return итог


def порт_занят(порт: int) -> bool:
    with socket.socket() as с:
        с.settimeout(0.4)
        return с.connect_ex(("127.0.0.1", порт)) == 0


def снять(папка: pathlib.Path) -> int:
    стр = папка / ИМЯ_СТРАНИЦЫ
    if стр.exists():
        стр.unlink()
        print(f"  страница проверки снята: {стр}")
    else:
        print("  страницы проверки нет — снимать нечего")
    return 0


def проверить(папка: pathlib.Path, порт: int) -> int:
    print(f"\nПРИЛОЖЕНИЕ: {папка}")

    страница = найти_страницу(папка)
    if not страница:
        print("  ✕ нет index.html — это не готовая веб-сборка, проверять нечего")
        return 1
    print(f"  ✓ стартовая страница: {страница.name}")

    # ── Что видно без запуска ────────────────────────────────────────────────
    живые_обработчики = [и for и in ФАЙЛЫ_ОБРАБОТЧИКА if (папка / и).exists()]
    if живые_обработчики:
        print(f"  ⚠ свой обработчик страниц: {', '.join(живые_обработчики)}")
        print("    пока он жив, правки в index.html до браузера НЕ доходят.")
        print("    снять: mv <файл> <файл>.снято  — браузер сам уберёт регистрацию")
    else:
        print("  ✓ своего обработчика страниц нет (или уже снят)")

    хранение = признаки_хранения(папка)
    if хранение["браузер"] == 0 and хранение["базы"] == 0:
        print("  ⚠ в коде НЕТ обращений к хранилищу — приложение, возможно, "
              "не сохраняет работу вовсе (сборка без слоя сохранения)")
    else:
        куда = []
        if хранение["браузер"]:
            куда.append(f"хранилище браузера ({хранение['браузер']})")
        if хранение["базы"]:
            куда.append(f"базы браузера ({хранение['базы']})")
        print(f"  ✓ признаки сохранения: {', '.join(куда)}")

    # Живые загрузки со стороны — это и есть проверка обещания «без интернета»
    наружу = звонит_наружу(страница)
    if наружу:
        print("  ✕ приложение ЗВОНИТ НАРУЖУ при каждом открытии:")
        for стр in наружу[:6]:
            print(f"      {стр}")
        print("    обещание «всё локально, без интернета» в таком виде НЕВЕРНО.")
        print("    убрать эти строки из index.html (шрифты — на местные файлы),")
        print("    затем перепроверить сетевые запросы в окне браузера")
    else:
        print("  ✓ стартовая страница наружу не звонит")

    if отказ_во_встроенном_окне(папка):
        print("  ⚠ приложение сверяет, кто его открыл, и может ОТКАЗАТЬСЯ работать")
        print("    внутри другого окна (защита от встраивания самого в себя).")
        print("    в окне ОС адрес снаружи чужой — обычно работает; проверять живьём")

    прочие = внешние_адреса(папка)
    if прочие:
        print(f"  · адреса в коде (могут быть просто текстом): {', '.join(прочие[:4])}")

    # ── Страница-проверки рядом с приложением ────────────────────────────────
    # Рядом — потому что только со СВОЕГО адреса видно хранилище приложения.
    if not ШАБЛОН.exists():
        print(f"  ✕ нет шаблона: {ШАБЛОН}")
        return 1
    цель = папка / ИМЯ_СТРАНИЦЫ
    shutil.copyfile(ШАБЛОН, цель)
    print(f"  ✓ страница проверки готова: {цель.name}  (снять: --снять)")

    # ── Как запускать ────────────────────────────────────────────────────────
    print("\nЧТО ДЕЛАТЬ ДАЛЬШЕ")
    if порт_занят(порт):
        print(f"  порт {порт} уже раздаётся — считаю, что это ваше приложение")
    else:
        print("  1) запустить раздачу с хранилищем на диске:")
        print(f"     python3 {КОРЕНЬ / 'tools' / 'cabinet_server.py'} \\")
        print(f"       --папка {папка} --порт {порт} --имя проба --данные ~/extella-cabinet/данные")
    print(f"  2) открыть в ВИДИМОМ окне: http://127.0.0.1:{порт}/{ИМЯ_СТРАНИЦЫ}")
    print("  3) поработать в приложении и нажать «Проверить сохранение»")
    print("\n  Проверять только в видимом окне: часть приложений намеренно не")
    print("  сохраняет в фоновой вкладке, и исправное выглядит сломанным.")
    return 0


def selftest() -> int:
    import tempfile
    ошибки = []
    with tempfile.TemporaryDirectory() as врем:
        п = pathlib.Path(врем)

        if найти_страницу(п) is not None:
            ошибки.append("пустая папка не должна считаться приложением")
        else:
            print("  ✓ папка без index.html отвергается")

        (п / "index.html").write_text("<!doctype html><meta charset=utf-8><body>ok")
        (п / "sw.js").write_text("// обработчик")
        (п / "код.js").write_text(
            "localStorage.setItem('a',1); fetch('https://cdn.example.com/x.woff2');")

        if найти_страницу(п) is None:
            ошибки.append("index.html не найден")
        else:
            print("  ✓ стартовая страница находится")

        живые = [и for и in ФАЙЛЫ_ОБРАБОТЧИКА if (п / и).exists()]
        if живые != ["sw.js"]:
            ошибки.append(f"обработчик не пойман: {живые}")
        else:
            print("  ✓ свой обработчик страниц ловится")

        зн = признаки_хранения(п)
        if зн["браузер"] != 1:
            ошибки.append(f"признак хранения не пойман: {зн}")
        else:
            print("  ✓ признак сохранения ловится")

        вн = внешние_адреса(п)
        if not any("cdn.example.com" in а for а in вн):
            ошибки.append(f"внешний адрес не пойман: {вн}")
        else:
            print("  ✓ внешний адрес ловится")

        (п / "свой.js").write_text("fetch('http://127.0.0.1:34785/x')")
        if any("127.0.0.1" in а for а in внешние_адреса(п)):
            ошибки.append("свой адрес ошибочно признан внешним")
        else:
            print("  ✓ свой адрес внешним не считается")

        # «звонит наружу» — живые загрузки в стартовой странице
        (п / "index.html").write_text(
            '<!doctype html><meta charset=utf-8>'
            '<script src="https://scripts.simpleanalyticscdn.com/latest.js"></script>'
            '<link rel="preload" href="https://cdn.example.com/f.woff2" as="font">'
            '<script src="/assets/свой.js"></script><body>ok')
        зв = звонит_наружу(п / "index.html")
        if len(зв) != 2:
            ошибки.append(f"живые внешние загрузки посчитаны неверно: {зв}")
        elif not any(с.startswith("аналитика") for с in зв):
            ошибки.append(f"аналитика не распознана: {зв}")
        else:
            print("  ✓ звонки наружу ловятся, аналитика распознаётся")

        (п / "index.html").write_text(
            '<!doctype html><meta charset=utf-8><script src="/свой.js"></script>'
            '<link rel="canonical" href="https://excalidraw.com"/>')
        if звонит_наружу(п / "index.html"):
            ошибки.append("местная загрузка или метка canonical принята за звонок")
        else:
            print("  ✓ местные загрузки и метки звонком наружу не считаются")

        # отказ работать внутри другого окна
        if отказ_во_встроенном_окне(п):
            ошибки.append("защита от встраивания найдена там, где её нет")
        else:
            print("  ✓ ложной защиты от встраивания не находит")
        (п / "защита.js").write_text(
            "let f=!1;if(window.self!==window.top)try{"
            "const e=new URL(document.referrer);f=!0}catch{}")
        if not отказ_во_встроенном_окне(п):
            ошибки.append("защита от встраивания не поймана")
        else:
            print("  ✓ защита от встраивания ловится")

        if not ШАБЛОН.exists():
            ошибки.append(f"нет шаблона страницы: {ШАБЛОН}")
        else:
            текст = ШАБЛОН.read_text()
            голова = текст[:текст.find("<script")] if "<script" in текст else текст
            if "charset" not in голова.lower():
                ошибки.append("в шаблоне нет объявления кодировки до скрипта")
            else:
                print("  ✓ у страницы проверки кодировка объявлена до скрипта")

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
    р.add_argument("--порт", type=int, default=34785)
    р.add_argument("--снять", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()

    if а.selftest:
        return selftest()
    if not а.папка:
        р.print_help()
        return 1

    папка = pathlib.Path(а.папка).expanduser().resolve()
    if not папка.is_dir():
        print(f"  ✕ нет такой папки: {папка}")
        return 1
    return снять(папка) if а.снять else проверить(папка, а.порт)


if __name__ == "__main__":
    raise SystemExit(main())
