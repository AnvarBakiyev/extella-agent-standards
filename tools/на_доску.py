#!/usr/bin/env python3
"""Универсальный рисовальщик: любая из пяти форм → доска схем.

ЗАЧЕМ ОТДЕЛЬНО ОТ ИСТОЧНИКОВ. Это вторая половина замысла «N+M вместо N×M»: доска
не знает ни одного приложения по имени, а приложение не знает доски. Между ними —
только словарь `формы.py`. Появится пятисотое приложение — рисовать его научится
никто: оно уже умеет, если умеет привести своё содержимое к одной из пяти форм.

ДВА ПРАВИЛА ЗАПИСИ, и оба про чужую работу:
  1. Агент пишет только свои элементы — с меткой `ext_<источник>_` в идентификаторе.
     Нарисованного человеком он не трогает никогда.
  2. Повтор ЗАМЕНЯЕТ прошлый рисунок ТОГО ЖЕ источника, а не копит слои. Рисунки
     других источников при этом остаются: Астра не стирает договор юриста.

Образцы элементов вшиты literal'ами, а не берутся с доски. Прежний инструмент
требовал, чтобы на доске уже лежали прямоугольник и подпись, — на чистой доске он
отказывал, и это выглядело поломкой, хотя было отсутствием образца.

    python3 tools/на_доску.py --файл форма.json --источник астра
    python3 tools/на_доску.py --пример связи --источник проба
    python3 tools/на_доску.py --стереть --источник астра
"""

import argparse
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ, проверить, пример, строки_пункта, по_человечески  # noqa: E402

ПОРТ = 34786
ПРЕФИКС = "ext_"

# Палитра Extella. Цвет мимо палитры — дефект, а не мелочь.
ЧЕРНИЛА, СЕРЫЙ, БРОНЗА, ПЕТРОЛЬ = "#1a1a1a", "#868e96", "#c57e33", "#2f6b66"
ФОН_КАРТЫ, ФОН_ГЛАВНОЙ = "#f5f3ee", "#fcf7f1"

ШИР, ВЫС, ЗАЗОР = 300, 132, 28      # карточка списка и расстояние между карточками
КОЛОНОК = 3

_ФИГУРА = {"type": "rectangle", "angle": 0, "strokeColor": ЧЕРНИЛА,
           "backgroundColor": ФОН_КАРТЫ, "fillStyle": "solid", "strokeWidth": 1,
           "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
           "frameId": None, "roundness": {"type": 3}, "boundElements": [],
           "link": None, "locked": False}
_ТЕКСТ = {"type": "text", "angle": 0, "strokeColor": ЧЕРНИЛА,
          "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1,
          "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
          "frameId": None, "roundness": None, "boundElements": [], "link": None,
          "locked": False, "fontSize": 16, "fontFamily": 5, "textAlign": "left",
          "verticalAlign": "top", "containerId": None, "autoResize": False,
          "lineHeight": 1.25}
_СТРЕЛКА = {"type": "arrow", "angle": 0, "strokeColor": ПЕТРОЛЬ,
            "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1,
            "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": {"type": 2}, "boundElements": [],
            "link": None, "locked": False, "startBinding": None, "endBinding": None,
            "startArrowhead": None, "endArrowhead": "arrow"}


def метка(источник: str) -> str:
    """Метка источника. Подчёркивание внутри имени запрещено намеренно.

    Замер 19.08.2026: источник «астра» стёр рисунок источника «астра_новая» —
    его метка `ext_астра_` оказалась началом чужой `ext_астра_новая_`. Это ровно
    тот класс, от которого метки и заводились: один источник затирает другой.
    Разделитель обязан быть невозможен внутри имени, иначе граница не граница.
    """
    чистое = "".join(с if (с.isalnum() or с == "-") else "-" for с in источник.lower())
    return f"{ПРЕФИКС}{чистое.strip('-') or 'агент'}_"


def _эл(шаблон: dict, источник: str, **поля) -> dict:
    э = dict(шаблон)
    э.update(поля)
    э["id"] = f"{метка(источник)}{random.randint(10**11, 10**12)}"
    э["seed"] = random.randint(1, 2 ** 31)
    э["versionNonce"] = random.randint(1, 2 ** 31)
    э["version"] = 1
    э["updated"] = int(time.time() * 1000)
    э["isDeleted"] = False
    return э


def перенос(текст: str, знаков: int) -> str:
    """Мягкий перенос по словам. Excalidraw сам не переносит — он обрежет."""
    вывод, строка = [], ""
    for слово in str(текст).split():
        if len(строка) + len(слово) + 1 > знаков and строка:
            вывод.append(строка)
            строка = слово
        else:
            строка = f"{строка} {слово}".strip()
    if строка:
        вывод.append(строка)
    return "\n".join(вывод)


