#!/usr/bin/env python3
"""Схема на доске → работающее приложение в магазине ОС.

ЗАЧЕМ. Это конец пути, который начался с чужой сборки на GitHub. Человек говорит
словами, агент рисует схему будущего приложения, человек правит её руками —
убирает блок, дописывает свой, — и агент собирает из схемы приложение с живыми
данными и кладёт его в магазин. Из рисунка родился продукт.

Ни строчки кода человек не пишет и ни одной формы не заполняет. Схема — и есть
задание.

Как это устроено честно:
  * агент рисует блоки-заготовки; человек правит их своими словами;
  * блок понимается по короткому словарю — что не понято, называется вслух;
  * данные берутся из озера Астры и вшиваются в страницу: приложение работает
    без интернета, как и всё в этом контуре;
  * получается страничный продукт — его выкладывает tools/deploy_page_product.py,
    а Publish жмёт владелец.

    python3 tools/board_to_app.py --нарисовать-схему "Панель по оттоку"
    python3 tools/board_to_app.py --собрать --slug churn-panel --имя "Панель по оттоку"
    python3 tools/board_to_app.py --selftest

Коды выхода: 0 — сделано, 1 — отказ с названной причиной.
"""

import argparse
import json
import pathlib
import re
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
КОРЕНЬ = СЮДА.parent
sys.path.insert(0, str(СЮДА))
from astra_churn_to_board import (  # noqa: E402
    ОЗЕРО, ПОРТ, Отказ, деньги, тяжесть, хранилище, _основа)

МЕТКА = "схема_"

# Словарь блоков: что человек может написать в прямоугольнике → что соберётся.
# Короткий намеренно: лучше честно не понять один блок, чем собрать не то.
БЛОКИ = {
    "сводка":   ("итог", ["сводка", "итог", "главное", "kpi"]),
    "города":   ("города", ["город", "отток", "churn"]),
    "деньги":   ("деньги", ["деньг", "потер", "убыт", "на кону"]),
    "жалобы":   ("жалобы", ["жалоб", "обращен", "проблем"]),
    "выручка":  ("выручка", ["arpu", "выручк", "доход", "сегмент"]),
}
ЗАГОЛОВКИ = {
    "итог":    "Главное",
    "города":  "Отток по городам",
    "деньги":  "Где теряем деньги",
    "жалобы":  "Жалобы: на что и как быстро закрываем",
    "выручка": "Выручка и ARPU по сегментам",
}


def узнать_блок(текст: str) -> str | None:
    т = текст.lower()
    for вид, (ключ, слова) in БЛОКИ.items():
        if any(с in т for с in слова):
            return ключ
    return None


# ── что рисуем на доске ───────────────────────────────────────────────────────

def нарисовать_схему(название: str, эл: list, порт: int) -> int:
    живые = [э for э in эл if not э.get("isDeleted")]
    фигура = next((э for э in живые if э.get("type") == "rectangle"), None)
    текст = next((э for э in живые if э.get("type") == "text"), None)
    if not (фигура and текст):
        raise Отказ("на доске нет прямоугольника и подписи — с них берётся форма")
    низ = max(э.get("y", 0) + (э.get("height") or 0) for э in живые)
    лев = min(э.get("x", 0) for э in живые)
    y = низ + 220

    новые = []

    def пометить(э):
        э["id"] = МЕТКА + э["id"].split("_", 1)[1]
        новые.append(э)
        return э

    шапка = f"СХЕМА ПРИЛОЖЕНИЯ: {название}"
    пометить(_основа(текст, x=лев, y=y, width=800, height=34, fontSize=24,
                     strokeColor="#1a1a1a", text=шапка, originalText=шапка))
    подсказка = ("блоки ниже — задание для агента. Уберите лишний, допишите свой "
                 "своими словами, потом соберём приложение")
    пометить(_основа(текст, x=лев, y=y + 40, width=800, height=22, fontSize=14,
                     strokeColor="#868e96", text=подсказка, originalText=подсказка))

    заготовки = ["сводка", "отток по городам", "где теряем деньги", "жалобы"]
    for i, слова in enumerate(заготовки):
        кол, ряд = i % 2, i // 2
        x, yy = лев + кол * 320, y + 90 + ряд * 130
        пометить(_основа(фигура, x=x, y=yy, width=290, height=100,
                         strokeColor="#5f3dc4", backgroundColor="#e5dbff"))
        пометить(_основа(текст, x=x + 20, y=yy + 38, width=250, height=26,
                         fontSize=18, strokeColor="#1a1a1a",
                         text=слова, originalText=слова))

    прочие = [э for э in эл if not str(э.get("id", "")).startswith(МЕТКА)]
    хранилище(порт, {"ключ": "excalidraw",
                     "значение": json.dumps(прочие + новые, ensure_ascii=False)})
    return len(новые)


