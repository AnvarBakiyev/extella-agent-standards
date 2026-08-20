# Эксперт платформы: form_to_app (global, cspl=nohup)
# Обобщение board_draw_form (20.08.2026, запрос Анвара «CSO должен уметь и в
# таблицы»): агент чата (CSO КТ, дефолтный, любой с run_expert) сочиняет форму
# из словаря пяти форм и доставляет её В ЛЮБОЕ окно устройства:
#   получатель "таблица" → в_таблицу.py (лист «От агента · <источник>»),
#   получатель "доска"   → на_доску.py  (слой с меткой источника),
#   получатель "отчёт"   → в_отчёт.py   (страница-отчёт файлом).
# Правило агентам — rule_id 50809 (global, обновлено с board_draw_form на
# form_to_app; правка через MCP update_rule — REST rules/update из чужого
# скоупа отвечает 500). board_draw_form оставлен живым для совместимости.
# ЗАКРЕПЛЕНИЕ: только targets массивом ["24f37e45-8c9f-4896-b64f-0dcd0cd8b0e4"]
# (MacBook Анвара) — дефолтный таргет VPS. Сохранён REST /api/expert/save.
# Проверено 20.08.2026: лист «От агента · чат» лёг в живую Таблицу, листы
# человека не тронуты. У агентов CSO run_expert есть (12 инструментов, без
# sys__all__).

import json, os, subprocess, tempfile

ф = """{{форма}}"""
куда = """{{получатель}}""".strip().lower()
ист = """{{источник}}"""
if not ист or ист.startswith("{{"):
    ист = "чат"
if not куда or куда.startswith("{{"):
    куда = "таблица"
СКРИПТЫ = {"доска": "на_доску.py", "board": "на_доску.py",
           "таблица": "в_таблицу.py", "table": "в_таблицу.py",
           "отчёт": "в_отчёт.py", "отчет": "в_отчёт.py", "report": "в_отчёт.py"}
if not ф or ф.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра форма: передай JSON формы"}, ensure_ascii=False), flush=True)
elif куда not in СКРИПТЫ:
    print(json.dumps({"ошибка": "получатель «" + куда + "» неизвестен: доска, таблица, отчёт"}, ensure_ascii=False), flush=True)
else:
    try:
        д = json.loads(ф)
        врем = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(д, врем, ensure_ascii=False)
        врем.close()
        py = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
        if not os.path.exists(py):
            py = "python3"
        инстр = os.path.expanduser("~/Documents/Extella/extella-agent-standards/tools/" + СКРИПТЫ[куда])
        итог = subprocess.run([py, инстр, "--файл", врем.name, "--источник", ист],
                              capture_output=True, text=True, timeout=90)
        os.unlink(врем.name)
        print(json.dumps({"код": итог.returncode,
                          "вывод": ((итог.stdout or "") + (итог.stderr or "")).strip()[-1200:]},
                         ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