def _подпись(источник: str, x, y, ш, текст, кегль=16, цвет=ЧЕРНИЛА) -> dict:
    строки = текст.count("\n") + 1
    return _эл(_ТЕКСТ, источник, x=x, y=y, width=ш, height=int(кегль * 1.25 * строки) + 4,
               fontSize=кегль, strokeColor=цвет, text=текст, originalText=текст)


def шапка(д: dict, источник: str, лев: float, верх: float) -> tuple:
    """Заголовок, подпись источника и время. Рисунок без подписи — слух."""
    эл = [_подпись(источник, лев, верх, 900, д["title"], 28)]
    y = верх + 44
    if д.get("caption"):
        эл.append(_подпись(источник, лев, y, 900, перенос(д["caption"], 90), 16, СЕРЫЙ))
        y += 26
    след = (f"нарисовано агентом · источник: {источник} · "
            f"{time.strftime('%d.%m.%Y %H:%M')}")
    эл.append(_подпись(источник, лев, y, 900, след, 13, СЕРЫЙ))
    return эл, y + 40


def рисовать(д: dict, источник: str, лев: float, верх: float) -> list:
    """Форма → элементы. Раскладка простая нарочно: её читают глазами."""
    эл, y = шапка(д, источник, лев, верх)
    форма = д["form"]

    if форма == "number":
        эл.append(_эл(_ФИГУРА, источник, x=лев, y=y, width=560, height=150,
                      backgroundColor=ФОН_ГЛАВНОЙ, strokeColor=БРОНЗА))
        эл.append(_подпись(источник, лев + 28, y + 34, 500, str(д["value"]), 40, БРОНЗА))
        return эл

    if форма == "list":
        for i, п in enumerate(д["rows"]):
            кол, ряд = i % КОЛОНОК, i // КОЛОНОК
            x, yy = лев + кол * (ШИР + ЗАЗОР), y + ряд * (ВЫС + ЗАЗОР)
            эл.append(_эл(_ФИГУРА, источник, x=x, y=yy, width=ШИР, height=ВЫС))
            строки = строки_пункта(п, форма)
            эл.append(_подпись(источник, x + 16, yy + 14, ШИР - 32,
                               перенос(строки[0], 26), 18))
            if строки[1:]:
                эл.append(_подпись(источник, x + 16, yy + 46, ШИР - 32,
                                   "\n".join(строки[1:])[:260], 14, "#3d3a35"))
        return эл

    if форма == "steps":
        for i, п in enumerate(д["steps"]):
            кол, ряд = i % КОЛОНОК, i // КОЛОНОК
            x, yy = лев + кол * (ШИР + 80), y + ряд * (ВЫС + ЗАЗОР)
            эл.append(_эл(_ФИГУРА, источник, x=x, y=yy, width=ШИР, height=ВЫС))
            эл.append(_подпись(источник, x + 16, yy + 14, ШИР - 32,
                               f"{i + 1}. " + перенос(п["name"], 24), 18))
            if п.get("caption"):
                эл.append(_подпись(источник, x + 16, yy + 50, ШИР - 32,
                                   перенос(п["caption"], 30), 14, "#3d3a35"))
            # Стрелка только внутри ряда: перенос строки рисуется разрывом,
            # а не диагональю через полдоски.
            if i + 1 < len(д["steps"]) and кол + 1 < КОЛОНОК:
                эл.append(_эл(_СТРЕЛКА, источник, x=x + ШИР + 12, y=yy + ВЫС / 2,
                              width=56, height=0, points=[[0, 0], [56, 0]]))
        return эл

    if форма == "links":
        for i, п in enumerate(д["links"]):
            yy = y + i * (92 + 20)
            эл.append(_эл(_ФИГУРА, источник, x=лев, y=yy, width=380, height=92))
            эл.append(_подпись(источник, лев + 16, yy + 16, 348,
                               перенос(п["from"], 32), 16))
            эл.append(_эл(_СТРЕЛКА, источник, x=лев + 396, y=yy + 46,
                          width=96, height=0, points=[[0, 0], [96, 0]]))
            if п.get("caption"):
                эл.append(_подпись(источник, лев + 396, yy + 16, 96,
                                   перенос(п["caption"], 14), 12, ПЕТРОЛЬ))
            эл.append(_эл(_ФИГУРА, источник, x=лев + 508, y=yy, width=380, height=92,
                          backgroundColor=ФОН_ГЛАВНОЙ, strokeColor=БРОНЗА))
            эл.append(_подпись(источник, лев + 524, yy + 16, 348,
                               перенос(п["to"], 32), 16))
        return эл

    if форма == "document":
        yy = y
        for п in д["sections"]:
            текст = перенос(п["text"], 96)
            высота = 46 + (текст.count("\n") + 1) * 20 + 16
            эл.append(_эл(_ФИГУРА, источник, x=лев, y=yy, width=900, height=высота))
            эл.append(_подпись(источник, лев + 20, yy + 14, 860, п["name"], 18, ПЕТРОЛЬ))
            эл.append(_подпись(источник, лев + 20, yy + 44, 860, текст, 15, "#3d3a35"))
            yy += высота + 18
        return эл

    raise Отказ(f"рисовальщик не знает форму «{форма}»")


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
        raise Отказ(f"доска не отвечает на порту {порт} ({е}). "
                    f"Проверить: launchctl list | grep ai.extella.board")