# ── что читаем с доски ────────────────────────────────────────────────────────

def подпись(фигура: dict, элементы: list) -> str:
    ид = фигура.get("id")
    для_него = [э for э in элементы if э.get("type") == "text"
                and э.get("containerId") == ид]
    if для_него:
        return (для_него[0].get("text") or "").strip()
    x, y = фигура.get("x", 0), фигура.get("y", 0)
    ш, в = фигура.get("width", 0), фигура.get("height", 0)
    внутри = [э for э in элементы if э.get("type") == "text"
              and x - 4 <= э.get("x", 0) <= x + ш and y - 4 <= э.get("y", 0) <= y + в]
    return " ".join((э.get("text") or "").strip() for э in внутри).strip()


def прочитать_схему(эл: list) -> tuple[str, list, list]:
    """Схема = блоки в области, которую агент разметил. Правки человека внутри
    этой области — часть задания: он мог переписать блок или добавить свой."""
    живые = [э for э in эл if not э.get("isDeleted")]
    мои = [э for э in живые if str(э.get("id", "")).startswith(МЕТКА)]
    if not мои:
        raise Отказ("на доске нет схемы приложения — нарисовать: --нарисовать-схему «Имя»")

    название = "Панель"
    for э in мои:
        т = (э.get("text") or "")
        if т.startswith("СХЕМА ПРИЛОЖЕНИЯ:"):
            название = т.split(":", 1)[1].strip() or название

    верх = min(э.get("y", 0) for э in мои)
    низ = max(э.get("y", 0) + (э.get("height") or 0) for э in мои)
    лев = min(э.get("x", 0) for э in мои)
    прав = max(э.get("x", 0) + (э.get("width") or 0) for э in мои)
    поле = 80

    блоки, непонятые = [], []
    for ф in [э for э in живые if э.get("type") == "rectangle"]:
        цx = ф.get("x", 0) + (ф.get("width") or 0) / 2
        цy = ф.get("y", 0) + (ф.get("height") or 0) / 2
        if not (лев - поле <= цx <= прав + поле and верх - поле <= цy <= низ + поле):
            continue
        имя = подпись(ф, живые)
        if not имя:
            continue
        вид = узнать_блок(имя)
        (блоки if вид else непонятые).append(
            {"текст": имя, "вид": вид, "y": ф.get("y", 0), "x": ф.get("x", 0)})
    блоки.sort(key=lambda б: (б["y"], б["x"]))
    # один вид блока — один раздел: два одинаковых прямоугольника не должны
    # давать две одинаковые таблицы
    видано, единые = set(), []
    for б in блоки:
        if б["вид"] in видано:
            continue
        видано.add(б["вид"])
        единые.append(б)
    return название, единые, непонятые


# ── что собираем ──────────────────────────────────────────────────────────────

def данные_для(виды: list, озеро: pathlib.Path) -> dict:
    try:
        import duckdb
    except ImportError:
        raise Отказ("нет duckdb — поставить: pip3 install duckdb")
    if not озеро.exists():
        raise Отказ(f"озера нет: {озеро}")
    с = duckdb.connect(str(озеро), read_only=True)
    д = {}
    if {"итог", "города", "деньги"} & set(виды):
        д["города"] = [dict(zip(("город", "всего", "ушло", "доля", "потеряно_тыс", "nps"), р))
                       for р in с.execute("""
            SELECT city, sum(total_subs), sum(churned),
                   round(100.0*sum(churned)/sum(total_subs),1),
                   round(sum(churned*avg_ltv_k_kzt),0), round(avg(avg_nps),0)
            FROM gold_churn_analysis GROUP BY city ORDER BY 5 DESC""").fetchall()]
    if "жалобы" in виды:
        д["жалобы"] = [dict(zip(("вид", "сколько", "дней", "закрыто"), р))
                       for р in с.execute("""
            SELECT complaint_type, sum(cnt), round(avg(avg_days),1),
                   round(avg(resolve_pct),1)
            FROM gold_complaint_kpis GROUP BY complaint_type ORDER BY 2 DESC""").fetchall()]
    if "выручка" in виды:
        д["выручка"] = [dict(zip(("сегмент", "абонентов", "выручка", "arpu"), р))
                        for р in с.execute("""
            SELECT segment, sum(paying_subs), round(sum(revenue_kzt),0),
                   round(avg(arpu_kzt),0)
            FROM gold_arpu_monthly GROUP BY segment ORDER BY 3 DESC""").fetchall()]
    return д


