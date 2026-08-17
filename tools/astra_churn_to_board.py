#!/usr/bin/env python3
"""Астра Телеком → Доска схем: картина оттока рисуется на доске сама.

ЗАЧЕМ. У доски есть структура, но нет данных. У Астры есть данные, но нет
структуры. Поодиночке это рисовалка и отчёт; вместе — схема бизнеса, которая
обновляется сама и рядом с которой человек дорисовывает своё.

Это первый мост между двумя приложениями магазина, и он показывает приём целиком:
приложения не разговаривают между собой (окна ОС изолированы намеренно) — их
соединяет агент на устройстве, читая данные одного и записывая работу другого.

Что делает:
  * читает витрину `gold_churn_analysis` озера Астры (DuckDB, синтетика);
  * считает ДЕТЕРМИНИРОВАННО, без ИИ: потерянные деньги = ушедшие × LTV;
  * рисует на доске заголовок, сводку и карточки городов, цвет — по тяжести;
  * при повторе ЗАМЕНЯЕТ свой прошлый рисунок, а не кладёт второй поверх.

Работу человека не трогает: свои элементы помечены и живут отдельно.

    python3 tools/astra_churn_to_board.py
    python3 tools/astra_churn_to_board.py --топ 8 --порт 34786
    python3 tools/astra_churn_to_board.py --сухой     # посчитать и показать, не рисуя
    python3 tools/astra_churn_to_board.py --стереть   # убрать нарисованное
    python3 tools/astra_churn_to_board.py --selftest

Коды выхода: 0 — нарисовано (или показано), 1 — отказ с причиной.
"""

import argparse
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request

ОЗЕРО = pathlib.Path.home() / "Downloads" / "kt_datalake.db"
ПОРТ = 34786
МЕТКА = "астра_"            # по ней узнаём свои элементы и заменяем их при повторе
ШАГ_X, ШАГ_Y = 300, 150     # сетка карточек
КОЛОНОК = 4

# Светофор по доле оттока. Пороги названы явно: «плохо» должно быть решением,
# а не впечатлением от цвета.
ПОРОГ_ТРЕВОГА = 20.0
ПОРОГ_ВНИМАНИЕ = 15.0
ЦВЕТА = {
    "тревога":  ("#e03131", "#ffc9c9"),
    "внимание": ("#f08c00", "#ffec99"),
    "норма":    ("#2f9e44", "#b2f2bb"),
}


class Отказ(Exception):
    pass


def тяжесть(доля: float) -> str:
    if доля >= ПОРОГ_ТРЕВОГА:
        return "тревога"
    if доля >= ПОРОГ_ВНИМАНИЕ:
        return "внимание"
    return "норма"


def деньги(тыс_тенге: float) -> str:
    """Тенге человеческим языком: миллиарды и миллионы, а не 14 знаков подряд."""
    т = тыс_тенге * 1000
    if т >= 1_000_000_000:
        return f"{т / 1_000_000_000:.1f} млрд ₸"
    if т >= 1_000_000:
        return f"{т / 1_000_000:.0f} млн ₸"
    return f"{т:,.0f} ₸".replace(",", " ")


def взять_данные(озеро: pathlib.Path, топ: int) -> dict:
    """Считаем кодом, не моделью: у чисел не должно быть двух версий."""
    try:
        import duckdb
    except ImportError:
        raise Отказ("нет duckdb — поставить: pip3 install duckdb")
    if not озеро.exists():
        raise Отказ(f"озера нет: {озеро}")
    с = duckdb.connect(str(озеро), read_only=True)
    есть = [r[0] for r in с.execute(
        "SELECT table_name FROM information_schema.tables").fetchall()]
    if "gold_churn_analysis" not in есть:
        raise Отказ("в озере нет витрины gold_churn_analysis — это не озеро Астры")

    города = с.execute("""
        SELECT city,
               sum(total_subs)                      AS всего,
               sum(churned)                         AS ушло,
               round(100.0*sum(churned)/sum(total_subs), 1) AS доля,
               round(sum(churned*avg_ltv_k_kzt), 0) AS потеряно_тыс,
               round(avg(avg_nps), 0)               AS nps
        FROM gold_churn_analysis
        GROUP BY city
        ORDER BY потеряно_тыс DESC
    """).fetchall()
    поля = ("город", "всего", "ушло", "доля", "потеряно_тыс", "nps")
    все = [dict(zip(поля, р)) for р in города]
    return {
        "города": все[:топ],
        "городов_всего": len(все),
        "абонентов": sum(г["всего"] for г in все),
        "ушло": sum(г["ушло"] for г in все),
        "потеряно_тыс": sum(г["потеряно_тыс"] for г in все),
    }


