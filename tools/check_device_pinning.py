#!/usr/bin/env python3
"""Закрепление за машиной — только массивом `targets` (H107).

ЗАЧЕМ. Одиночное поле `target` читает установленная сборка витрины, а исходники
платформы — нет. Код, который закрепляет работу одним полем, у одного человека
работает, у другого молча уезжает на устройство по умолчанию: именно так задачи
коллег ушли на машину владельца. Замеры и разбор — H107 в DEPLOY_REQUIREMENTS.md.

ЧТО ЛОВИТ. Строку, где есть `target=` или `"target":`, но во всём вызове нет
`targets`. Проверяются исходники продуктов: tools/*.py, templates/**, editions/**,
experts/*.py.

ЧЕГО НЕ ЛОВИТ (намеренно). `target_id` и `set_default_target` — это работа с
записями и умолчанием, а не закрепление вызова. Ложный красный вреден так же, как
пропуск: гейт, который врёт, отключают целиком.

    python3 tools/check_device_pinning.py
    python3 tools/check_device_pinning.py --selftest

Коды выхода: 0 — нарушений нет, 1 — есть.
"""

from __future__ import annotations

import pathlib
import re
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parents[1]
ПАПКИ = ("tools", "templates", "editions", "experts")
РАСШИРЕНИЯ = {".py", ".js", ".html"}
# Чужой код не наш и правилу не подчиняется: библиотеки продуктов и всё минифицированное.
# Первая редакция гейта покраснела на luckysheet внутри пакета «Таблицы» — ложный красный
# так же вреден, как пропуск.
ЧУЖОЕ = ("node_modules", "/vendor", "/payload/apps/", ".min.")


def чужой(путь: pathlib.Path, текст: str) -> bool:
    if any(кусок in str(путь) for кусок in ЧУЖОЕ):
        return True
    строки = текст.splitlines() or [""]
    return max((len(с) for с in строки), default=0) > 400          # минифицировано

# `target=` или "target": — но не target_id, не default_target, не targets
ОДИНОЧНОЕ = re.compile(r"""(?<![_a-z])target\s*[=:]\s*['"{]|["']target["']\s*:""", re.I)
ЕСТЬ_МАССИВ = re.compile(r"targets\s*[=:]", re.I)
# Создание записи о машине распознаём по всему вызову: имя эндпоинта стоит строкой выше поля.
СОЗДАНИЕ = re.compile(r"targets?/add|add_target", re.I)
# Не закрепление вызова, а другое дело: запись о цели, умолчание, ссылка, стрелка схемы.
БЕЗОПАСНОЕ = re.compile(
    r"target_id|default_target|targetId|data-target"
    r"|target\s*[=:]\s*['\"]_blank"
    r"|edge\s*=|source\s*=",            # стрелка схемы drawio: source/target — узлы
    re.I)


def нарушения(текст: str) -> list[tuple[int, str]]:
    беды = []
    строки = текст.splitlines()
    for н, строка in enumerate(строки, 1):
        if not ОДИНОЧНОЕ.search(строка) or БЕЗОПАСНОЕ.search(строка):
            continue
        # Окно вызова: массив может стоять соседней строкой.
        окно = "\n".join(строки[max(0, н - 4):н + 3])
        if not ЕСТЬ_МАССИВ.search(окно) and not СОЗДАНИЕ.search(окно):
            беды.append((н, строка.strip()[:100]))
    return беды


def проверить() -> int:
    плохо = 0
    for папка in ПАПКИ:
        корень = КОРЕНЬ / папка
        if not корень.exists():
            continue
        for путь in корень.rglob("*"):
            if путь.suffix not in РАСШИРЕНИЯ or not путь.is_file():
                continue
            if путь.resolve() == pathlib.Path(__file__).resolve():
                continue
            текст = путь.read_text(encoding="utf-8", errors="replace")
            if чужой(путь, текст):
                continue
            for н, строка in нарушения(текст):
                print(f"  ✗ {путь.relative_to(КОРЕНЬ)}:{н} закрепление одиночным полем — "
                      f"нужен массив targets (H107): {строка}")
                плохо += 1
    if плохо:
        print(f"\nНЕ УСПЕХ: закреплений одиночным полем — {плохо}. "
              "Платформа читает массив; одиночное поле тихо уводит работу на устройство "
              "по умолчанию.")
        return 1
    print("Закрепление за машиной везде массивом targets (H107).")
    return 0


def _selftest() -> int:
    провалы = []

    def проба(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка check_device_pinning:")
    проба("одиночное поле ловится",
          len(нарушения('msg = {"target": device}')) == 1)
    проба("массив рядом снимает претензию",
          нарушения('msg.target = d\nmsg.targets = [d]') == [])
    проба("массив в том же вызове снимает претензию",
          нарушения('run(target=d, targets=[d])') == [])
    проба("target_id не считается закреплением",
          нарушения('delete_target(target_id="efe19380")') == [])
    проба("set_default_target не считается закреплением",
          нарушения('set_default_target(device_id=d)') == [])
    проба("ссылка target=\"_blank\" не считается",
          нарушения('<a target="_blank" href="x">') == [])
    проба("создание записи о цели не считается закреплением",
          нарушения('код, т = зов(ЯДРО, "/api/targets/add", {\n    "target": свой,\n    "description": "стенд"})') == [])
    проба("стрелка схемы не считается закреплением",
          нарушения('f\'edge="1" parent="1" source="{откуда}" target="{куда}">\'') == [])
    проба("минифицированный чужой код пропускается",
          чужой(pathlib.Path("editions/x/payload/apps/y/lib.js"), "a".ljust(500, "b")))
    проба("наш обычный файл не считается чужим",
          not чужой(pathlib.Path("tools/new_product.py"), "короткая строка\nещё одна"))
    проба("H107 упомянут в тексте проверки", "H107" in pathlib.Path(__file__).read_text(encoding="utf-8"))

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы — " + "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else проверить())
