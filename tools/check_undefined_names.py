#!/usr/bin/env python3
r"""Инструмент не ссылается на имя, которого нет (H120).

ЗАЧЕМ. Замер 28.09.2026: правка проверки в `store_app/update.py` убрала переменную
`маркер`, но использовалась она ДВАЖДЫ — до отправки и после. Первое место я поправил,
второе не заметил. Страница при этом успешно уехала покупателям, а скрипт упал
`NameError` на контроле ПОСЛЕ отправки: выкладка выглядела провалившейся, хотя
прошла. Человек в такой ситуации жмёт ещё раз, не зная, что уже всё сделано.

Python обнаруживает такое только в момент исполнения этой ветки, а ветка «после
успешной отправки» на сухом прогоне не исполняется никогда. Компиляция файла
(`py_compile`) NameError не видит: синтаксис-то верен.

ЧТО ПРОВЕРЯЕТСЯ. Разбором дерева: имя, прочитанное внутри функции, должно быть либо
её локальным, либо аргументом, либо заданным на верхнем уровне модуля, либо
импортом, либо встроенным. Иначе — ссылка на несуществующее имя.

ГРАНИЦЫ. Проверка НЕ заменяет pyflakes и не ищет неиспользованные имена, теневые
области и прочее. Она закрывает один класс: правка удалила имя и оставила ссылку.
Узко намеренно — широкая проверка на своём коде даёт ложные тревоги, а врущий гейт
отключают целиком.

ПРИЁМКА 28.09.2026: прогон по 179 файлам дал 18 попаданий, из них 17 ЛОЖНЫХ — на
модульное имя `__file__`, которое Python даёт сам и которого нет в `dir(builtins)`.
Добавлены модульные имена, проба держит это. Настоящая находка одна и та, ради
которой проверка писалась: `маркер` в `store_app/update.py`.

Предыдущая редакция этой строки называла «2 ложные тревоги» — я написал её ДО
прогона, по догадке о том, что найдётся. Так делать нельзя: строка приёмки описывает
замер, а не ожидание (H113).

Повторная приёмка 29.09.2026 на дереве после шести чужих PR (инструменты переписаны
под Windows-консоль): 183 файла, ложных тревог нет; на `update.py` из main, где
дефект ещё жил, гейт его поймал. Номер правила сменён с H118 на H120 — H118 и H119
на main к этому времени заняли другие правила.

    python3 tools/check_undefined_names.py
    python3 tools/check_undefined_names.py --selftest

Коды выхода: 0 — все имена определены, 1 — есть ссылка на несуществующее имя.
"""

from __future__ import annotations

import ast
import builtins
import pathlib
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parents[1]
# Модульные имена Python даёт сам и в dir(builtins) их нет: живой прогон дал на них
# 17 ложных тревог из 18 попаданий (замер 28.09.2026).
МОДУЛЬНЫЕ = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
             "__loader__", "__builtins__", "__debug__", "__path__"}
ВСТРОЕННЫЕ = set(dir(builtins)) | МОДУЛЬНЫЕ
МИМО = ("/.git/", "/dist/", "/node_modules/", "/backups/")


