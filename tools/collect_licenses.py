#!/usr/bin/env python3
"""Собрать лицензии чужой сборки в один файл рядом с приложением.

ЗАЧЕМ. Свободные лицензии разрешают брать, менять и продавать, но почти все
требуют одного: **сохранять текст лицензии и уведомление об авторстве в копиях**.
Готовые сборки с GitHub приезжают без файла LICENSE — он остаётся в исходниках,
а в собранной папке его нет. Замер 16.08.2026: в сборке Excalidraw файла лицензии
не было вовсе, при 174 блоках лицензий внутри собранного кода (Apache 2.0 у
шрифтового движка и шрифтов, MIT у DOMPurify, pako, js-yaml и других).

Условие выполняется буквально: тексты, которые уже едут внутри кода, выкладываются
рядом читаемым файлом, а лицензия самого приложения ставится первой.

    python3 tools/collect_licenses.py ~/extella-plugins/приложение \\
            --основная ЛИЦЕНЗИЯ_ПРИЛОЖЕНИЯ.txt --имя "Excalidraw"
    python3 tools/collect_licenses.py <папка> --показать      # ничего не писать
    python3 tools/collect_licenses.py --selftest

Инструмент НЕ решает юридических вопросов и не заменяет юриста: он лишь не даёт
потерять то, что уже приехало вместе с кодом.

Коды выхода: 0 — файл собран (или показан), 1 — отказ с причиной.
"""

import argparse
import pathlib
import re
import sys

ИМЯ_ФАЙЛА = "ЛИЦЕНЗИИ.md"
РАСШИРЕНИЯ = (".js", ".css", ".mjs")
# Блок лицензии в собранном коде: /*! … */ или /** @license … */
БЛОК = re.compile(r"/\*[!*][\s\S]{0,4000}?\*/")
ПРИЗНАК = re.compile(r"licen[cs]e|copyright", re.I)
КОПИРАЙТ = re.compile(r"Copyright[^\n\"'<*]{5,90}")


def вид_лицензии(текст: str) -> str:
    # Машинная метка SPDX — самый надёжный источник, она и задумана для этого.
    м = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+(?:\s+(?:OR|AND)\s+[A-Za-z0-9.+-]+)*)",
                  текст, re.I)
    if м:
        return м.group(1).strip()
    # Иначе по названию. Двойные лицензии называем обе: скрыть одну — соврать.
    виды = []
    if re.search(r"apache\s+licen[cs]e", текст, re.I):
        виды.append("Apache 2.0")
    if re.search(r"mozilla public license|\bMPL\b", текст, re.I):
        виды.append("MPL 2.0")
    if re.search(r"\bMIT\b", текст):
        виды.append("MIT")
    if re.search(r"\bBSD\b", текст):
        виды.append("BSD")
    if re.search(r"\b(GPL|LGPL)\b", текст):
        виды.append("GPL/LGPL")
    return " / ".join(виды) if виды else "не определена"


def имя_компонента(текст: str) -> str:
    м = re.search(r"@license\s+([A-Za-z0-9@/._-]{2,40})", текст)
    if м and м.group(1).lower() not in ("mit", "apache", "bsd"):
        return м.group(1)
    м = re.search(r"/\*!\s*([a-z0-9@/._-]{3,40})\s+v?[\d.]", текст)
    if м:
        return м.group(1)
    м = КОПИРАЙТ.search(текст)
    if м:
        # «Copyright (c) 2019 Ebrahim Byagowi» → «Ebrahim Byagowi»
        имя = re.sub(r"Copyright\s*(\(c\))?\s*[\d,\s-]*", "", м.group(0)).strip()
        return (имя.split("(")[0].strip() or "неизвестный компонент")[:48]
    return "неизвестный компонент"


