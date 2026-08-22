# Эксперт платформы: collect_kz_listings (global, cspl=nohup)
# Сбор объявлений Krisha.kz (недвижимость) и Kolesa.kz (авто) — для агентов.
# Обёртка над tools/источник_объявлений.py: агент называет адрес страницы
# списка, эксперт приносит цены и сразу кладёт их в приложение человека.
#
# ЗАЧЕМ ОБЁРТКА, А НЕ «АГЕНТ САМ СХОДИТ». Агент по сети не ходит: сеть есть у
# устройства человека. Ещё важнее — разбор. Заставлять модель разбирать 400 КБ
# разметки значит платить за токены и получать выдумки там, где не распозналось.
# Разбор делает код, модель получает уже готовые строки.
#
# ЗАЧЕМ СРАЗУ ДОСТАВКА. Возвращать агенту 40 объявлений, чтобы он переслал их
# form_to_app, — двойной проезд через модель, где данные портятся. Здесь сбор и
# доставка в одном шаге, а агенту уходит короткая сводка: сколько собрано,
# минимум, максимум, средняя цена. Без получателя эксперт просто вернёт сводку.
#
# ЗАКРЕПЛЕНИЕ: только targets массивом (устройство человека) — иначе платформа
# уводит запуск на дефолтный таргет и сбор идёт не с той машины.
# description: Collect classified ads from Kazakh marketplaces Krisha.kz (real estate) and Kolesa.kz (cars) and deliver them straight into the user's local apps. Params: адрес — full URL of a LISTING page, filters included, copied from the browser (e.g. https://krisha.kz/prodazha/kvartiry/almaty/ or https://kolesa.kz/cars/toyota/camry/); страниц — how many pages to walk (1..20, default 1, ~20 ads per page); получатель — where to put the result: "таблица" | "доска" | "отчёт" | "диаграмма" | "" (empty = just return the summary, deliver nothing); источник — short label for the sheet/layer name (default "объявления"). Returns a summary: count, min/max/average price in tenge, and the first rows. Fields collected per ad: имя, цена_тенге, адрес, and where applicable комнат, площадь_м2, цена_за_м2, этаж, год, пробег_км, объём_л, коробка, ссылка.

import json, os, subprocess, tempfile

адрес = """{{адрес}}""".strip()
страниц = """{{страниц}}""".strip()
куда = """{{получатель}}""".strip().lower()
ист = """{{источник}}""".strip()
if not ист or ист.startswith("{{"):
    ист = "объявления"
if not страниц or страниц.startswith("{{"):
    страниц = "1"
if куда.startswith("{{"):
    куда = ""

КОРЕНЬ = os.path.expanduser("~/Documents/Extella/extella-agent-standards/tools/")
py = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
if not os.path.exists(py):
    py = "python3"

if not адрес or адрес.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра адрес: дайте ссылку на страницу "
                      "списка объявлений — со своими фильтрами, прямо из браузера"},
                     ensure_ascii=False), flush=True)
elif "krisha.kz" not in адрес and "kolesa.kz" not in адрес and "krysha.kz" not in адрес:
    # Отказываем прямо, а не пробуем «вдруг получится»: разбор написан под
    # разметку этих двух площадок, на чужом сайте он вернул бы пустой список
    # или, хуже, мусор, похожий на данные.
    print(json.dumps({"ошибка": "этот сборщик знает только krisha.kz и kolesa.kz; "
                      "для другого сайта нужен свой разбор"}, ensure_ascii=False), flush=True)
else:
    try:
        врем = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        врем.close()
        итог = subprocess.run(
            [py, КОРЕНЬ + "источник_объявлений.py", "--адрес", адрес,
             "--страниц", str(int(страниц)), "--в-файл", врем.name],
            capture_output=True, text=True, timeout=300)
        if итог.returncode != 0 or not os.path.getsize(врем.name):
            os.unlink(врем.name)
            print(json.dumps({"ошибка": ((итог.stdout or "") + (итог.stderr or "")).strip()[-400:]
                              or "сбор не дал ни одной строки"}, ensure_ascii=False), flush=True)
        else:
            д = json.load(open(врем.name, encoding="utf-8"))
            строки = д.get("rows") or []
            цены = [с.get("цена_тенге") for с in строки if с.get("цена_тенге")]
            сводка = {"собрано": len(строки), "заголовок": д.get("title"),
                      "подпись": д.get("caption")}
            if цены:
                сводка["цена_мин"] = min(цены)
                сводка["цена_макс"] = max(цены)
                сводка["цена_средняя"] = round(sum(цены) / len(цены))
            метры = [с.get("цена_за_м2") for с in строки if с.get("цена_за_м2")]
            if метры:
                сводка["средняя_за_м2"] = round(sum(метры) / len(метры))
            сводка["первые"] = строки[:3]
            if куда:
                # Доставку делает тот же form_to_app, что и всегда: один путь в
                # приложения человека, а не второй такой же рядом.
                форма = {"form": "list", "title": д.get("title"),
                         "caption": д.get("caption"),
                         "rows": [{"name": с.get("name"),
                                   "fields": {к: з for к, з in list(с.items())
                                              if к not in ("name", "описание")}}
                                  for с in строки]}
                ф2 = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
                json.dump(форма, ф2, ensure_ascii=False)
                ф2.close()
                СКРИПТЫ = {"доска": "на_доску.py", "таблица": "в_таблицу.py",
                           "отчёт": "в_отчёт.py", "отчет": "в_отчёт.py",
                           "диаграмма": "в_диаграммы.py", "диаграммы": "в_диаграммы.py"}
                if куда in СКРИПТЫ:
                    д2 = subprocess.run([py, КОРЕНЬ + СКРИПТЫ[куда], "--файл", ф2.name,
                                         "--источник", ист],
                                        capture_output=True, text=True, timeout=120)
                    сводка["доставка"] = ((д2.stdout or "") + (д2.stderr or "")).strip()[-500:]
                else:
                    сводка["доставка"] = ("получатель «" + куда + "» неизвестен: "
                                          "таблица, доска, отчёт, диаграмма")
                os.unlink(ф2.name)
            os.unlink(врем.name)
            print(json.dumps(сводка, ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
