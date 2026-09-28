#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Инструмент, который мы велим запустить, не должен умирать на первой печати (H118, F04).

ЗАЧЕМ. Замер 28.09.2026, первый в истории прогон CI на windows-latest: консоль там
в кодировке cp1252, и `print("  ✓ H78: источник ключа…")` роняет процесс
`UnicodeEncodeError` — на первом же символе. Человек на Windows видит стектрейс
вместо подсказки, причём ДО того, как инструмент что-либо сделал. До этого прогона
мы говорили «любая ОС», ни разу её не запустив.

ЧТО ПРОВЕРЯЕТСЯ. Не весь репозиторий, а ровно то, что мы велим запустить человеку.
Список НЕ пишется руками: он собирается из документов, которые новичок читает, —
README, вход агента, копируемый промпт, онбординг и текст приложения. Скажем ему
завтра запускать новый инструмент — он попадёт сюда сам.

Каждый такой инструмент запускается со своей самопроверкой в узкой кодировке
(`PYTHONIOENCODING=cp1252`). Падение с `UnicodeEncodeError` — провал.

ГРАНИЦА, КОТОРУЮ НАЗЫВАЕМ ВСЛУХ. Уязвим не только этот список: печатают по-русски
почти все инструменты репозитория, и на Windows упадёт каждый. Гейт печатает это
число в каждом прогоне, чтобы дыра не забывалась. Поддержка Windows этим НЕ
объявляется — закрыт только путь новичка.

    python3 tools/check_windows_console.py
    python3 tools/check_windows_console.py --selftest

Коды выхода: 0 — путь новичка переживает узкую консоль, 1 — нет.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parents[1]
ДОКУМЕНТЫ_НОВИЧКА = (
    "README.md", "AGENT_START.md", "PROMPT_FOR_EXTERNAL_AGENT.md",
    "EXTELLA_AI_ONBOARDING.md", "store_app/content.json",
)
ВЫЗОВ = re.compile(r"python3?\s+((?:tools|store_app)/[A-Za-z0-9_/]+\.py)")
УЗКАЯ = "cp1252"


def названные() -> list[str]:
    """Инструменты, которые документы велят запустить человеку. Порядок — по имени,
    чтобы вывод был одинаков от прогона к прогону."""
    найдено = set()
    for имя in ДОКУМЕНТЫ_НОВИЧКА:
        путь = КОРЕНЬ / имя
        if not путь.exists():
            continue
        текст = путь.read_text(encoding="utf-8", errors="replace")
        for m in ВЫЗОВ.finditer(текст):
            if (КОРЕНЬ / m.group(1)).exists():
                найдено.add(m.group(1))
    return sorted(найдено)


def защищён_вход(текст: str) -> bool:
    """Защита стоит в НАСТОЯЩЕЙ точке входа — последнем верхнеуровневом
    `if __name__ == "__main__"`. Искать по тексту нельзя: строка точки входа
    встречается и внутри тестовых заготовок, и 28.09.2026 сплошной проход по
    тексту вставил защиту в заготовку, мимо настоящего входа. Синтаксис при
    этом цел — ловит только дерево разбора."""
    import ast
    try:
        дерево = ast.parse(текст)
    except SyntaxError:
        return False
    входы = [у for у in дерево.body
             if isinstance(у, ast.If) and "__name__" in ast.unparse(у.test)]
    if not входы:
        return True  # модуль без входа печатает в канал того, кто его импортировал
    тело = "\n".join(ast.unparse(у) for у in входы[-1].body)
    return "reconfigure(" in тело or "настроить_вывод(" in тело


def уязвимые_всего() -> tuple[int, int, list[str]]:
    """Сколько инструментов печатают не-ASCII, сколько защищены в настоящей точке
    входа, и какие — нет."""
    печатают = защищены = 0
    голые = []
    for f in sorted((КОРЕНЬ / "tools").rglob("*.py")):
        т = f.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"print\([^)]*[^\x00-\x7f]", т):
            continue
        печатают += 1
        if защищён_вход(т):
            защищены += 1
        else:
            голые.append(f.relative_to(КОРЕНЬ).as_posix())
    return печатают, защищены, голые


