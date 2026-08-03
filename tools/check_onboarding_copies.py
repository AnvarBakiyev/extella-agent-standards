#!/usr/bin/env python3
"""Экран выбора агента одинаков во всех продуктах.

ЗАЧЕМ. Решение 30.07: агента выбирает пользователь на первом экране КАЖДОГО продукта.
Общей библиотеки у нас нет и быть не может — продукты раздаются самостоятельными
архивами, — поэтому модуль живёт копией в каждом. Копии расходятся молча: кто-то
чинит отказ у себя, и с этого момента один продукт при недоступной платформе говорит
«попробуйте ещё раз», а другой удаляет созданного агента. Разное поведение в момент
отказа — худший вид расхождения: он проявляется ровно тогда, когда человеку и так плохо.

Продуктозависимы ровно шесть констант (имя, роль, тексты, путь к файлу привязки) и
вводный docstring. Всё остальное обязано совпадать с каноном байт в байт.

Канон — extella-recruiting-agent/app/agent_onboarding.py: там модуль родился и там же
лежат его тесты (tests/test_agent_binding.py). Меняешь логику — меняй в каноне и
пересобирай копии, а не правь копию на месте.

Коды выхода: 0 — копии совпадают, 1 — разошлись.
"""
import re
import sys
from pathlib import Path

CANON = Path.home() / "Documents/Extella/extella-recruiting-agent/app/agent_onboarding.py"

COPIES = [
    ("Юрист по договорам", Path.home() / "Documents/kazakh-lawyer/app/agent_onboarding.py"),
    ("Travel Agency", Path.home() / "Documents/Extella/extella-core-portal/"
                                    "extella-travel-agency-pack/app/agent_onboarding.py"),
    ("Таргетолог", Path.home() / "Documents/Codex/extella-targetologist/agent_onboarding.py"),
]

# Продукты, порождённые каркасом new_product.py, встают под гейт сами — через реестр.
# Без этого изменение канона гнило бы в них молча (класс «машина отката»).
_reg = Path(__file__).resolve().parents[1] / "product_registry.txt"
if _reg.exists():
    for _line in _reg.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#"):
            _f = Path(_line) / "app" / ("platform_client.py" if "platform_client" in CANON.name
                                        else "agent_onboarding.py")
            COPIES.append((Path(_line).name, _f))

# Строки, которым положено отличаться: блок настройки продукта.
TUNABLE = re.compile(r"^\s*(PRODUCT_RU|PRODUCT_EN|ROLE_RU|BRAIN_RU|BRAIN_EN|BINDING_FILE)\s*=")


def logic(text: str) -> list:
    """Логика модуля: без вводного docstring и без продуктовых констант."""
    body = text.split('"""', 2)[-1] if text.lstrip().startswith('"""') else text
    return [ln.rstrip() for ln in body.splitlines()
            if ln.strip() and not TUNABLE.match(ln)]


def main() -> int:
    if not CANON.exists():
        print("  ~ канона нет на этой машине — сверять не с чем")
        return 0
    canon_lines = logic(CANON.read_text(encoding="utf-8"))
    problems = []

    print("Экран выбора агента: копии против канона\n")
    for name, path in COPIES:
        if not path.exists():
            print(f"  ~ {name}: исходников нет на этой машине")
            continue
        lines = logic(path.read_text(encoding="utf-8"))
        if lines == canon_lines:
            print(f"  ✓ {name}: совпадает с каноном")
            continue
        extra = [l for l in lines if l not in canon_lines]
        missing = [l for l in canon_lines if l not in lines]
        problems.append(name)
        print(f"  ✗ {name}: логика разошлась с каноном "
              f"(+{len(extra)} своих строк, −{len(missing)} канонических)")
        for l in (missing[:3] + extra[:3]):
            print(f"      {l.strip()[:96]}")

    print()
    if problems:
        print("КОПИИ ЭКРАНА РАЗОШЛИСЬ — продукты поведут себя по-разному при отказе платформы.")
        print("Чинить в каноне и пересобирать копии, а не править копию на месте.")
        return 1
    print("Первый экран одинаков во всех продуктах.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