def _основа(шаблон: dict, **поля) -> dict:
    n = json.loads(json.dumps(шаблон))
    n.update(поля)
    n["id"] = МЕТКА + str(random.randint(10 ** 9, 10 ** 10))
    n["seed"] = random.randint(1, 2 ** 31)
    n["versionNonce"] = random.randint(1, 2 ** 31)
    n["version"] = 1
    n["updated"] = int(time.time() * 1000)
    n["groupIds"] = []
    n["boundElements"] = None
    n["isDeleted"] = False
    n["containerId"] = None
    return n


def нарисовать(данные: dict, фигура: dict, текст: dict,
               лев: float, верх: float) -> list:
    """Собрать элементы схемы. Раскладка простая нарочно: её читают глазами."""
    эл = []
    эл.append(_основа(текст, x=лев, y=верх, width=760, height=40, fontSize=28,
                      strokeColor="#1a1a1a",
                      text="Отток абонентов — Астра Телеком (демо)",
                      originalText="Отток абонентов — Астра Телеком (демо)"))
    сводка = (f"{данные['городов_всего']} городов · абонентов {данные['абонентов']:,} · "
              f"ушло {данные['ушло']:,} · потеряно {деньги(данные['потеряно_тыс'])}"
              ).replace(",", " ")
    эл.append(_основа(текст, x=лев, y=верх + 48, width=900, height=26, fontSize=18,
                      strokeColor="#495057", text=сводка, originalText=сводка))
    подпись = (f"нарисовано агентом из витрины gold_churn_analysis · "
               f"{time.strftime('%d.%m.%Y %H:%M')} · данные синтетические")
    эл.append(_основа(текст, x=лев, y=верх + 80, width=900, height=22, fontSize=14,
                      strokeColor="#868e96", text=подпись, originalText=подпись))

    for i, г in enumerate(данные["города"]):
        кол, ряд = i % КОЛОНОК, i // КОЛОНОК
        x, y = лев + кол * ШАГ_X, верх + 130 + ряд * ШАГ_Y
        обводка, заливка = ЦВЕТА[тяжесть(г["доля"])]
        эл.append(_основа(фигура, x=x, y=y, width=270, height=120,
                          strokeColor=обводка, backgroundColor=заливка))
        строки = (f"{г['город']}\n"
                  f"отток {г['доля']}%  ·  ушло {г['ушло']:,}\n"
                  f"потеряно {деньги(г['потеряно_тыс'])}\n"
                  f"NPS {int(г['nps'])}").replace(",", " ")
        эл.append(_основа(текст, x=x + 16, y=y + 18, width=238, height=88,
                          fontSize=16, strokeColor="#1a1a1a",
                          text=строки, originalText=строки))
    return эл


