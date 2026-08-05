#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Манифест зависимостей есть у каждого продукта — и проверяется установщиком (№29).

ЗАЧЕМ. Зависимость, не названная заранее, проявляется у коллеги в момент падения:
«нет модуля», «порт занят», «нет связи при живом интернете». Урок 03.08 стоил дня
слепой переписки. Лечение — MANIFEST.yaml в каждом продукте плюс проверка ДО первой
установки.

Гейт следит за тремя вещами, каждая из которых уже ломалась в других местах:
  1. манифест ЕСТЬ (иначе продукт молча вернулся к прежнему поведению);
  2. модуль проверки — байт в байт копия канона (расхождение = один продукт
     останавливает установку там, где другой её тихо продолжает);
  3. установщик его действительно ЗОВЁТ (файл рядом с установщиком, который никто
     не запускает, — самый дорогой вид зелёной галочки).

Канон: extella-agent-standards/templates/manifest_check.py.

Запуск: python3 tools/check_manifest_copies.py [--selftest]
Коды выхода: 0 — у всех продуктов на этой машине порядок, 1 — нет.
"""
import sys
from pathlib import Path

CANON = Path(__file__).resolve().parents[1] / "templates" / "manifest_check.py"

PRODUCTS = [
    ("Подключения", Path.home() / "Documents/Codex/extella-connectors"),
    ("Predictive Sales", Path.home() / "Documents/Codex/extella-predictive-sales-pack"),
    ("Таргетолог AI", Path.home() / "Documents/Codex/extella-targetologist"),
    ("Юрист по договорам", Path.home() / "Documents/kazakh-lawyer"),
    ("Travel Agency", Path.home() / "Documents/Extella/extella-core-portal/"
                                    "extella-travel-agency-pack"),
    ("Агент-рекрутёр", Path.home() / "Documents/Extella/extella-recruiting-agent"),
]

# Продукты, порождённые каркасом, встают под гейт сами — через реестр. Без этого
# изменение канона гнило бы в них молча (класс «машина отката», уже проходили).
_registry = Path(__file__).resolve().parents[1] / "product_registry.txt"
if _registry.exists():
    for _line in _registry.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#"):
            PRODUCTS.append((Path(_line).name, Path(_line)))


def problems_for(name: str, root: Path) -> list:
    """Что не так у одного продукта. Пустой список = порядок."""
    found = []
    manifest = root / "MANIFEST.yaml"
    module = root / "manifest_check.py"
    if not manifest.is_file():
        found.append("нет MANIFEST.yaml — зависимости продукта нигде не названы")
    else:
        text = manifest.read_text(encoding="utf-8")
        if "checks:" not in text:
            found.append("MANIFEST.yaml без блока checks: — проверять нечего")
    if not module.is_file():
        found.append("нет manifest_check.py — манифест некому прочитать")
    elif module.read_text(encoding="utf-8") != CANON.read_text(encoding="utf-8"):
        found.append("manifest_check.py разошёлся с каноном "
                     "(templates/manifest_check.py) — верни копию канона")
    installers = [p for p in (root / "thin" / "install.py", root / "install.py",
                              root / "deploy.py") if p.is_file()]
    if not installers:
        found.append("не нашёл установщик — проверке негде сработать")
    elif not any("manifest_check" in p.read_text(encoding="utf-8") for p in installers):
        found.append("установщик не зовёт manifest_check — манифест декоративный")
    return found


def selftest() -> int:
    """Гейт обязан краснеть. Проверяем на выдуманном продукте без манифеста."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp)
        (fake / "thin").mkdir()
        (fake / "thin" / "install.py").write_text("print('ставлю')\n", encoding="utf-8")
        found = problems_for("выдуманный", fake)
        if len(found) < 3:
            print("FAIL: гейт не увидел продукт без манифеста —", found)
            return 1
    print("селфтест: продукт без манифеста ловится")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if not CANON.is_file():
        print("  ~ канона нет на этой машине — сверять не с чем")
        return 0
    bad = 0
    for name, root in PRODUCTS:
        if not root.is_dir():
            print("  ~ %s: исходников нет на этой машине — пропускаю" % name)
            continue
        found = problems_for(name, root)
        if not found:
            print("  ✓ %s" % name)
            continue
        bad += 1
        print("  ✗ %s" % name)
        for line in found:
            print("      " + line)
    if bad:
        print("\nМАНИФЕСТЫ ЗАВИСИМОСТЕЙ НЕ В ПОРЯДКЕ (продуктов: %d)." % bad)
        return 1
    print("\nУ каждого продукта на этой машине манифест есть и он проверяется.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
