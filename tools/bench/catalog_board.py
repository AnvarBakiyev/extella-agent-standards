#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Доска-каталог: прогнать стенд приёмки по всем нашим приложениям разом.

Открывает каждый листинг как ПОСТОРОННИЙ покупатель на живом os.extella.ai
(режим проверенного зелёного из check_opens_elsewhere), судит экран по яркости и,
где есть крючки data-testid, прокликивает — и сводит всё в одну таблицу
зелёный/жёлтый/красный на приложение.

Запускать НА СТЕНДЕ (VPS ~/extella-bench), где живёт Chrome и same_origin_probe:

    python3 catalog_board.py --apps apps.json            # все
    python3 catalog_board.py --apps apps.json --limit 4  # первые 4 (проверка)
    python3 catalog_board.py --apps apps.json --пауза 8  # пауза между прогонами

apps.json — список [{"имя": "...", "id": "<listing_id>"}]. Список публичных
листингов готовит владелец на своей машине (там его my-listings) и кладёт рядом.

Между прогонами держим паузу: 20+ браузерных сессий подряд клали VPS (замер).
Красный хотя бы у одного → код выхода 1.
"""
import argparse
import json
import pathlib
import sys
import time
import traceback

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ЗДЕСЬ))


def прогнать_один(лид: str) -> dict:
    """Один листинг → вердикт стенда. Ошибка прогона — не падение доски."""
    import same_origin_probe
    import check_opens_elsewhere as chk
    сб = same_origin_probe.собрать(лид)
    if сб.get("ошибка"):
        return {"цвет": "серый", "блок": False, "жёсткие": [сб["ошибка"]],
                "мягкие": [], "проклик": []}
    std = chk.измерить_плотность(сб["папка"] / "окно_на_домене.png")
    в = chk.классифицировать_домен(std, сб["конс"],
                                   chk.видимый_текст(сб["dom"]), сб.get("проклик"))
    в["папка"] = str(сб["папка"])
    return в


ЗНАЧОК = {"зелёный": "🟢", "жёлтый": "🟡", "красный": "🔴", "серый": "⚪"}
ПОРЯДОК = {"красный": 0, "серый": 1, "жёлтый": 2, "зелёный": 3}


def main(argv) -> int:
    р = argparse.ArgumentParser()
    р.add_argument("--apps", required=True, help="json со списком {имя,id}")
    р.add_argument("--limit", type=int, default=0, help="прогнать только первые N")
    # Латинский --pause как алиас: под cron локаль бывает POSIX, кириллический
    # флаг через неё лучше не гонять.
    р.add_argument("--пауза", "--pause", dest="пауза", type=int, default=8,
                   help="секунд между прогонами")
    р.add_argument("--out", default="catalog_board.json")
    а = р.parse_args(argv)

    приложения = json.loads(pathlib.Path(а.apps).read_text(encoding="utf-8"))
    if а.limit:
        приложения = приложения[: а.limit]

    доска = []
    for i, п in enumerate(приложения, 1):
        имя, лид = п.get("имя") or п.get("name") or лид_коротко(п), п["id"]
        print(f"[{i}/{len(приложения)}] {имя} …", flush=True)
        try:
            в = прогнать_один(лид)
        except Exception as беда:                               # noqa: BLE001
            в = {"цвет": "серый", "блок": False,
                 "жёсткие": [f"прогон упал: {str(беда)[:160]}"], "мягкие": [],
                 "проклик": []}
            traceback.print_exc()
        # «проклик» бывает и списком словарей (кнопка+отклик), и списком строк-
        # описаний — считаем кнопками только структурированные записи.
        клики = [к for к in (в.get("проклик") or []) if isinstance(к, dict)]
        ответили = len([к for к in клики if к.get("откликнулось")])
        доска.append({"имя": имя, "id": лид, "цвет": в.get("цвет"),
                      "блок": в.get("блок"), "жёсткие": в.get("жёсткие", []),
                      "мягкие": в.get("мягкие", []),
                      "кнопок": len(клики), "откликнулось": ответили})
        if i < len(приложения):
            time.sleep(а.пауза)

    доска.sort(key=lambda с: (ПОРЯДОК.get(с["цвет"], 1), с["имя"]))
    print("\n" + "=" * 60 + "\nДОСКА-КАТАЛОГ\n" + "=" * 60)
    for с in доска:
        крючки = (f"  клики {с['откликнулось']}/{с['кнопок']}"
                  if с["кнопок"] else "  без крючков")
        print(f"{ЗНАЧОК.get(с['цвет'],'⚪')} {с['имя']:34}{крючки}")
        for б in с["жёсткие"][:2]:
            print(f"      · {б[:90]}")
    красные = [с for с in доска if с["цвет"] == "красный"]
    print(f"\nитог: 🔴 {len(красные)}  "
          f"🟡 {len([с for с in доска if с['цвет']=='жёлтый'])}  "
          f"🟢 {len([с for с in доска if с['цвет']=='зелёный'])}  "
          f"⚪ {len([с for с in доска if с['цвет']=='серый'])}")
    pathlib.Path(а.out).write_text(
        json.dumps(доска, ensure_ascii=False, indent=2), encoding="utf-8")
    print("сохранено:", а.out)
    return 1 if красные else 0


def лид_коротко(п: dict) -> str:
    return (п.get("id") or "?")[:12]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
