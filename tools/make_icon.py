#!/usr/bin/env python3
"""Старое имя генератора иконок. Работу делает `bronze_icon.py`.

ПОЧЕМУ ОБЁРТКА, А НЕ ВТОРОЙ ГЕНЕРАТОР. Канон стиля один —
`docs/ICON_STYLE_BRONZE.md`, исполняемый источник — `tools/bronze_icon.py`.
20.08.2026 здесь недолго жил свой генератор Bronze Engraved, написанный, пока
канонический уже лежал в репозитории: два источника одного стиля расходятся
молча, и это ровно тот класс поломки, против которого стоят гейты копий.
Поэтому файл сведён к переходнику: старые вызовы продолжают работать и получают
каноническую плитку.

    python3 tools/make_icon.py доска editions/пример/icon.png

Новые вызовы пишите прямо к канону:

    python3 tools/bronze_icon.py shapes editions/пример/icon.png
    python3 tools/bronze_icon.py --список
"""

import pathlib
import subprocess
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
КАНОН = СЮДА / "bronze_icon.py"

# Старые имена → глифы Lucide. Соответствия взяты из реестра занятых глифов
# в docs/ICON_STYLE_BRONZE.md, а не придуманы заново: «доска» там shapes,
# «сторож» — activity.
СИНОНИМЫ = {
    "доска": "shapes",
    "сторож": "activity",
    "таблица": "table",
    "пульт": "terminal",
    "docs": "book-open",
    "tech": "terminal",
    "box": "app-window",
    "search": "app-window",
}


def _глиф(имя: str) -> str:
    имя = (имя or "").strip()
    return СИНОНИМЫ.get(имя, имя)


def main() -> int:
    if "--selftest" in sys.argv:
        # Гейт остаётся зелёным и проверяет то единственное, за что теперь
        # отвечает этот файл: что переходник ведёт к канону и что каждое старое
        # имя разрешается в существующий глиф Lucide.
        ошибки = []
        if not КАНОН.is_file():
            ошибки.append("канонический bronze_icon.py не найден")
        набор = {x.stem for x in (СЮДА.parent / "templates" / "lucide").glob("*.svg")}
        for старое, глиф in СИНОНИМЫ.items():
            if глиф in набор:
                print(f"  ✓ {старое} → {глиф}")
            else:
                print(f"  ✗ {старое} → {глиф}: глифа нет в templates/lucide")
                ошибки.append(старое)
        if ошибки:
            print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(ошибки))
            return 1
        print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
        return 0

    if len(sys.argv) < 3:
        print(__doc__)
        print("старые имена:", ", ".join(f"{k}→{v}" for k, v in СИНОНИМЫ.items()))
        return 2

    аргументы = [sys.executable, str(КАНОН), _глиф(sys.argv[1]), sys.argv[2]]
    аргументы += [а for а in sys.argv[3:] if а.startswith("--")]
    return subprocess.run(аргументы).returncode


if __name__ == "__main__":
    sys.exit(main())