def _таблица(заголовки: list, строки: list) -> str:
    шапка = "".join(f"<th>{з}</th>" for з in заголовки)
    тело = "".join("<tr>" + "".join(f"<td>{я}</td>" for я in с) + "</tr>" for с in строки)
    return f"<table><thead><tr>{шапка}</tr></thead><tbody>{тело}</tbody></table>"


def раздел(вид: str, д: dict) -> str:
    з = ЗАГОЛОВКИ[вид]
    if вид == "итог":
        г = д["города"]
        всего, ушло = sum(x["всего"] for x in г), sum(x["ушло"] for x in г)
        потери = sum(x["потеряно_тыс"] for x in г)
        плитки = [("Абонентов", f"{всего:,}".replace(",", " ")),
                  ("Ушло за период", f"{ушло:,}".replace(",", " ")),
                  ("Доля оттока", f"{round(100*ушло/всего,1)}%"),
                  ("Потеряно денег", деньги(потери))]
        внутри = "".join(f'<div class="плитка"><b>{з_}</b><span>{v}</span></div>'
                         for з_, v in плитки)
        return f'<section><h2>{з}</h2><div class="плитки">{внутри}</div></section>'
    if вид == "города":
        строки = [(x["город"],
                   f'<span class="{тяжесть(x["доля"])}">{x["доля"]}%</span>',
                   f'{x["ушло"]:,}'.replace(",", " "), int(x["nps"]))
                  for x in д["города"][:12]]
        return (f'<section><h2>{з}</h2>'
                + _таблица(["Город", "Отток", "Ушло", "NPS"], строки) + "</section>")
    if вид == "деньги":
        строки = [(x["город"], деньги(x["потеряно_тыс"]),
                   f'<span class="{тяжесть(x["доля"])}">{x["доля"]}%</span>')
                  for x in д["города"][:12]]
        return (f'<section><h2>{з}</h2>'
                + _таблица(["Город", "Потеряно", "Отток"], строки) + "</section>")
    if вид == "жалобы":
        строки = [(x["вид"], f'{int(x["сколько"]):,}'.replace(",", " "),
                   f'{x["дней"]} дн.', f'{x["закрыто"]}%') for x in д["жалобы"]]
        return (f'<section><h2>{з}</h2>'
                + _таблица(["Тип", "Сколько", "Срок", "Закрыто"], строки) + "</section>")
    if вид == "выручка":
        строки = [(x["сегмент"], f'{int(x["абонентов"]):,}'.replace(",", " "),
                   деньги(x["выручка"] / 1000), f'{int(x["arpu"]):,} ₸'.replace(",", " "))
                  for x in д["выручка"]]
        return (f'<section><h2>{з}</h2>'
                + _таблица(["Сегмент", "Абонентов", "Выручка", "ARPU"], строки) + "</section>")
    return ""


СТИЛЬ = """
:root{--бум:#FAF9F5;--чер:#1A1A1A;--сер:#6B7280;--рам:#E2E0DA;--зол:#C57E33;--пан:#fff}
@media (prefers-color-scheme:dark){:root{--бум:#141414;--чер:#EDEDED;--сер:#9AA0A6;--рам:#2E2E2E;--пан:#1C1C1C}}
*{box-sizing:border-box}body{margin:0;background:var(--бум);color:var(--чер);
 font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.лист{max-width:980px;margin:0 auto;padding:28px 22px 60px}
h1{font:600 26px/1.25 Georgia,serif;margin:0 0 6px}
.под{color:var(--сер);font-size:13.5px;margin-bottom:24px}
section{margin:0 0 26px;padding:18px 20px;border:1px solid var(--рам);
 border-radius:12px;background:var(--пан)}
h2{font-size:16px;margin:0 0 14px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:var(--сер);font-weight:500;padding:6px 10px 10px;
 border-bottom:1px solid var(--рам)}
td{padding:9px 10px;border-bottom:1px solid var(--рам)}
tr:last-child td{border-bottom:0}
.плитки{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.плитка{padding:14px 16px;border:1px solid var(--рам);border-radius:10px}
.плитка b{display:block;color:var(--сер);font-weight:500;font-size:12.5px;margin-bottom:6px}
.плитка span{font-size:22px;font-weight:600}
.тревога{color:#e03131;font-weight:600}.внимание{color:#f08c00;font-weight:600}
.норма{color:#2f9e44}
footer{color:var(--сер);font-size:12px;margin-top:8px;line-height:1.7}
"""