def собрать(папка: pathlib.Path) -> tuple[list[dict], list[str]]:
    блоки: dict[str, dict] = {}
    копирайты: set[str] = set()
    файлы = [п for п in папка.rglob("*")
             if п.is_file() and п.suffix.lower() in РАСШИРЕНИЯ and ".снято" not in п.name]
    for ф in файлы:
        try:
            т = ф.read_text(errors="ignore")
        except OSError:
            continue
        for c in КОПИРАЙТ.findall(т):
            копирайты.add(" ".join(c.split())[:88])
        for м in БЛОК.finditer(т):
            текст = м.group(0)
            if not ПРИЗНАК.search(текст):
                continue
            ключ = re.sub(r"\s+", " ", текст).strip()
            if ключ in блоки:
                continue
            блоки[ключ] = {"текст": текст.strip(), "вид": вид_лицензии(текст),
                           "имя": имя_компонента(текст)}
    порядок = sorted(блоки.values(), key=lambda б: (б["вид"], б["имя"].lower()))
    return порядок, sorted(копирайты)


def свести(блоки: list[dict], копирайты: list[str], основная: str, имя: str) -> str:
    виды: dict[str, int] = {}
    for б in блоки:
        виды[б["вид"]] = виды.get(б["вид"], 0) + 1
    сводка = " · ".join(f"{в}: {н}" for в, н in sorted(виды.items()))

    ч = [f"# Лицензии — {имя}", "",
         "Этот файл собран инструментом `tools/collect_licenses.py` из самой сборки.",
         "",
         "**Зачем он.** Свободные лицензии разрешают брать, менять и продавать, но почти",
         "все требуют одного: сохранять текст лицензии и уведомление об авторстве в копиях.",
         "Готовые сборки с GitHub приезжают без файла лицензии — он остаётся в исходниках.",
         "Здесь собрано то, что уже едет внутри кода, плюс лицензия самого приложения.",
         "",
         f"Найдено блоков лицензий: **{len(блоки)}** ({сводка}).",
         "",
         "Это не юридическое заключение: инструмент лишь не даёт потерять то,",
         "что приехало вместе с кодом.",
         "", "---", "", f"## Лицензия приложения ({имя})", "", "```", основная.strip(), "```", ""]

    if блоки:
        ч += ["---", "", "## Лицензии встроенных компонентов", ""]
        текущий = None
        for б in блоки:
            if б["вид"] != текущий:
                текущий = б["вид"]
                ч += [f"### {текущий}", ""]
            ч += [f"**{б['имя']}**", "", "```", б["текст"], "```", ""]

    if копирайты:
        ч += ["---", "", "## Уведомления об авторстве, найденные в коде", ""]
        ч += [f"- {c}" for c in копирайты]
        ч += [""]
    return "\n".join(ч)


def работа(папка: pathlib.Path, основная_путь: str, имя: str, показать: bool) -> int:
    блоки, копирайты = собрать(папка)
    print(f"\nПАПКА: {папка}")
    виды: dict[str, int] = {}
    for б in блоки:
        виды[б["вид"]] = виды.get(б["вид"], 0) + 1
    for в, н in sorted(виды.items()):
        print(f"  {в:14} блоков: {н}")
    print(f"  уведомлений об авторстве: {len(копирайты)}")
    if any("GPL" in в for в in виды):
        print("  ⚠ найдена GPL/LGPL — у неё условия жёстче остальных,")
        print("    выкладку такого продукта надо обсудить с юристом отдельно")
    неясные = виды.get("не определена", 0)
    if неясные:
        print(f"  ⚠ не опознано блоков: {неясные} — посмотреть глазами в {ИМЯ_ФАЙЛА}:")
        print("    оставлять «не определена» в файле лицензий нельзя, это дыра")

    if показать:
        return 0
    основная = pathlib.Path(основная_путь).expanduser()
    if not основная.exists():
        print(f"  ✕ нет файла лицензии приложения: {основная}")
        print("    возьмите его из первоисточника проекта (файл LICENSE) — угадывать нельзя")
        return 1
    цель = папка / ИМЯ_ФАЙЛА
    цель.write_text(свести(блоки, копирайты, основная.read_text(), имя))
    print(f"  ✓ собрано: {цель}  ({цель.stat().st_size} байт)")
    return 0


