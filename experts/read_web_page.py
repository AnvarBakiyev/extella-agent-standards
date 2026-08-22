# Эксперт платформы: read_web_page (global, cspl=nohup)
# Чтение любой веб-страницы для агента: страница → форма «документ» → окно.
# Обёртка над tools/источник_страницы.py.
#
# ЗАЧЕМ ОТДЕЛЬНО ОТ СБОРЩИКА ОБЪЯВЛЕНИЙ. Тот знает разметку двух площадок и
# достаёт из неё поля. Здесь разбор не нужен вовсе: нужен текст статьи,
# инструкции, описания тендера. Два разных дела — два разных инструмента.
#
# ПРИВАТНОСТЬ ЗАПЕЧЁНА В ПОВЕДЕНИЕ, А НЕ В ПРЕДУПРЕЖДЕНИЕ. Сначала страница
# читается своими силами и никуда не уходит. Только если она пустая без
# скриптов, зовётся сторонний читатель — и в подписи формы это НАЗВАНО. Для
# внутренних адресов (localhost, 192.168.*, extella.ai) внешний путь закрыт
# совсем: данные контура наружу не отдаём даже ради удобства.
# description: Read ANY web page and turn it into the five-forms "документ" (document) form, optionally delivering it straight into the user's local apps. Unlike collect_kz_listings (which parses classified ads on two known sites), this works on any URL: articles, docs, tender descriptions, product pages. Params: адрес — the page URL; получатель — "отчёт" | "таблица" | "доска" | "диаграмма" | "" (empty = return the text summary only); источник — short label for the sheet/page name (default "страница"); только_сами — "да" forbids the external reader outright. PRIVACY: the page is first read locally and never leaves the machine; only if it is an empty script-driven shell does it fall back to the Jina reader, and the form's caption always states which of the two happened. Internal addresses (localhost, 192.168.*, extella.ai) never use the external reader. Returns: title, section count, which reader was used, and the first section.

import json, os, subprocess, tempfile

адрес = """{{адрес}}""".strip()
куда = """{{получатель}}""".strip().lower()
ист = """{{источник}}""".strip()
только_сами = """{{только_сами}}""".strip().lower()
if not ист or ист.startswith("{{"):
    ист = "страница"
if куда.startswith("{{"):
    куда = ""
if только_сами.startswith("{{"):
    только_сами = ""

КОРЕНЬ = os.path.expanduser("~/Documents/Extella/extella-agent-standards/tools/")
py = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
if not os.path.exists(py):
    py = "python3"

if not адрес or адрес.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра адрес: дайте ссылку на страницу"},
                     ensure_ascii=False), flush=True)
else:
    try:
        врем = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        врем.close()
        команда = [py, КОРЕНЬ + "источник_страницы.py", "--адрес", адрес,
                   "--в-файл", врем.name]
        if только_сами in ("да", "yes", "true", "1"):
            команда.append("--только-сами")
        итог = subprocess.run(команда, capture_output=True, text=True, timeout=180)
        if итог.returncode != 0 or not os.path.getsize(врем.name):
            os.unlink(врем.name)
            print(json.dumps({"ошибка": ((итог.stdout or "") + (итог.stderr or "")).strip()[-400:]
                              or "страницу прочитать не удалось"}, ensure_ascii=False), flush=True)
        else:
            д = json.load(open(врем.name, encoding="utf-8"))
            разделы = д.get("разделы") or []
            сводка = {"заголовок": д.get("заголовок"), "разделов": len(разделы),
                      "подпись": д.get("подпись")}
            # Первый раздел — чтобы агент понял, о чём страница, и не тащил
            # весь текст через модель: остальное уже лежит в приложении.
            if разделы:
                сводка["начало"] = разделы[0].get("текст", "")[:600]
            if куда:
                СКРИПТЫ = {"доска": "на_доску.py", "таблица": "в_таблицу.py",
                           "отчёт": "в_отчёт.py", "отчет": "в_отчёт.py",
                           "диаграмма": "в_диаграммы.py", "диаграммы": "в_диаграммы.py"}
                if куда in СКРИПТЫ:
                    д2 = subprocess.run([py, КОРЕНЬ + СКРИПТЫ[куда], "--файл", врем.name,
                                         "--источник", ист],
                                        capture_output=True, text=True, timeout=120)
                    сводка["доставка"] = ((д2.stdout or "") + (д2.stderr or "")).strip()[-500:]
                else:
                    сводка["доставка"] = ("получатель «" + куда + "» неизвестен: "
                                          "отчёт, таблица, доска, диаграмма")
            os.unlink(врем.name)
            print(json.dumps(сводка, ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