def собрать_страницу(название: str, блоки: list, д: dict, непонятые: list) -> str:
    разделы = "".join(раздел(б["вид"], д) for б in блоки)
    хвост = ("собрано агентом из схемы на Доске схем · данные из витрин Астра Телеком "
             "(синтетика) · всё лежит внутри страницы, интернет не нужен")
    если = ""
    if непонятые:
        список = ", ".join(f"«{н['текст'][:28]}»" for н in непонятые[:4])
        если = (f'<footer>Блоки, которых агент не понял и не стал выдумывать: '
                f'{список}.</footer>')
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{название}</title><style>{СТИЛЬ}</style></head>
<body><div class="лист">
<h1>{название}</h1>
<div class="под">{len(блоки)} раздела собрано по схеме, которую вы нарисовали</div>
{разделы}
<footer>{хвост}</footer>{если}
</div></body></html>"""


def собрать(slug: str, имя: str, порт: int, озеро: pathlib.Path, сухой: bool) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        raise Отказ("slug — только строчная латиница, цифры и дефис")
    эл = json.loads(хранилище(порт).get("excalidraw") or "[]")
    название, блоки, непонятые = прочитать_схему(эл)
    имя = имя or название

    print(f"\nПРОЧИТАЛ СХЕМУ С ДОСКИ: «{название}»")
    for б in блоки:
        print(f"  ✓ «{б['текст']}» → раздел «{ЗАГОЛОВКИ[б['вид']]}»")
    for н in непонятые:
        print(f"  · «{н['текст'][:40]}» — не понял, в приложение не пойдёт")
    if not блоки:
        raise Отказ("ни одного понятного блока. Слова, которые агент знает: "
                    "сводка, отток/города, деньги/потери, жалобы, ARPU/выручка")

    д = данные_для([б["вид"] for б in блоки], озеро)
    страница = собрать_страницу(имя, блоки, д, непонятые)
    print(f"\n  страница собрана: {len(страница):,} знаков".replace(",", " "))
    if сухой:
        print("  СУХОЙ ПРОГОН: на диск не писал")
        return 0

    издание = КОРЕНЬ / "editions" / slug
    издание.mkdir(parents=True, exist_ok=True)
    (издание / "index.html").write_text(страница)
    if not (издание / "icon.png").exists():
        import subprocess
        subprocess.run([sys.executable, str(СЮДА / "make_icon.py"), "доска",
                        str(издание / "icon.png")], capture_output=True)
    карточка = издание / "listing.json"
    если = json.loads(карточка.read_text()) if карточка.exists() else {}
    если.update({
        "name": имя,
        "описание": (f"{имя}: живая картина по данным Астра Телеком — "
                     + ", ".join(ЗАГОЛОВКИ[б["вид"]].lower() for б in блоки)
                     + ". Собрано по схеме, нарисованной человеком на доске; "
                       "данные лежат внутри страницы, интернет не нужен."),
        "теги": ["приложение", "аналитика", "телеком", "локально"],
        "иконка": "icon.png",
        "версия": если.get("версия") or "0.1.0",
        "цена": 0, "права": [],
        "состояние": "черновик, собран из схемы",
        "границы": ("данные вшиты на момент сборки и сами не обновляются — "
                    "пересоберите приложение, когда цифры устареют"),
    })
    карточка.write_text(json.dumps(если, ensure_ascii=False, indent=2) + "\n")
    print(f"  ✓ продукт готов: editions/{slug}/ (страница, иконка, карточка)")
    print(f"\n  Дальше:")
    print(f"    python3 tools/check_listing_meta.py editions/{slug}")
    print(f"    python3 tools/deploy_page_product.py editions/{slug}")
    print("    Publish в магазине — владелец")
    return 0


def selftest() -> int:
    ошибки = []
    for текст, ждём in (("сводка", "итог"), ("отток по городам", "города"),
                        ("где теряем деньги", "деньги"), ("жалобы", "жалобы"),
                        ("ARPU по сегментам", "выручка"), ("нарисуй кота", None)):
        if узнать_блок(текст) != ждём:
            ошибки.append(f"«{текст}» → {узнать_блок(текст)}, ждали {ждём}")
    print("  ✓ блоки узнаются по словам человека" if not ошибки else "")

    эл = [
        {"id": "схема_1", "type": "text", "text": "СХЕМА ПРИЛОЖЕНИЯ: Панель", "x": 0, "y": 0,
         "width": 400, "height": 30},
        {"id": "схема_2", "type": "rectangle", "x": 0, "y": 60, "width": 200, "height": 80},
        {"id": "схема_3", "type": "text", "containerId": "схема_2", "text": "сводка",
         "x": 10, "y": 90},
        {"id": "чел_1", "type": "rectangle", "x": 220, "y": 60, "width": 200, "height": 80},
        {"id": "чел_2", "type": "text", "containerId": "чел_1", "text": "жалобы",
         "x": 230, "y": 90},
        {"id": "чужой", "type": "rectangle", "x": 0, "y": 5000, "width": 100, "height": 50},
        {"id": "чужой_т", "type": "text", "containerId": "чужой", "text": "сводка",
         "x": 5, "y": 5010},
    ]
    имя, блоки, неп = прочитать_схему(эл)
    if имя != "Панель":
        ошибки.append(f"название схемы «{имя}»")
    elif [б["вид"] for б in блоки] != ["итог", "жалобы"]:
        ошибки.append(f"блоки прочитаны как {[б['вид'] for б in блоки]}")
    else:
        print("  ✓ блок человека, дорисованный в схему, попадает в задание")
        print("  ✓ фигура вне схемы в задание НЕ попадает")

    эл2 = эл + [{"id": "чел_3", "type": "rectangle", "x": 0, "y": 160,
                 "width": 200, "height": 80},
                {"id": "чел_4", "type": "text", "containerId": "чел_3",
                 "text": "нарисуй кота", "x": 10, "y": 190}]
    _, блоки2, неп2 = прочитать_схему(эл2)
    if not неп2 or неп2[0]["текст"] != "нарисуй кота":
        ошибки.append("непонятный блок не назван вслух")
    else:
        print("  ✓ непонятный блок называется, а не выдумывается")

    д = {"города": [{"город": "А", "всего": 100, "ушло": 25, "доля": 25.0,
                     "потеряно_тыс": 900, "nps": 40}]}
    html = собрать_страницу("Тест", [{"вид": "итог"}, {"вид": "города"}], д, неп2)
    for кусок, что in (("<table", "таблица"), ("плитка", "плитки"),
                       ("тревога", "светофор"), ("синтетика", "честная подпись"),
                       ("charset", "кодировка")):
        if кусок not in html:
            ошибки.append(f"в странице нет: {что}")
    if not any("странице нет" in о for о in ошибки):
        print("  ✓ страница собирается с таблицами, плитками и честной подписью")

    if ошибки:
        for о in ошибки:
            print(f"  ✕ {о}")
        print("ИТОГ САМОПРОВЕРКИ: есть отказы")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("--нарисовать-схему", dest="нарисовать", default="")
    р.add_argument("--собрать", action="store_true")
    р.add_argument("--slug", default="")
    р.add_argument("--имя", dest="имя", default="")
    р.add_argument("--порт", type=int, default=ПОРТ)
    р.add_argument("--озеро", default=str(ОЗЕРО))
    р.add_argument("--сухой", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    try:
        if а.нарисовать:
            эл = json.loads(хранилище(а.порт).get("excalidraw") or "[]")
            n = нарисовать_схему(а.нарисовать, эл, а.порт)
            print(f"  ✓ схема нарисована на доске ({n} элементов)")
            print("  Откройте доску: уберите лишний блок, допишите свой своими словами.")
            print(f"  Потом: --собрать --slug <имя-латиницей>")
            return 0
        if а.собрать:
            if not а.slug:
                raise Отказ("нужен --slug: под ним продукт ляжет в editions/")
            return собрать(а.slug, а.имя, а.порт,
                           pathlib.Path(а.озеро).expanduser(), а.сухой)
        р.print_help()
        return 1
    except Отказ as о:
        print(f"\nНе смог: {о}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