def хранилище(порт: int, тело: dict | None = None) -> dict:
    адрес = f"http://127.0.0.1:{порт}/_extella_storage"
    try:
        if тело is None:
            with urllib.request.urlopen(адрес, timeout=15) as о:
                return json.loads(о.read().decode())
        з = urllib.request.Request(
            адрес, data=json.dumps(тело, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(з, timeout=20) as о:
            return json.loads(о.read().decode())
    except (urllib.error.URLError, OSError) as е:
        raise Отказ(f"доска не отвечает на порту {порт} ({е}). "
                    f"Проверить: launchctl list | grep ai.extella")


def работа(порт: int, озеро: pathlib.Path, топ: int, сухой: bool, стереть: bool) -> int:
    if not стереть:
        данные = взять_данные(озеро, топ)
        print(f"\nАСТРА ТЕЛЕКОМ — витрина оттока (посчитано кодом, не моделью)")
        print(f"  городов {данные['городов_всего']} · абонентов {данные['абонентов']:,}"
              f" · ушло {данные['ушло']:,} · потеряно {деньги(данные['потеряно_тыс'])}"
              .replace(",", " "))
        print(f"\n  Топ-{топ} по потерянным деньгам:")
        for г in данные["города"]:
            print(f"    {тяжесть(г['доля']):9} {г['город']:14} отток {г['доля']:5}% "
                  f"· ушло {г['ушло']:6,} · {деньги(г['потеряно_тыс'])}".replace(",", " "))
        if сухой:
            print("\n  СУХОЙ ПРОГОН: на доску ничего не писал")
            return 0

    д = хранилище(порт)
    эл = json.loads(д.get("excalidraw") or "[]")
    свои = [e for e in эл if str(e.get("id", "")).startswith(МЕТКА)]
    чужие = [e for e in эл if not str(e.get("id", "")).startswith(МЕТКА)]
    if свои:
        print(f"\n  прошлый рисунок агента: {len(свои)} элементов — заменяю, не дублирую")

    if стереть:
        новые = чужие
        print(f"  стёрто элементов агента: {len(свои)}")
    else:
        живые = [e for e in чужие if not e.get("isDeleted")]
        if not живые:
            raise Отказ("на доске нет ни одного элемента человека — "
                        "нечем взять образец формы, откройте доску хотя бы раз")
        фигура = next((e for e in живые if e.get("type") == "rectangle"), None)
        текст = next((e for e in живые if e.get("type") == "text"), None)
        if not (фигура and текст):
            raise Отказ("на доске нет прямоугольника и подписи — "
                        "с них берётся форма элементов, чтобы не выдумывать схему")
        низ = max(e.get("y", 0) + (e.get("height") or 0) for e in живые)
        лев = min(e.get("x", 0) for e in живые)
        новые = чужие + нарисовать(данные, фигура, текст, лев, низ + 260)
        print(f"  нарисовано элементов: {len(новые) - len(чужие)}")

    хранилище(порт, {"ключ": "excalidraw",
                     "значение": json.dumps(новые, ensure_ascii=False)})
    print(f"  ✓ доска обновлена: было {len(эл)}, стало {len(новые)}")
    print(f"\n  Откройте доску заново — она читает работу при открытии.")
    return 0


def selftest() -> int:
    ошибки = []
    for доля, ждём in ((25.0, "тревога"), (20.0, "тревога"), (17.0, "внимание"),
                       (15.0, "внимание"), (9.9, "норма")):
        if тяжесть(доля) != ждём:
            ошибки.append(f"тяжесть({доля}) = {тяжесть(доля)}, ждали {ждём}")
    print("  ✓ пороги светофора названы и срабатывают" if not ошибки else "")

    for тыс, ждём in ((2_500_000, "2.5 млрд ₸"), (3_400, "3 млн ₸")):
        if деньги(тыс) != ждём:
            ошибки.append(f"деньги({тыс}) = {деньги(тыс)}, ждали {ждём}")
    if not any("деньги" in о for о in ошибки):
        print("  ✓ деньги читаются человеком, а не в 14 знаков")

    образец_ф = {"type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10}
    образец_т = {"type": "text", "x": 0, "y": 0, "text": "", "originalText": ""}
    данные = {"города": [{"город": "Алматы", "всего": 100, "ушло": 21, "доля": 21.0,
                          "потеряно_тыс": 2_100, "nps": 50}] * 5,
              "городов_всего": 20, "абонентов": 1000, "ушло": 200, "потеряно_тыс": 9_000}
    эл = нарисовать(данные, образец_ф, образец_т, 0, 0)
    if len(эл) != 3 + 5 * 2:
        ошибки.append(f"элементов {len(эл)}, ждали 13 (3 шапки + 5 городов по 2)")
    else:
        print("  ✓ раскладка: шапка, сводка, подпись и по две фигуры на город")
    if not all(str(e["id"]).startswith(МЕТКА) for e in эл):
        ошибки.append("не все элементы помечены — повтор создаст дубли")
    else:
        print("  ✓ все элементы помечены: повтор заменит, а не удвоит")
    ряды = {round(e["y"]) for e in эл if e.get("type") == "rectangle"}
    if len(ряды) != 2:
        ошибки.append(f"пять карточек по четыре в ряд должны дать 2 ряда, вышло {len(ряды)}")
    else:
        print("  ✓ карточки переносятся на новый ряд")
    if "синтетические" not in json.dumps(эл, ensure_ascii=False):
        ошибки.append("на схеме не сказано, что данные синтетические")
    else:
        print("  ✓ на схеме честно сказано про синтетику и источник")

    if ошибки:
        for о in ошибки:
            print(f"  ✕ {о}")
        print("ИТОГ САМОПРОВЕРКИ: есть отказы")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("--порт", type=int, default=ПОРТ)
    р.add_argument("--озеро", default=str(ОЗЕРО))
    р.add_argument("--топ", type=int, default=8)
    р.add_argument("--сухой", action="store_true")
    р.add_argument("--стереть", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    try:
        return работа(а.порт, pathlib.Path(а.озеро).expanduser(), а.топ, а.сухой, а.стереть)
    except Отказ as о:
        print(f"\nНе нарисовал: {о}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
