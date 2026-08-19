#!/usr/bin/env python3
"""Второй получатель: любая из пяти форм → страница-отчёт.

ЗАЧЕМ ИМЕННО ВТОРОЙ. Пока получатель один, «общий язык» — слова: доска могла
оказаться просто хорошо написанным инструментом под Астру. Второй получатель
доказывает утверждение делом: он не знает ни одного источника по имени, читает
тот же словарь и не потребовал ни одной правки ни в словаре, ни в источниках.

Отсюда же правило на будущее: получатель добавляется ОДНИМ файлом, и приложений
это не касается вовсе. Ровно так же добавляется источник — паспортом. Это и есть
N+M на практике, а не на схеме.

    python3 tools/в_отчёт.py --файл форма.json --источник <имя-приложения>
    python3 tools/в_отчёт.py --пример связи --источник проба --открыть

Имени реального приложения нет даже в примере запуска — намеренно: получатель,
знающий хоть одно приложение, возвращает счёт N×M незаметно для всех.
"""

import argparse
import html
import json
import pathlib
import subprocess
import sys
import time

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ, проверить, пример, строки_пункта  # noqa: E402

ПАПКА = pathlib.Path.home() / "extella-cabinet" / "отчёты"

# Палитра и шрифты Extella. Цвет мимо палитры — дефект, а не мелочь; заголовки
# набираются серифом, жирный гротеск в заголовке каноном запрещён.
СТИЛЬ = """
:root{--бум:#FAFAF8;--крем:#F5F3EE;--бел:#fff;--чер:#0A0A0A;--раздел:#EBE8E1;
      --серебро:#8C8C8C;--золото:#A5632A;--петроль:#2F6B66}
@media (prefers-color-scheme:dark){
  :root{--бум:#0A0A0A;--крем:#141414;--бел:#141414;--чер:#F5F3EE;
        --раздел:rgba(243,238,229,.10);--серебро:#8d8880;--золото:#D4944A;--петроль:#5FA8A0}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--бум);color:var(--чер);font:15px/1.6 Nunito,-apple-system,sans-serif;
     padding:32px 24px 64px}
.лист{max-width:940px;margin:0 auto}
h1{font:600 26px/1.25 'Source Serif 4',Georgia,serif;margin-bottom:8px}
.подпись{color:var(--золото);font-size:13.5px;margin-bottom:4px}
.след{color:var(--серебро);font-size:12.5px;margin-bottom:24px}
.карты{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.карта{background:var(--бел);border:1px solid var(--раздел);border-radius:12px;padding:16px 18px}
.карта b{display:block;font-size:15px;margin-bottom:6px}
.карта dl{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:13.5px}
.карта dt{color:var(--серебро)}
.карта dd{text-align:right}
.число{font:600 44px/1 'Source Serif 4',Georgia,serif;color:var(--золото);
       padding:24px 26px;border:1px solid var(--золото);border-radius:12px;display:inline-block}
.шаг{background:var(--бел);border:1px solid var(--раздел);border-radius:12px;
     padding:14px 16px;margin-bottom:10px}
.шаг i{color:var(--петроль);font-style:normal;font-weight:600;margin-right:8px}
.связь{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px;
       margin-bottom:10px}
.связь div{background:var(--бел);border:1px solid var(--раздел);border-radius:12px;padding:14px 16px}
.связь span{color:var(--петроль);font-size:13px;text-align:center}
.раздел{background:var(--бел);border:1px solid var(--раздел);border-radius:12px;
        padding:18px 20px;margin-bottom:12px}
.раздел h2{font:600 17px/1.3 'Source Serif 4',Georgia,serif;color:var(--петроль);margin-bottom:8px}
.раздел p{font-size:14.5px;white-space:pre-wrap}
"""


def _э(т) -> str:
    return html.escape(str(т))


