# Эксперт платформы: form_to_app (global, cspl=nohup)
# Обобщение board_draw_form (20.08.2026, запрос Анвара «CSO должен уметь и в
# таблицы»): агент чата (CSO КТ, дефолтный, любой с run_expert) сочиняет форму
# из словаря пяти форм и доставляет её В ЛЮБОЕ окно устройства:
#   получатель "таблица"   → в_таблицу.py   (лист «От агента · <источник>»),
#   получатель "доска"     → на_доску.py    (слой с меткой источника),
#   получатель "отчёт"     → в_отчёт.py     (страница-отчёт файлом),
#   получатель "диаграмма" → в_диаграммы.py (чертёж в окне Диаграмм, draw.io).
# Диаграммы добавлены 23.08.2026: окно Диаграмм у человека уже было и строка
# агента в нём работала, а через этого эксперта получатель не назывался — то
# есть агенту в чате чертёж был недоступен, хотя всё для него стояло. Разница
# с доской: доска рисует от руки, диаграмма — строгий чертёж со стрелками.
# Правило агентам — rule_id 50809 (global, обновлено с board_draw_form на
# form_to_app; правка через MCP update_rule — REST rules/update из чужого
# скоупа отвечает 500). board_draw_form оставлен живым для совместимости.
# ГДЕ ЖИВЁТ ОБЩАЯ КОПИЯ — ЭТО НЕ МЕЛОЧЬ. Эксперт лежит в скоупе агента
# «Evolution Console · Lab» (agent_LqSG1ss4l1Hn-l-2kb9DA — тот же, что в
# tools/паспорт.py) и оттуда виден всем как global. Сохранение с ЛЮБЫМ другим
# X-Agent-Id (в том числе agent_extella_default и через MCP save_expert)
# создаёт ЛИЧНУЮ копию этого агента: она перекрывает общую только ему, а всем
# остальным по-прежнему отдаётся старая. Замер 23.08.2026: после такой правки
# «диаграмма» появилась у default и НЕ появилась у Баги, Строителя и Агента 1С.
# Проверять правку надо чтением от лица ЧУЖОГО агента, а не своего.
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
           "отчёт": "в_отчёт.py", "отчет": "в_отчёт.py", "report": "в_отчёт.py",
           "диаграмма": "в_диаграммы.py", "диаграммы": "в_диаграммы.py",
           "диаграмму": "в_диаграммы.py", "diagram": "в_диаграммы.py"}
if not ф or ф.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра форма: передай JSON формы"}, ensure_ascii=False), flush=True)
elif куда not in СКРИПТЫ:
    print(json.dumps({"ошибка": "получатель «" + куда + "» неизвестен: "
                      "доска, таблица, отчёт, диаграмма"}, ensure_ascii=False), flush=True)
else:
    try:
        д = json.loads(ф)
        врем = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(д, врем, ensure_ascii=False)
        врем.close()
        py = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
        if not os.path.exists(py):
            import shutil
            py = shutil.which("python3") or shutil.which("python") or "python3"
        # Путь к инструментам ищем, а не знаем: вшитый верен только на машине
        # автора, у коллеги репозиторий лежит иначе.
        корень = os.environ.get("EXTELLA_TOOLS") or ""
        if not корень:
            for где in ("~/Documents/Extella/extella-agent-standards/tools/",
                        "~/extella-agent-standards/tools/",
                        "~/Documents/extella-agent-standards/tools/",
                        "~/extella-cabinet/tools/"):
                если = os.path.expanduser(где)
                if os.path.isdir(если):
                    корень = если
                    break
        if not корень:
            raise RuntimeError("не нашёл папку инструментов Extella; "
                               "укажите её переменной среды EXTELLA_TOOLS")
        инстр = корень + СКРИПТЫ[куда]
        итог = subprocess.run([py, инстр, "--файл", врем.name, "--источник", ист],
                              capture_output=True, text=True, timeout=90)
        os.unlink(врем.name)
        print(json.dumps({"код": итог.returncode,
                          "вывод": ((итог.stdout or "") + (итог.stderr or "")).strip()[-1200:]},
                         ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