def заданные_модуля(дерево: ast.AST) -> set[str]:
    имена: set[str] = set()
    for узел in ast.walk(дерево):
        if isinstance(узел, (ast.Import, ast.ImportFrom)):
            for а in узел.names:
                имена.add((а.asname or а.name).split(".")[0])
        elif isinstance(узел, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            имена.add(узел.name)
        elif isinstance(узел, ast.Name) and isinstance(узел.ctx, ast.Store):
            имена.add(узел.id)
        elif isinstance(узел, ast.arg):
            имена.add(узел.arg)
    return имена


def беды_файла(путь: pathlib.Path) -> list[str]:
    try:
        дерево = ast.parse(путь.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []                      # синтаксис — забота другой проверки
    верх = заданные_модуля(дерево)
    плохо = []
    for ф in [у for у in ast.walk(дерево)
              if isinstance(у, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        свои = {а.arg for а in ф.args.args + ф.args.kwonlyargs}
        if ф.args.vararg: свои.add(ф.args.vararg.arg)
        if ф.args.kwarg: свои.add(ф.args.kwarg.arg)
        for у in ast.walk(ф):
            if isinstance(у, ast.Name) and isinstance(у.ctx, ast.Store):
                свои.add(у.id)
            elif isinstance(у, ast.ExceptHandler) and у.name:
                свои.add(у.name)
            elif isinstance(у, (ast.Import, ast.ImportFrom)):
                for а in у.names:
                    свои.add((а.asname or а.name).split(".")[0])
            # Объявленное global/nonlocal имя задаётся не здесь — это не ошибка.
            elif isinstance(у, (ast.Global, ast.Nonlocal)):
                свои.update(у.names)
            elif isinstance(у, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                свои.add(у.name)
        for у in ast.walk(ф):
            if isinstance(у, ast.Name) and isinstance(у.ctx, ast.Load):
                if у.id not in свои and у.id not in верх and у.id not in ВСТРОЕННЫЕ:
                    плохо.append(f"{путь.name}:{у.lineno} {ф.name}(): имя «{у.id}» "
                                 f"не задано — правка удалила его, а ссылка осталась")
    return плохо


def проверить() -> int:
    плохо = []
    файлов = 0
    for ф in sorted(КОРЕНЬ.rglob("*.py")):
        путь = "/" + str(ф.relative_to(КОРЕНЬ))
        if any(м in путь for м in МИМО):
            continue
        файлов += 1
        плохо += беды_файла(ф)
    for б in sorted(set(плохо)):
        print("  ✗ " + б)
    print(f"проверено файлов: {файлов}")
    if плохо:
        print("\nНЕ УСПЕХ (H120): инструмент ссылается на имя, которого нет.")
        return 1
    print("H120 цел: ссылок на несуществующие имена нет.")
    return 0


def _selftest() -> int:
    import tempfile
    провалы = []

    def проба(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка check_undefined_names:")
    with tempfile.TemporaryDirectory() as вр:
        д = pathlib.Path(вр)

        плохой = д / "плохой.py"
        плохой.write_text("def f():\n    return маркер\n", encoding="utf-8")
        проба("ссылка на несуществующее имя ловится", беды_файла(плохой) != [])

        хороший = д / "хороший.py"
        хороший.write_text("МЕТКА = 1\ndef f():\n    x = 2\n    return МЕТКА + x\n", encoding="utf-8")
        проба("имя модуля и локальное претензий не вызывают", беды_файла(хороший) == [])

        # Ложная тревога живого прогона: объявленное global имя задаётся не здесь.
        глоб = д / "глоб.py"
        глоб.write_text("СЧЁТ = 0\ndef f():\n    global СЧЁТ\n    СЧЁТ += 1\n", encoding="utf-8")
        проба("объявленное global имя за ошибку не считается", беды_файла(глоб) == [])

        # Ложная тревога живого прогона: имя задано в другой ветке try.
        ветка = д / "ветка.py"
        ветка.write_text("def f():\n    try:\n        x = 1\n    except Exception:\n"
                         "        x = 2\n    return x\n", encoding="utf-8")
        проба("имя из ветки try/except за ошибку не считается", беды_файла(ветка) == [])

        # Ложная тревога живого прогона: модульное имя, которое даёт Python.
        модульное = д / "модульное.py"
        модульное.write_text("def f():\n    return __file__ + __name__\n", encoding="utf-8")
        проба("модульные имена за ошибку не считаются", беды_файла(модульное) == [])

        импорт = д / "импорт.py"
        импорт.write_text("def f():\n    import json\n    return json.dumps({})\n", encoding="utf-8")
        проба("импорт внутри функции виден", беды_файла(импорт) == [])

        битый = д / "битый.py"
        битый.write_text("def f(:\n", encoding="utf-8")
        проба("битый синтаксис не ломает проверку", беды_файла(битый) == [])

    проба("H120 назван в тексте проверки",
          "H120" in pathlib.Path(__file__).read_text(encoding="utf-8"))

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы — " + "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    # H118: узкая консоль Windows (cp1252) роняет печать по-русски на первом символе.
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(_selftest() if "--selftest" in sys.argv else проверить())
