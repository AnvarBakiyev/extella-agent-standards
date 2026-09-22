#!/usr/bin/env python3
"""Не даёт уменьшить число правил H, закреплённых машинными проверками.

`--обновить` поднимает минимальную планку до текущего покрытия после зелёной
самопроверки. Обычный запуск падает, если проверок стало меньше.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "DEPLOY_REQUIREMENTS.md"
BASELINE = ROOT / "tools" / "canon_coverage_baseline.json"
NUMBER = re.compile(r"\bH(\d+)(?:-[А-Яа-яA-Za-z]+)?\b")


def canon_numbers() -> set[str]:
    return {"H" + value for value in NUMBER.findall(CANON.read_text(encoding="utf-8"))}


def checked_numbers() -> set[str]:
    found: set[str] = set()
    roots = [ROOT / "tools", ROOT / "templates"]
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".js", ".html", ".md"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            # Номер засчитывается только рядом с исполняемой проверкой/отказом.
            for line in text.splitlines():
                if any(word in line for word in ("if ", "errors.append", "raise ", "bad +=", "assert")):
                    found.update("H" + value for value in NUMBER.findall(line))
                elif line.lstrip().startswith("# H"):
                    found.update("H" + value for value in NUMBER.findall(line))
    return found & canon_numbers()


def main(argv: list[str]) -> int:
    covered = sorted(checked_numbers(), key=lambda item: int(item[1:]))
    if "--обновить" in argv:
        BASELINE.write_text(json.dumps({"minimum": len(covered), "covered": covered},
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"планка покрытия обновлена: {len(covered)} правил; H106 засчитан: {'H106' in covered}")
        return 0 if "H106" in covered else 1
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {"minimum": 0}
    minimum = int(baseline.get("minimum", 0))
    print(f"покрыто машиной: {len(covered)}; минимальная планка: {minimum}")
    if len(covered) < minimum:
        print("ПОКРЫТИЕ КАНОНА УПАЛО")
        return 1
    if "H106" not in covered:
        print("H106 не закреплён машинной проверкой")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
