#!/usr/bin/env python3
"""Зафиксировать: add-version публичного листинга — тоже публичное действие."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "store_app" / "content.json"
OLD_VERSION = "2026-08-14.2"
NEW_VERSION = "2026-08-14.3"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"миграция не применена: ожидался один якорь {label}")
    return text.replace(old, new, 1)


def main() -> None:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("версия_содержимого") != OLD_VERSION:
        raise SystemExit("миграция не применена: неожиданная версия содержимого")
    by_number = {section.get("номер"): section for section in data.get("разделы") or []}
    section_11 = by_number.get("11") or {}
    section_12 = by_number.get("12") or {}
    section_11["тело"] = replace_once(
        section_11.get("тело", ""),
        "<li>Выложи предрелизом, купи себе, пройди первый запуск чистым состоянием.</li>\n<li>Остановись перед Publish: эту кнопку нажимает человек.</li>",
        "<li>Новый листинг выложи предрелизом, купи себе, пройди первый запуск чистым состоянием.</li>\n<li>Остановись перед публичным действием: Publish для нового листинга или add-version для уже опубликованного. Решение принимает человек.</li>",
        "границы публичного действия",
    )
    section_12["тело"] = replace_once(
        section_12.get("тело", ""),
        "выкладывает предрелизом, покупает автору и проверяет страницу, права и ярлык. Publish остаётся\nединственным ручным необратимым действием.",
        "новый листинг выкладывает предрелизом, покупает автору и проверяет страницу, права и ярлык.\nДля опубликованного листинга add-version сразу виден в публичном API, поэтому требует отдельного\nрешения владельца так же, как Publish.",
        "описания конвейера",
    )
    data["версия_содержимого"] = NEW_VERSION
    data["что_нового"].insert(0, {
        "версия": NEW_VERSION,
        "строки": [
            "Живая проверка: add-version уже опубликованного листинга сразу становится публичным",
            "Конвейер требует отдельное решение владельца и перед Publish, и перед такой новой версией",
        ],
    })
    CONTENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
