#!/usr/bin/env python3
"""Плитка приложения на стол ОС — честным путём, через desktop-state.

ЗАЧЕМ. Программная установка (purchase-stream / переустановить) создаёт
ПОКУПКУ, но не плитку: плитки стола рисуются из отдельного серверного
состояния /api/desktop-state. Замер 20.08.2026 («Пульт CEO»): шесть покупок
идеальны, трёх плиток нет — одинаково в браузере и приложении. Полный разбор:
docs/DESKTOP_STATE.md.

ПРАВИЛА, ЗАШИТЫЕ ЗДЕСЬ:
- бэкап состояния целиком ПЕРЕД записью (POST пишет state целиком — криво
  собранное состояние это снесённый стол человека);
- только добавлять, чужие слои не трогать;
- идемпотентность: ярлык с тем же listing_id не дублируется;
- после записи перечитать и убедиться, что ярлык на месте.

    python3 tools/ярлык_на_стол.py <listing_id> --имя "CEO · Маркетинг" [--x 900 --y 300]
    python3 tools/ярлык_на_стол.py --selftest
"""

import argparse
import json
import pathlib
import sys
import time

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from platform_client import ОС, Отказ, запрос, как_json  # noqa: E402

БЭКАПЫ = pathlib.Path.home() / "extella-cabinet" / "записи"


def добавить_ярлык(состояние: dict, лид: str, имя: str,
                   x: int | None, y: int | None) -> tuple[dict, str | None]:
    """Чистая сборка: вернуть (новое состояние, sid) или (прежнее, None) если уже есть.

    Тип плитки — ПРЯМАЯ ССЫЛКА (state.shortcuts, url на /app-page/{lид}/):
    открывает приложение окном сразу. НЕ appShortcuts: тот тип без агента
    открывает карточку магазина — замер 20.08.2026, «странно открываются»."""
    адрес = f"https://os.extella.ai/app-page/{лид}/"
    ссылки = состояние.setdefault("shortcuts", {})
    for з in ссылки.values():
        if (з or {}).get("url") == адрес:
            return состояние, None                     # идемпотентность
    sid = f"link_{лид[:8]}"
    while sid in ссылки:                               # коллизия ключа — удлиняем
        sid += "x"
    ссылки[sid] = {"name": имя, "url": адрес}
    if x is not None and y is not None:
        состояние.setdefault("pos", {})[sid] = {"x": x, "y": y}
    return состояние, sid


def поставить(лид: str, имя: str, x: int | None, y: int | None) -> int:
    код, т = запрос(ОС, "/api/desktop-state")
    if код != 200:
        raise Отказ(f"стол не отдал состояние: HTTP {код}")
    ответ = как_json(т, "состояние стола")
    состояние = ответ.get("state") or {}

    БЭКАПЫ.mkdir(parents=True, exist_ok=True)
    бэкап = БЭКАПЫ / f"desktop_state_бэкап_{int(time.time())}.json"
    бэкап.write_text(json.dumps(ответ, ensure_ascii=False, indent=1))
    print(f"  бэкап состояния: {бэкап}")

    состояние, sid = добавить_ярлык(состояние, лид, имя, x, y)
    if sid is None:
        print(f"✓ ярлык на {лид[:8]}… уже стоит — не дублирую")
        return 0

    код, т = запрос(ОС, "/api/desktop-state", тело={"state": состояние})
    if код != 200:
        raise Отказ(f"стол не принял запись: HTTP {код} · {т[:120]}")

    код, т = запрос(ОС, "/api/desktop-state")
    свежее = как_json(т, "перечитка").get("state") or {}
    if sid not in (свежее.get("appShortcuts") or {}):
        raise Отказ("записал, а перечитка ярлыка не видит — возможно, открытый "
                    "стол перекрыл правку своим сохранением; повторите")
    print(f"✓ плитка «{имя}» поставлена ({sid}). Открытые столы подтянут сами.")
    return 0


def selftest() -> int:
    ошибки = []
    с = {"pos": {"старое": {"x": 1, "y": 2}}, "folders": {"f1": {}}, "trash": ["т"]}
    с2, sid = добавить_ярлык(dict(с), "лид-123456789", "Имя", 10, 20)
    if not sid or с2["shortcuts"][sid] != {"name": "Имя",
            "url": "https://os.extella.ai/app-page/лид-123456789/"}:
        ошибки.append("ярлык не добавился или не прямой ссылкой")
    elif с2["pos"]["старое"] != {"x": 1, "y": 2} or с2["folders"] != {"f1": {}} or с2["trash"] != ["т"]:
        ошибки.append("чужие слои состояния тронуты — это снесённый стол")
    else:
        print("  ✓ ярлык добавляется, чужие слои нетронуты")

    _, sid2 = добавить_ярлык(с2, "лид-123456789", "Имя2", None, None)
    if sid2 is not None:
        ошибки.append("дубль ярлыка на тот же listing_id — плитки размножатся")
    else:
        print("  ✓ повтор на тот же listing_id честно отказывает")

    с3, sid3 = добавить_ярлык(с2, "лид-999", "Без места", None, None)
    if sid3 in (с3.get("pos") or {}):
        ошибки.append("без --x/--y позиция не должна писаться (стол сам разложит)")
    else:
        print("  ✓ без координат позицию решает стол")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Плитка приложения на стол ОС")
    р.add_argument("listing_id", nargs="?")
    р.add_argument("--имя", dest="имя", default="")
    р.add_argument("--x", type=int, default=None)
    р.add_argument("--y", type=int, default=None)
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    if not а.listing_id or not а.имя:
        print(__doc__)
        return 2
    if (а.x is None) != (а.y is None):
        print("ОТКАЗ: --x и --y задаются вместе либо не задаются вовсе", file=sys.stderr)
        return 1
    try:
        return поставить(а.listing_id, а.имя.strip()[:60], а.x, а.y)
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