def положить(д: dict | None, источник: str, порт: int, стереть: bool) -> int:
    моя_метка = метка(источник)
    было = хранилище(порт)
    эл = json.loads(было.get("excalidraw") or "[]")
    свои = [e for e in эл if str(e.get("id", "")).startswith(моя_метка)]
    прочие = [e for e in эл if not str(e.get("id", "")).startswith(моя_метка)]

    if свои:
        print(f"  прошлый рисунок источника «{источник}»: {len(свои)} элементов — "
              f"заменяю, не накапливаю")
    if стереть:
        новые = прочие
        print(f"  стёрто элементов источника «{источник}»: {len(свои)}")
    else:
        живые = [e for e in прочие if not e.get("isDeleted")]
        низ = max((e.get("y", 0) + (e.get("height") or 0) for e in живые), default=0)
        лев = min((e.get("x", 0) for e in живые), default=0)
        новые = прочие + рисовать(д, источник, лев, низ + 240 if живые else 0)
        print(f"  нарисовано элементов: {len(новые) - len(прочие)}")

    хранилище(порт, {"ключ": "excalidraw",
                     "value": json.dumps(новые, ensure_ascii=False)})
    print(f"  ✓ доска обновлена: было {len(эл)}, стало {len(новые)}")
    print("  Откройте доску заново — она перечитает работу сама.")
    return 0


def selftest() -> int:
    ошибки = []

    # Все пять форм обязаны рисоваться. Форма, которую словарь принимает, а
    # рисовальщик не умеет, — это дыра ровно посередине замысла.
    for ф in ("list", "number", "steps", "links", "document"):
        try:
            эл = рисовать(проверить(пример(ф)), "проба", 0, 0)
            if not эл:
                ошибки.append(f"форма «{ф}» дала пустой рисунок")
        except Exception as о:
            ошибки.append(f"форма «{ф}» не рисуется: {о}")
    if not ошибки:
        print("  ✓ все пять форм рисуются")

    эл = рисовать(проверить(пример("list")), "астра", 0, 0)
    чужие = [e for e in эл if not e["id"].startswith("ext_астра_")]
    if чужие:
        ошибки.append(f"{len(чужие)} элементов без метки источника — их нечем заменить")
    else:
        print("  ✓ каждый элемент помечен источником: чужое не трогаем, своё заменяем")

    # Метки разных источников не должны совпадать по префиксу — иначе Астра
    # сотрёт договор юриста при следующем прогоне.
    # Пара «астра» / «астра_новая» — не выдуманный случай: на ней это и сломалось.
    пары = (("астра", "юрист"), ("астра", "астра_новая"), ("а", "а-б"))
    беда = [f"{о1}/{о2}" for о1, о2 in пары
            if метка(о1) == метка(о2) or метка(о2).startswith(метка(о1))
            or метка(о1).startswith(метка(о2))]
    if беда:
        ошибки.append(f"метки источников вкладываются друг в друга ({', '.join(беда)}) — "
                      f"один источник сотрёт рисунок другого")
    else:
        print("  ✓ метки источников не вкладываются: Астра не стирает ни юриста, "
              "ни свою же вторую витрину")
    if "_" in метка("астра_новая")[len(ПРЕФИКС):-1]:
        ошибки.append("разделитель попал внутрь имени — граница снова не граница")

    if перенос("а" * 3 + " " + "б" * 3 + " " + "в" * 3, 8) != "ааа ббб\nввв":
        ошибки.append("перенос по словам сломан")
    else:
        print("  ✓ длинный текст переносится по словам, а не обрезается")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Любая из пяти форм → доска схем")
    р.add_argument("--файл", help="файл с формой (json)")
    р.add_argument("--пример", metavar="ФОРМА", help="нарисовать пример формы")
    р.add_argument("--источник", default="агент",
                   help="чей это рисунок: по метке он заменяется при повторе")
    р.add_argument("--порт", type=int, default=ПОРТ)
    р.add_argument("--стереть", action="store_true", help="убрать рисунки источника")
    р.add_argument("--сухой", action="store_true", help="показать, но не писать")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    try:
        if а.стереть:
            return положить(None, а.источник, а.порт, True)
        if а.файл:
            д = проверить(json.loads(pathlib.Path(а.файл).read_text()))
        elif а.пример:
            д = проверить(пример(а.пример))
        else:
            р.print_help()
            return 0
        print(f"\nФорма «{по_человечески(д['form'])}» · {д['title']} · источник «{а.источник}»")
        if а.сухой:
            print(f"  СУХОЙ ПРОГОН: нарисовал бы {len(рисовать(д, а.источник, 0, 0))} "
                  f"элементов, на доску не писал")
            return 0
        return положить(д, а.источник, а.порт, False)
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