def selftest() -> int:
    import tempfile
    ошибки = []
    with tempfile.TemporaryDirectory() as врем:
        п = pathlib.Path(врем)
        (п / "a.js").write_text(
            '/*! pako 2.0 | (c) 2014 Vitaly Puzrin | MIT License */\nvar a=1;\n'
            '/**\n * @license React\n * Copyright (c) Meta Platforms, Inc.\n'
            ' * This source code is licensed under the MIT license.\n */\n')
        (п / "b.js").write_text(
            '/*!\n * Copyright 2019 Google LLC\n * Licensed under the Apache License, Version 2.0\n */\n'
            '/*! pako 2.0 | (c) 2014 Vitaly Puzrin | MIT License */\n')   # дубль
        (п / "c.js").write_text('var b=2; // без лицензий')
        блоки, копирайты = собрать(п)

        (п / "d.js").write_text(
            "/** @license\n * Copyright Кто-то\n * SPDX-License-Identifier: Apache-2.0\n */\n"
            "/*! @license Штука 1.0 | Released under the Apache license 2.0 "
            "and Mozilla Public License 2.0 */\n")
        блоки, копирайты = собрать(п)

        проверки = [
            ("дубль не удваивается", len(блоки) == 5),
            ("Apache распознан", any(б["вид"] == "Apache 2.0" for б in блоки)),
            ("MIT распознан", any(б["вид"] == "MIT" for б in блоки)),
            ("метка SPDX сильнее догадок", any(б["вид"] == "Apache-2.0" for б in блоки)),
            ("двойная лицензия названа целиком",
             any(б["вид"] == "Apache 2.0 / MPL 2.0" for б in блоки)),
            ("неопознанных не осталось", not any(б["вид"] == "не определена" for б in блоки)),
            ("имя пакета вытащено", any(б["имя"] == "pako" for б in блоки)),
            ("копирайты собраны", len(копирайты) >= 2),
        ]
        for имя_п, ок in проверки:
            print(("  ✓ " if ок else "  ✕ ") + имя_п)
            if not ок:
                ошибки.append(имя_п)

        (п / "своя.txt").write_text("MIT License\n\nCopyright (c) 2020 Пример\n")
        код = работа(п, str(п / "своя.txt"), "Пример", False)
        текст = (п / ИМЯ_ФАЙЛА).read_text() if (п / ИМЯ_ФАЙЛА).exists() else ""
        for имя_п, ок in [
            ("файл собран", код == 0 and текст),
            ("лицензия приложения первой", текст.find("Лицензия приложения") < текст.find("встроенных компонентов")),
            ("текст лицензии приложения на месте", "Copyright (c) 2020 Пример" in текст),
            ("блоки перенесены дословно", "Vitaly Puzrin" in текст and "Google LLC" in текст),
        ]:
            print(("  ✓ " if ок else "  ✕ ") + имя_п)
            if not ок:
                ошибки.append(имя_п)

        # Без лицензии приложения молча собирать нельзя: угадывать её запрещено.
        (п / ИМЯ_ФАЙЛА).unlink()
        if работа(п, str(п / "нет.txt"), "Пример", False) == 0:
            ошибки.append("собрал без лицензии приложения")
        else:
            print("  ✓ без лицензии приложения отказывает")

    if ошибки:
        print("ИТОГ САМОПРОВЕРКИ: есть отказы")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("папка", nargs="?")
    р.add_argument("--основная", default="")
    р.add_argument("--имя", default="приложение")
    р.add_argument("--показать", action="store_true")
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
    return работа(папка, а.основная, а.имя, а.показать)


if __name__ == "__main__":
    raise SystemExit(main())