def переживает(относительный: str, таймаут: int = 180) -> tuple[bool, str]:
    """Запускаем самопроверку инструмента в узкой консоли. Нас интересует ровно
    одно: не умер ли он на печати. Прочие отказы — не наше дело, их стерегут
    собственные гейты."""
    среда = dict(os.environ, PYTHONIOENCODING=УЗКАЯ)
    аргумент = "--selftest"
    текст = (КОРЕНЬ / относительный).read_text(encoding="utf-8", errors="replace")
    if "--selftest" not in текст:
        аргумент = "--help"
    try:
        итог = subprocess.run([sys.executable, str(КОРЕНЬ / относительный), аргумент],
                              capture_output=True, env=среда, timeout=таймаут)
    except subprocess.TimeoutExpired:
        return False, "не ответил вовремя"
    вывод = (итог.stdout or b"") + (итог.stderr or b"")
    if b"UnicodeEncodeError" in вывод:
        return False, "падает на печати (UnicodeEncodeError)"
    return True, f"{аргумент}, код {итог.returncode}"


def прогон() -> int:
    список = названные()
    if not список:
        print("  ✗ в документах новичка не названо ни одного инструмента — "
              "разбор сломался, а не документы стали чище")
        return 1
    беды = []
    for имя in список:
        цел, как = переживает(имя)
        print(("  ✓ " if цел else "  ✗ ") + f"{имя}: {как}")
        if not цел:
            беды.append(имя)

    печатают, защищены, голые = уязвимые_всего()
    print(f"\nВсе инструменты: печатают по-русски {печатают}, защищены в настоящей "
          f"точке входа {защищены}.")
    for г in голые:
        print(f"  ✗ {г}: вывод не переведён в UTF-8 — на Windows упадёт на первой печати")
    if беды or голые:
        if беды:
            print("НЕ УСПЕХ: путь новичка не переживает узкую консоль — " + ", ".join(беды))
        if голые:
            print("НЕ УСПЕХ: инструмент без защиты вывода (H118). Шесть строк в точке "
                  "входа — образец в любом соседнем файле tools/.")
        return 1
    print("ПРОВЕРКА ПОВЕДЕНИЕМ пройдена для пути новичка, ПРОВЕРКА ИСХОДНИКОВ — для "
          "всех инструментов. Живого Windows-прогона всех инструментов это не заменяет: "
          "CI гоняет на Windows только коннектор и обвязку.")
    return 0


def selftest() -> int:
    import tempfile
    провалы = []
    print("Самопроверка check_windows_console:")

    if not названные():
        провалы.append("список инструментов пуст — разбор документов сломан")
    print(f"  ✓ список собран из документов, не руками ({len(названные())} шт.)")

    with tempfile.TemporaryDirectory() as вр:
        вр = pathlib.Path(вр)
        (вр / "tools").mkdir()
        хрупкий = вр / "tools" / "хрупкий.py"
        хрупкий.write_text(
            "import sys\nprint('  ✓ проба кириллицей')\n", encoding="utf-8")
        крепкий = вр / "tools" / "крепкий.py"
        крепкий.write_text(
            "import sys\n"
            "for п in (sys.stdout, sys.stderr):\n"
            "    try:\n        п.reconfigure(encoding='utf-8', errors='replace')\n"
            "    except Exception:\n        pass\n"
            "print('  ✓ проба кириллицей')\n", encoding="utf-8")
        глобальный = globals()
        прежний = глобальный["КОРЕНЬ"]
        глобальный["КОРЕНЬ"] = вр
        try:
            цел, _ = переживает("tools/хрупкий.py")
            if цел:
                провалы.append("падение на печати НЕ поймано — детектор слеп")
            цел2, _ = переживает("tools/крепкий.py")
            if not цел2:
                провалы.append("защищённый инструмент объявлен падающим — ложная тревога")
        finally:
            глобальный["КОРЕНЬ"] = прежний
    print("  ✓ падение на печати ловится, защищённый проходит")

    # Защита в строке-заготовке, а не в настоящем входе, обязана ловиться.
    обманка = (
        "import sys\n"
        "ЗАГОТОВКА = '''\n"
        "if __name__ == \"__main__\":\n"
        "    sys.stdout.reconfigure(encoding=\"utf-8\")\n"
        "'''\n"
        "if __name__ == \"__main__\":\n"
        "    print(\"проба\")\n")
    if защищён_вход(обманка):
        провалы.append("защита внутри строки-заготовки засчитана — ровно та ошибка 28.09")
    else:
        print("  ✓ защита в заготовке мимо настоящего входа ловится")

    if провалы:
        for п in провалы:
            print("  ✗ " + п)
        print("ИТОГ САМОПРОВЕРКИ: провалы есть")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(selftest() if "--selftest" in sys.argv else прогон())
