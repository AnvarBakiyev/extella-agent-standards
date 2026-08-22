#!/usr/bin/env python3
"""Справочник организаций 2ГИС — через Робота браузера, в форму «список».

    python3 tools/источник_2gis.py --что аптека --город almaty
    python3 tools/источник_2gis.py --адрес "https://2gis.kz/almaty/search/кофейня"

ЗАЧЕМ ЗДЕСЬ РОБОТ, А НЕ ЧИТАТЕЛЬ СТРАНИЦ. Замер 23.08.2026: страница 2ГИС без
браузера пуста — наш Читатель видит оболочку без единой организации, сторонний
читатель Jina получает отказ 403. Живой браузер Робота ту же страницу
отрисовывает, и в ней 12 карточек с названиями, адресами и рейтингами. Это
ровно та граница, ради которой Робот и держится: сайты, которые без браузера не
собираются.

РАЗБОР ДЕЛАЕТ БРАУЗЕР, А НЕ МЫ. Скрипт извлечения выполняется там, где есть
разметка, и возвращает уже готовые поля. Разбирать слитый текст карточки
(«Аптека Рядом Аптеки4.9340 оценок») на нашей стороне значило бы угадывать, где
кончается название и начинается рубрика.

ЗАЧЕМ ЭТО БИЗНЕСУ. Справочник организаций города — это список поставщиков,
конкурентов или лидов: кто есть в нужной рубрике, где сидит, как оценён.
Выгружается в Таблицу, дальше человек фильтрует сам.
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ, проверить  # noqa: E402

# Порт ОКНА Робота, а не контейнера: через окно идёт наш прокси, который держит
# сессию (машинный автовход). Напрямую в контейнер пришлось бы носить пароль.
РОБОТ = 34797
ПРЕДЕЛ = 200

# Скрипт живёт в браузере: там есть разметка, и поля берутся по своим местам.
ИЗВЛЕЧЕНИЕ = r"""
const карточки = Array.from(document.querySelectorAll('div[class*=_1kf6gff]'));
const строки = [];
for (const к of карточки) {
  const ссылки = Array.from(к.querySelectorAll('a'));
  const фирма = ссылки.find(a => (a.getAttribute('href')||'').includes('/firm/'));
  if (!фирма) continue;
  const название = (фирма.textContent||'').replace(/\s+/g,' ').trim();
  if (!название) continue;
  const рубрика = ссылки.find(a => (a.getAttribute('href')||'').includes('/search/'));
  const филиалы = ссылки.find(a => (a.getAttribute('href')||'').includes('/branches/'));
  const весь = (к.textContent||'').replace(/​/g,'|').replace(/[ \t]+/g,' ');
  // Адрес — кусок между разделителями, в котором есть запятая и город.
  const куски = весь.split('|').map(s => s.trim()).filter(Boolean);
  const адрес = куски.find(s => s.includes(',') && !/оцен|Реклама|Лицензи/.test(s)) || '';
  const оценка = весь.match(/(\d[.,]\d)(\d+)\s*оцен/);
  строки.push({
    название,
    рубрика: рубрика ? (рубрика.textContent||'').trim() : '',
    рейтинг: оценка ? оценка[1].replace(',', '.') : '',
    оценок: оценка ? оценка[2] : '',
    адрес,
    филиалов: филиалы ? (филиалы.textContent||'').trim() : '',
    ссылка: 'https://2gis.kz' + (фирма.getAttribute('href')||''),
  });
}
return {строки, всего_карточек: карточки.length};
"""


def _спросить_робота(адрес: str, порт: int = РОБОТ) -> dict:
    тело = json.dumps({"url": адрес, "extractionScript": ИЗВЛЕЧЕНИЕ}).encode()
    запрос = urllib.request.Request(f"http://127.0.0.1:{порт}/scrape", data=тело,
                                    headers={"Content-Type": "application/json"},
                                    method="POST")
    try:
        with urllib.request.urlopen(запрос, timeout=180) as о:
            return json.loads(о.read().decode("utf-8", errors="ignore"))
    except urllib.error.HTTPError as е:
        raise Отказ(f"Робот браузера ответил отказом {е.code}. Проверьте, что "
                    f"приложение «Робот браузера» установлено и его окно "
                    f"открывается") from е
    except OSError as е:
        raise Отказ(f"Робот браузера не отвечает на порту {порт}: {е}. Это "
                    f"приложение обязательно — без живого браузера 2ГИС не "
                    f"собирается вовсе") from е


def собрать(адрес: str, порт: int = РОБОТ, спроси=None) -> dict:
    if "2gis." not in адрес:
        raise Отказ(f"этот источник знает только 2ГИС, а адрес другой: {адрес}")
    ответ = (спроси or _спросить_робота)(адрес, порт)
    данные = ответ.get("data") or {}
    строки = данные.get("строки") or []
    if not строки:
        raise Отказ(
            f"Робот открыл страницу, но организаций на ней не нашлось "
            f"(карточек в разметке: {данные.get('всего_карточек', 0)}). Либо "
            f"запрос ничего не дал, либо 2ГИС сменил разметку — проверьте "
            f"адрес глазами")
    if len(строки) > ПРЕДЕЛ:
        строки = строки[:ПРЕДЕЛ]
    вышло = []
    for с in строки:
        поля = {к: з for к, з in с.items() if к != "название" and з}
        вышло.append({"name": с["название"], "fields": поля})
    что = re.sub(r".*/search/", "", адрес).split("?")[0]
    try:
        что = urllib.request.unquote(что)
    except Exception:
        pass
    return проверить({
        "form": "list",
        "title": f"2ГИС: {что}",
        "caption": (f"собрано Роботом браузера, организаций {len(вышло)}; "
                    f"источник {адрес}"),
        "rows": вышло,
    })


ОБРАЗЕЦ_ОТВЕТА = {"data": {"всего_карточек": 2, "строки": [
    {"название": "Аптека Рядом", "рубрика": "Аптеки", "рейтинг": "4.9",
     "оценок": "340", "адрес": "Улица Манаса, 53а, Алматы",
     "филиалов": "10 филиалов", "ссылка": "https://2gis.kz/almaty/firm/700000011"},
    {"название": "АПТЕКАПЛЮС", "рубрика": "Аптеки", "рейтинг": "4.9",
     "оценок": "5205", "адрес": "Улица Ауэзова, 175, Алматы",
     "филиалов": "", "ссылка": "https://2gis.kz/almaty/firm/700000012"},
]}}


def _самопроверка() -> int:
    ошибки = []
    д = собрать("https://2gis.kz/almaty/search/аптека",
                спроси=lambda а, п: ОБРАЗЕЦ_ОТВЕТА)
    if д["form"] == "list" and len(д["rows"]) == 2:
        print("  ✓ ответ Робота превращается в форму «список»")
    else:
        ошибки.append(f"форма собрана неверно: {д}")
    if д["rows"][0]["name"] == "Аптека Рядом":
        print("  ✓ название организации на месте")
    else:
        ошибки.append("название потеряно")
    if д["rows"][0]["fields"].get("адрес") == "Улица Манаса, 53а, Алматы":
        print("  ✓ адрес разобран отдельным полем, а не слит с названием")
    else:
        ошибки.append(f"адрес не разобран: {д['rows'][0]['fields']}")
    # Пустые поля не должны засорять таблицу колонками без значений.
    if "филиалов" not in д["rows"][1]["fields"]:
        print("  ✓ пустые поля в таблицу не попадают")
    else:
        ошибки.append("пустое поле просочилось")
    try:
        собрать("https://krisha.kz/", спроси=lambda а, п: ОБРАЗЕЦ_ОТВЕТА)
        ошибки.append("чужой адрес не отвергнут")
    except Отказ:
        print("  ✓ чужой адрес отвергается — разбор написан под 2ГИС")
    try:
        собрать("https://2gis.kz/almaty/search/пусто",
                спроси=lambda а, п: {"data": {"строки": [], "всего_карточек": 0}})
        ошибки.append("пустой результат выдан за успех")
    except Отказ as е:
        if "не нашлось" in str(е):
            print("  ✓ пустой сбор — честный отказ, а не пустая таблица")
        else:
            ошибки.append(f"отказ не про пустоту: {е}")
    for о in ошибки:
        print(f"  ✗ {о}")
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("--что", dest="что", default="", help="что ищем: аптека, кофейня…")
    р.add_argument("--город", dest="город", default="almaty")
    р.add_argument("--адрес", dest="адрес", default="")
    р.add_argument("--порт", type=int, default=РОБОТ)
    р.add_argument("--в-файл", dest="в_файл", default="")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return _самопроверка()
    адрес = а.адрес or (f"https://2gis.kz/{а.город}/search/{urllib.request.quote(а.что)}"
                        if а.что else "")
    if not адрес:
        р.error("нужен --что или --адрес")
    try:
        д = собрать(адрес, а.порт)
    except Отказ as е:
        print(f"отказ: {е}")
        return 1
    if а.в_файл:
        путь = pathlib.Path(а.в_файл).expanduser()
        путь.parent.mkdir(parents=True, exist_ok=True)
        путь.write_text(json.dumps(д, ensure_ascii=False, indent=2))
        print(f"организаций {len(д['rows'])} → {путь}")
        print(f"  {д['caption']}")
    else:
        print(json.dumps(д, ensure_ascii=False, indent=2)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
