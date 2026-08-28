# -*- coding: utf-8 -*-
"""Обработчик языка `cspl=slide`: эксперт пишет презентацию, а не действие.

Третья ценность CSPL после ограничения прав и смены рантайма: эксперт
производит АРТЕФАКТ, а не побочный эффект. Артефакт версионируется, сравнивается
построчно, откатывается и проверяется приёмкой — в отличие от действия, которое
уже произошло.

Свой синтаксис здесь не украшение. В этом языке нельзя сказать «выполни» — можно
только «покажи»; и нельзя вставить разметку, потому что весь текст экранируется.
Опасное не запрещено политикой, его просто нет в языке.

Синтаксис:

    # Название презентации
    ## Заголовок слайда
    - пункт списка
    !число 24 из 25 | подпись под числом
    | ячейка | ячейка |          строка таблицы
    > примечание мелким шрифтом

Обработчик один на класс: смена оформления меняет ВСЕ презентации класса.
"""
from __future__ import annotations

import html
import re
import time

from core import CSPLError, plan_hash

DEFAULT_POLICY = {
    "schemaVersion": "cspl-slide-policy/v1",
    "profile": "presenter",
    "capabilities": {"slide.render": True},
    "scope": {"environments": ["test", "development", "copy", "production"],
              "maxSlides": 20, "maxCharsPerSlide": 1200, "allowExternalImages": False},
    "approval": {"export": "none"},
    "theme": "light",          # часть обработчика класса, а не отдельной презентации
    "footer": "",
}

ССЫЛКА = re.compile(r"https?://", re.IGNORECASE)


def разобрать(source: str, policy: dict) -> dict:
    """Текст на языке слайдов → структура. Ничего не исполняет."""
    охват = policy["scope"]
    if ССЫЛКА.search(source or "") and not охват.get("allowExternalImages", False):
        raise CSPLError("SCOPE_DENIED", "Внешние ссылки в этом языке запрещены политикой")
    название, слайды, текущий = "", [], None
    for строка in (source or "").splitlines():
        с = строка.rstrip()
        if not с.strip():
            continue
        if с.startswith("## "):
            текущий = {"title": с[3:].strip(), "blocks": []}
            слайды.append(текущий)
        elif с.startswith("# "):
            название = с[2:].strip()
        elif текущий is None:
            raise CSPLError("SCHEMA_REJECTED", "Содержимое до первого слайда")
        elif с.startswith("- "):
            текущий["blocks"].append(("bullet", с[2:].strip()))
        elif с.startswith("!число "):
            тело = с[len("!число "):]
            число, _, подпись = тело.partition("|")
            текущий["blocks"].append(("number", (число.strip(), подпись.strip())))
        elif с.startswith("|"):
            ячейки = [я.strip() for я in с.strip("|").split("|")]
            текущий["blocks"].append(("row", ячейки))
        elif с.startswith("> "):
            текущий["blocks"].append(("note", с[2:].strip()))
        else:
            текущий["blocks"].append(("text", с.strip()))
    if not слайды:
        raise CSPLError("SCHEMA_REJECTED", "В исходнике нет ни одного слайда")
    if len(слайды) > охват.get("maxSlides", 20):
        raise CSPLError("SCOPE_DENIED",
                        f"Слайдов больше разрешённого: {len(слайды)} > {охват['maxSlides']}")
    предел = охват.get("maxCharsPerSlide", 1200)
    for слайд in слайды:
        объём = len(слайд["title"]) + sum(len(str(з)) for _, з in слайд["blocks"])
        if объём > предел:
            raise CSPLError("SCOPE_DENIED", f"Слайд «{слайд['title'][:24]}» длиннее разрешённого")
    return {"title": название, "slides": слайды}


