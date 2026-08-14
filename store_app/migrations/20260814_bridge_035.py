#!/usr/bin/env python3
"""Перевести единственный ручной fallback моста с 0.3.4 на 0.3.5."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "store_app" / "content.json"
OLD_VERSION = "2026-08-14.1"
NEW_VERSION = "2026-08-14.2"
OLD_REF = "--ref v0.3.4"
NEW_REF = "--ref v0.3.5"


def main() -> None:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("версия_содержимого") != OLD_VERSION:
        raise SystemExit("миграция не применена: неожиданная версия содержимого")
    sections = data.get("разделы") or []
    bridge = [section for section in sections if section.get("номер") == "09"]
    if len(bridge) != 1 or bridge[0].get("тело", "").count(OLD_REF) != 1:
        raise SystemExit("миграция не применена: ручной fallback найден не один раз")
    bridge[0]["тело"] = bridge[0]["тело"].replace(OLD_REF, NEW_REF, 1)
    data["версия_содержимого"] = NEW_VERSION
    data["что_нового"].insert(0, {
        "версия": NEW_VERSION,
        "строки": [
            "Кнопка Codex использует мост 0.3.5 и читает локальный токен текущего Extella-аккаунта",
            "Установка выполняет только пять поддерживаемых безмодельных этапов",
        ],
    })
    CONTENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
