#!/usr/bin/env python3
"""Показать продукт в магазине или убрать его оттуда — и сверить результат чтением.

ЗАЧЕМ ОТДЕЛЬНЫЙ ИНСТРУМЕНТ. Публикация — единственное действие, которое видно всем,
и до 16.08.2026 мы считали её необратимой: чат останавливался перед ней и звал
владельца. Оказалось, что снятие с витрины есть, и это тот же адрес с флагом:

    POST /api/listing/{id}/publish   {"published": true|false}

Публикация перестала быть точкой невозврата, но осталась ПУБЛИЧНЫМ действием:
жмёт её по-прежнему владелец. Инструмент нужен, чтобы это делалось командой, а не
кликом в форме, и чтобы результат сверялся чтением, а не ответом.

    python3 tools/set_published.py <listing_id> --показать
    python3 tools/set_published.py <listing_id> --убрать
    python3 tools/set_published.py --мои          # что сейчас на витрине
    python3 tools/set_published.py --selftest

Удаление листинга — другое дело: `DELETE /api/listing/{id}` сносит листинг и ВСЕ
его версии навсегда. Этого инструмент не делает намеренно.
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

ОС = "https://os.extella.ai"


def токен() -> str:
    for путь in (pathlib.Path.home() / ".extella" / "os_token.txt",
                 pathlib.Path.home() / ".extella" / "api_token.txt"):
        if путь.exists() and путь.read_text().strip():
            return путь.read_text().strip()
    raise SystemExit("нет доступа: ожидается ~/.extella/api_token.txt")


def зов(путь, тело=None, метод=None, тк=None):
    д = json.dumps(тело).encode() if тело is not None else None
    з = {"X-Extella-Token": тк or токен()}
    if д:
        з["Content-Type"] = "application/json"
    r = urllib.request.Request(ОС + путь, data=д, headers=з, method=метод)
    try:
        with urllib.request.urlopen(r, timeout=120) as о:
            return о.status, о.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def мои(тк=None) -> list:
    код, тело = зов("/api/my-listings", тк=тк)
    if код != 200:
        raise SystemExit(f"не прочитал свои листинги ({код}): {тело[:120]}")
    return json.loads(тело).get("listings", [])


def состояние(lid: str, тк=None):
    for л in мои(тк):
        if л.get("id") == lid:
            return л
    return None


def переключить(lid: str, показать: bool, тк=None) -> int:
    было = состояние(lid, тк)
    if было is None:
        print("листинга нет у этого токена — публикуют только свои продукты")
        return 1
    if bool(было.get("published")) == показать:
        print(f"«{было['name']}» уже {'на витрине' if показать else 'снят с витрины'} — "
              f"ничего не меняю")
        return 0

    код, тело = зов(f"/api/listing/{lid}/publish", {"published": показать}, "POST", тк)
    if код != 200:
        print(f"платформа отказала ({код}): {тело[:160]}")
        return 1

    # Сверяем чтением: ответ «успех» без перечитывания у нас уже стоил доверия.
    стало = состояние(lid, тк)
    факт = bool(стало and стало.get("published"))
    if факт != показать:
        print(f"ОТВЕТ И ФАКТ РАСХОДЯТСЯ: платформа сказала «успех», а published={факт}")
        return 1
    print(f"«{стало['name']}»: {'показан в магазине' if показать else 'убран с витрины'} "
          f"· проверено чтением")
    if показать:
        print("  помни: у опубликованного листинга КАЖДАЯ новая версия уходит в магазин "
              "сразу (H20)")
    return 0


def _selftest() -> int:
    """Проверяем разбор состояния и решение «менять/не менять» без единого запроса."""
    провалы = []
    listings = [{"id": "A", "name": "Уже на витрине", "published": 1},
                {"id": "B", "name": "Предрелиз", "published": 0}]

    def случай(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    глобально = globals()
    исходная = глобально["мои"]
    глобально["мои"] = lambda тк=None: listings
    try:
        print("Самопроверка set_published:")
        случай("чужой листинг не трогаем", переключить("НЕТ", True) == 1)
        случай("повтор публикации ничего не делает", переключить("A", True) == 0)
        случай("повтор снятия ничего не делает", переключить("B", False) == 0)

        # Платформа ответила успехом, а факт не изменился — обязаны заметить.
        вызовы = []
        глобально["зов"] = lambda путь, тело=None, метод=None, тк=None: (
            вызовы.append(путь) or (200, '{"status":"ok"}'))
        случай("расхождение ответа и факта ловится", переключить("B", True) == 1)
        случай("адрес именно /publish", вызовы and вызовы[-1].endswith("/publish"))
    finally:
        глобально["мои"] = исходная

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--мои" in sys.argv:
        for л in мои():
            print(f"  {'НА ВИТРИНЕ' if л.get('published') else 'предрелиз '} "
                  f"{str(л.get('name'))[:36]:36} {л.get('id')}")
        sys.exit(0)
    аргументы = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not аргументы or not ("--показать" in sys.argv or "--убрать" in sys.argv):
        print(__doc__)
        sys.exit(2)
    sys.exit(переключить(аргументы[0], "--показать" in sys.argv))