def _тело(слайд: dict) -> str:
    куски, таблица = [], []

    def закрыть_таблицу():
        if таблица:
            строки = "".join(
                "<tr>" + "".join(f"<td>{html.escape(я)}</td>" for я in р) + "</tr>"
                for р in таблица)
            куски.append(f"<table>{строки}</table>")
            таблица.clear()

    for вид, значение in слайд["blocks"]:
        if вид == "row":
            таблица.append(значение); continue
        закрыть_таблицу()
        if вид == "bullet":
            куски.append(f"<li>{html.escape(значение)}</li>")
        elif вид == "number":
            число, подпись = значение
            куски.append(f'<p class="n"><b>{html.escape(число)}</b>'
                         f'<span>{html.escape(подпись)}</span></p>')
        elif вид == "note":
            куски.append(f'<p class="note">{html.escape(значение)}</p>')
        else:
            куски.append(f"<p>{html.escape(значение)}</p>")
    закрыть_таблицу()
    склеено, итог, буфер = "", [], []
    for к in куски:                      # пункты списка собираем в один <ul>
        if к.startswith("<li>"):
            буфер.append(к)
        else:
            if буфер: итог.append("<ul>" + "".join(буфер) + "</ul>"); буфер = []
            итог.append(к)
    if буфер: итог.append("<ul>" + "".join(буфер) + "</ul>")
    return склеено.join(итог)


def отрисовать(структура: dict, policy: dict) -> str:
    """Оформление живёт в ОБРАБОТЧИКЕ: меняется здесь — меняется весь класс."""
    тёмная = policy.get("theme") == "dark"
    фон, текст, полоса = ("#141310", "#F4F1EA", "#332F27") if тёмная else ("#FAF9F5", "#17150F", "#E7E2D6")
    подвал = policy.get("footer") or ""
    слайды = "".join(
        f'<section><h2>{html.escape(с["title"])}</h2>{_тело(с)}'
        + (f'<footer>{html.escape(подвал)}</footer>' if подвал else "")
        + "</section>"
        for с in структура["slides"])
    return f"""<meta charset="utf-8"><title>{html.escape(структура['title'] or 'Презентация')}</title>
<style>
 body{{margin:0;background:{фон};color:{текст};font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif}}
 section{{min-height:88vh;padding:8vh 7vw;border-bottom:1px solid {полоса};display:flex;flex-direction:column;justify-content:center}}
 h1{{font:400 44px/1.1 'Iowan Old Style',Palatino,Georgia,serif;margin:0 0 8px}}
 h2{{font:400 34px/1.15 'Iowan Old Style',Palatino,Georgia,serif;margin:0 0 22px;letter-spacing:-.01em}}
 ul{{margin:0 0 14px;padding-left:20px}} li{{margin:6px 0}}
 .n{{margin:10px 0}} .n b{{font:600 46px/1 inherit;color:#C57E33;margin-right:12px}}
 .n span{{color:#6E685C}} .note{{color:#6E685C;font-size:14px}}
 table{{border-collapse:collapse;margin:10px 0}} td{{border:1px solid {полоса};padding:8px 12px}}
 footer{{margin-top:auto;color:#9A9384;font:12px/1 ui-monospace,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase}}
 .cover{{background:{фон}}} .cover h1 span{{color:#C57E33}}
</style>
<section class="cover"><h1>{html.escape(структура['title'] or 'Презентация')}</h1></section>{слайды}"""


def run_expert(source: str, params: dict | None, policy: dict | None = None) -> dict:
    политика = policy or DEFAULT_POLICY
    начало = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not политика["capabilities"].get("slide.render", False):
        return {"ok": False, "error": {"code": "POLICY_DENIED",
                                       "message": "Политика не даёт право slide.render"}}
    try:
        структура = разобрать(source, политика)
    except CSPLError as беда:
        return {"ok": False, "error": {"code": беда.code, "message": беда.message}}
    страница = отрисовать(структура, политика)
    план = {"language": "slide", "title": структура["title"],
            "slides": [с["title"] for с in структура["slides"]],
            "theme": политика.get("theme"), "footer": политика.get("footer")}
    return {"ok": True, "language": "slide", "planHash": plan_hash(план),
            "result": {"html": страница, "slides": len(структура["slides"]),
                       "title": структура["title"], "bytes": len(страница.encode("utf-8"))},
            "receipt": {"startedAt": начало,
                        "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "executed": True, "verified": True,
                        "policyProfile": политика.get("profile")}}
