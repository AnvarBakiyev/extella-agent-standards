#!/usr/bin/env python3
"""Третий получатель: любая из пяти форм → лист таблицы.

ПЕРЕВОРОТ СВЯЗКИ. До этого таблица была источником — агент её читал. Теперь она
и получатель: «возьми из астры и положи в таблицу». Симметрия не для красоты:
таблица — единственный получатель, в котором человек может ПРОДОЛЖИТЬ работу
руками — дописать колонку, навесить формулы, посчитать своё.

ПРАВИЛО ЗАПИСИ — то же, что на доске, и оно не обсуждается:
  агент пишет ТОЛЬКО свой лист «От агента · <источник>» (index ext_<источник>);
  листы человека не трогаются никогда; повтор заменяет свой лист, а не копит.
Испортить человеку смету — хуже любого отказа.

    python3 tools/в_таблицу.py --файл форма.json --источник астра
    python3 tools/в_таблицу.py --пример список --источник проба
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ, проверить, пример, по_человечески  # noqa: E402

ПОРТ = 34787                     # служба Таблицы (ai.extella.tablica)
КЛЮЧ = "luckysheet.sheets"
МЕТКА = "ext_"

ЗОЛОТО_ФОН, ЧЕРНИЛА = "#FCF7F1", "#1a1a1a"


def _кл(r, c, значение, шапка=False):
    """Одна клетка в формате Luckysheet."""
    число = isinstance(значение, (int, float)) and not isinstance(значение, bool)
    v = {"v": значение, "m": str(значение),
         "ct": {"fa": "General", "t": "n" if число else "g"}}
    if шапка:
        v.update({"bl": 1, "bg": ЗОЛОТО_ФОН, "fc": ЧЕРНИЛА})
    return {"r": r, "c": c, "v": v}


def клетки(д: dict, источник: str) -> list:
    """Форма → клетки листа. Первая строка — шапка: тот же канон, что при чтении."""
    форма, кл = д["form"], []

    if форма == "number":
        кл.append(_кл(0, 0, д["title"], шапка=True))
        кл.append(_кл(1, 0, д["value"]))
    elif форма == "list":
        # Колонки — в порядке первого появления: источник знает, что важнее.
        колонки = []
        for с in д["rows"]:
            for к in (с.get("fields") or {}):
                if к not in колонки:
                    колонки.append(к)
        кл.append(_кл(0, 0, "Название", шапка=True))
        for j, к in enumerate(колонки, 1):
            кл.append(_кл(0, j, к, шапка=True))
        for i, с in enumerate(д["rows"], 1):
            кл.append(_кл(i, 0, с["name"]))
            for j, к in enumerate(колонки, 1):
                if к in (с.get("fields") or {}):
                    кл.append(_кл(i, j, с["fields"][к]))
    elif форма == "steps":
        for j, з in enumerate(("№", "Шаг", "Пояснение")):
            кл.append(_кл(0, j, з, шапка=True))
        for i, ш in enumerate(д["steps"], 1):
            кл.append(_кл(i, 0, i))
            кл.append(_кл(i, 1, ш["name"]))
            if ш.get("caption"):
                кл.append(_кл(i, 2, ш["caption"]))
    elif форма == "links":
        for j, з in enumerate(("От", "К", "Подпись")):
            кл.append(_кл(0, j, з, шапка=True))
        for i, с in enumerate(д["links"], 1):
            кл.append(_кл(i, 0, с["from"]))
            кл.append(_кл(i, 1, с["to"]))
            if с.get("caption"):
                кл.append(_кл(i, 2, с["caption"]))
    elif форма == "document":
        for j, з in enumerate(("Раздел", "Текст")):
            кл.append(_кл(0, j, з, шапка=True))
        for i, р in enumerate(д["sections"], 1):
            кл.append(_кл(i, 0, р["name"]))
            кл.append(_кл(i, 1, р["text"]))
    else:
        raise Отказ(f"получатель-таблица не знает форму «{форма}»")

    низ = max(к["r"] for к in кл) + 2
    след = (f"собрано агентом · источник: {источник} · {time.strftime('%d.%m.%Y %H:%M')}"
            + (f" · {д['caption']}" if д.get("caption") else ""))
    кл.append(_кл(низ, 0, след))
    return кл


def лист(д: dict, источник: str, порядок: int) -> dict:
    имя = f"От агента · {источник}"[:28]
    return {"name": имя, "index": МЕТКА + источник, "order": порядок,
            "status": 0,               # активным остаётся лист человека
            "celldata": клетки(д, источник), "config": {},
            "row": max(40, len(клетки(д, источник))), "column": 26}


def хранилище(порт: int, тело: dict | None = None) -> dict:
    адрес = f"http://127.0.0.1:{порт}/_extella_storage"
    try:
        if тело is None:
            with urllib.request.urlopen(адрес, timeout=15) as о:
                return json.loads(о.read().decode())
        з = urllib.request.Request(
            адрес, data=json.dumps(тело, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(з, timeout=25) as о:
            return json.loads(о.read().decode())
    except (urllib.error.URLError, OSError) as е:
        raise Отказ(f"таблица не отвечает на порту {порт} ({е}). "
                    f"Проверить: launchctl list | grep ai.extella.tablica")


def сложить(старые: list, новый: dict, источник: str) -> list:
    """Заменить СВОЙ лист, не тронув ни одного чужого. Единственное место записи."""
    мой = МЕТКА + источник
    чужие = [л for л in старые if str(л.get("index")) != мой]
    if len(чужие) != len(старые):
        pass                        # прошлый свой лист заменён, не скопирован
    if not any(not str(л.get("index", "")).startswith(МЕТКА) for л in чужие):
        # Все листы вдруг агентские — так не бывает, у человека всегда есть свой.
        # Скорее хранилище прочиталось битым: писать поверх нельзя.
        raise Отказ("в таблице не видно ни одного листа человека — "
                    "не пишу, чтобы не затереть чужую работу битым чтением")
    новый["order"] = len(чужие)
    return чужие + [новый]


def работа(д: dict, источник: str, порт: int, сухой: bool) -> int:
    print(f"\nФорма «{по_человечески(д['form'])}» · {д['title']} · источник «{источник}» → лист таблицы")
    if сухой:
        print(f"  СУХОЙ ПРОГОН: положил бы {len(клетки(д, источник))} клеток "
              f"в лист «От агента · {источник}»")
        return 0
    было = хранилище(порт)
    листы = json.loads(было.get(КЛЮЧ) or "[]")
    if not листы:
        raise Отказ("таблица пуста — откройте её хотя бы раз, чтобы появился лист")
    свои_было = sum(1 for л in листы if str(л.get("index")) == МЕТКА + источник)
    новые = сложить(листы, лист(д, источник, len(листы)), источник)
    # Поле хранилища — «значение» (не «value»): cabinet_server принимает только
    # его, при «value» ответ {"сохранено":true}, но ключ пишется пустым и запись
    # молча теряется (в_таблицу рапортует «добавлен лист», а storage пуст).
    # Доска схем (на_доску.py) всегда писала «значение» и работала. Замер 21.08.2026.
    хранилище(порт, {"ключ": КЛЮЧ,
                     "значение": json.dumps(новые, ensure_ascii=False)})
    print(f"  {'заменён прошлый лист агента' if свои_было else 'добавлен лист'} "
          f"«От агента · {источник}» · листов у человека не тронуто: "
          f"{sum(1 for л in новые if not str(л.get('index','')).startswith(МЕТКА))}")
    print("  Откройте таблицу — лист появится вкладкой внизу.")
    return 0


def selftest() -> int:
    ошибки = []

    for ф in ("list", "number", "steps", "links", "document"):
        try:
            кл = клетки(проверить(пример(ф)), "проба")
            if not кл:
                ошибки.append(f"форма «{ф}» дала пустой лист")
        except Exception as о:
            ошибки.append(f"форма «{ф}» не кладётся в лист: {о}")
    if not ошибки:
        print("  ✓ все пять форм кладутся в лист")

    кл = клетки(проверить(пример("list")), "проба")
    шапка = [к for к in кл if к["r"] == 0]
    if not all(к["v"].get("bl") for к in шапка):
        ошибки.append("первая строка не шапка — при обратном чтении паспорт потеряет поля")
    else:
        print("  ✓ первая строка — шапка: лист агента можно ЧИТАТЬ обратно тем же паспортом")

    человеческий = {"name": "Смета", "index": "0", "celldata": [{"r": 0, "c": 0}]}
    старый_агентский = {"name": "От агента · проба", "index": "ext_проба", "celldata": []}
    чужой_агентский = {"name": "От агента · астра", "index": "ext_астра", "celldata": []}
    итог = сложить([человеческий, старый_агентский, чужой_агентский],
                   лист(проверить(пример("number")), "проба", 0), "проба")
    имена = [л["index"] for л in итог]
    if "0" not in имена or "ext_астра" not in имена:
        ошибки.append(f"затронуты чужие листы: {имена}")
    elif имена.count("ext_проба") != 1:
        ошибки.append("свой лист скопился, а не заменился")
    else:
        print("  ✓ лист человека и лист другого агента не тронуты; свой — заменён")

    try:
        сложить([старый_агентский], лист(проверить(пример("number")), "проба", 0), "проба")
        ошибки.append("запись прошла при невидимых листах человека — риск затирания")
    except Отказ:
        print("  ✓ не видно листов человека → отказ, а не запись поверх битого чтения")

    с_числами = проверить({"форма": "list", "title": "х",
                           "rows": [{"name": "Алматы", "fields": {"долг": 4850000}}]})
    числ = [к for к in клетки(с_числами, "п") if к["v"]["ct"]["t"] == "n"]
    if not числ:
        ошибки.append("числа не помечены числами — формулы человека по ним не посчитают")
    else:
        print("  ✓ числа лежат числами: человек может навесить свои формулы")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Любая из пяти форм → лист таблицы")
    р.add_argument("--файл")
    р.add_argument("--пример", metavar="ФОРМА")
    р.add_argument("--источник", default="агент")
    р.add_argument("--порт", type=int, default=ПОРТ)
    р.add_argument("--сухой", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    try:
        if а.файл:
            д = проверить(json.loads(pathlib.Path(а.файл).read_text()))
        elif а.пример:
            д = проверить(пример(а.пример))
        else:
            р.print_help()
            return 0
        return работа(д, а.источник, а.порт, а.сухой)
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