def тело(д: dict) -> str:
    форма, куски = д["форма"], []

    if форма == "число":
        return f'<div class="число">{_э(д["значение"])}</div>'

    if форма == "список":
        куски.append('<div class="карты">')
        for п in д["строки"]:
            поля = "".join(f"<dt>{_э(к)}</dt><dd>{_э(з)}</dd>"
                           for к, з in (п.get("поля") or {}).items())
            куски.append(f'<div class="карта"><b>{_э(п["имя"])}</b><dl>{поля}</dl></div>')
        куски.append("</div>")
        return "".join(куски)

    if форма == "шаги":
        for i, п in enumerate(д["шаги"], 1):
            подпись = f' — {_э(п["подпись"])}' if п.get("подпись") else ""
            куски.append(f'<div class="шаг"><i>{i}</i>{_э(п["имя"])}{подпись}</div>')
        return "".join(куски)

    if форма == "связи":
        for п in д["связи"]:
            куски.append(f'<div class="связь"><div>{_э(п["от"])}</div>'
                         f'<span>→<br>{_э(п.get("подпись") or "")}</span>'
                         f'<div>{_э(п["к"])}</div></div>')
        return "".join(куски)

    for п in д["разделы"]:
        куски.append(f'<div class="раздел"><h2>{_э(п["имя"])}</h2>'
                     f'<p>{_э(п["текст"])}</p></div>')
    return "".join(куски)


def страница(д: dict, источник: str) -> str:
    подпись = (f'<div class="подпись">{_э(д["подпись"])}</div>' if д.get("подпись") else "")
    return (f'<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_э(д["заголовок"])}</title><style>{СТИЛЬ}</style></head><body>'
            f'<div class="лист"><h1>{_э(д["заголовок"])}</h1>{подпись}'
            f'<div class="след">собрано агентом · источник: {_э(источник)} · '
            f'{time.strftime("%d.%m.%Y %H:%M")} · форма: {_э(д["форма"])}</div>'
            f'{тело(д)}</div></body></html>')


def selftest() -> int:
    ошибки = []
    for ф in ("список", "число", "шаги", "связи", "документ"):
        с = страница(проверить(пример(ф)), "проба")
        if "<body>" not in с or len(с) < 800:
            ошибки.append(f"форма «{ф}» дала пустую страницу")
    if not ошибки:
        print("  ✓ все пять форм превращаются в страницу")

    # Получатель обязан не знать источников. Если в его коде появится имя
    # приложения — счёт снова станет N×M, просто незаметно.
    #
    # Имена собраны ИЗ ЧАСТЕЙ намеренно. Первый заход читал файл целиком и
    # находил их... в самом себе, в этой же строке проверки. Проверка, ловящая
    # собственный текст, всегда «находит дефект» — это третий раз, когда я
    # наступаю на неё, и потому она объяснена здесь.
    свой = pathlib.Path(__file__).read_text().lower()
    текст = свой.split("def selftest")[0]          # проверка себя не проверяет
    имена = [и for и in ("аст" + "ра", "юр" + "ист", "excali" + "draw",
                         "compo" + "sio", "sb" + "om") if и in текст]
    if имена:
        ошибки.append(f"получатель знает источники по имени: {имена} — это снова N×M")
    else:
        print("  ✓ получатель не знает ни одного источника по имени")

    # Опасное: содержимое источника попадает в HTML.
    зло = {"форма": "список", "заголовок": "<script>alert(1)</script>",
           "строки": [{"имя": "<img src=x onerror=alert(1)>", "поля": {}}]}
    с = страница(проверить(зло), "проба")
    # Ищем ОТКРЫВАЮЩИЙ тег, а не текст «onerror=alert»: экранирование оставляет
    # эти буквы как обычные буквы, и первый заход считал их дефектом.
    if "<script" in с.replace("<script>" + СТИЛЬ[:0], "", 0)[с.index("<body>"):] \
       or "<img" in с[с.index("<body>"):]:
        ошибки.append("содержимое источника попадает в страницу как разметка")
    else:
        print("  ✓ содержимое источника экранируется: чужие данные не становятся кодом")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Любая из пяти форм → страница-отчёт")
    р.add_argument("--файл")
    р.add_argument("--пример", metavar="ФОРМА")
    р.add_argument("--источник", default="агент")
    р.add_argument("--открыть", action="store_true")
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
        ПАПКА.mkdir(parents=True, exist_ok=True)
        куда = ПАПКА / f"{а.источник}.html"
        куда.write_text(страница(д, а.источник))
        print(f"\nФорма «{д['форма']}» · {д['заголовок']} · источник «{а.источник}»")
        print(f"  ✓ отчёт собран: {куда} ({куда.stat().st_size // 1024} КБ)")
        if а.открыть:
            subprocess.run(["open", str(куда)])
        return 0
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
