# Эксперт платформы: board_draw_form (global, cspl=nohup)
# Канал «чат агента → Доска схем»: агент в чате ОС сочиняет форму из словаря
# пяти форм и зовёт этого эксперта — рисунок ложится на доску устройства,
# открытое окно перечитывается само (счётчик версий cabinet_server).
#
# Сохранён 20.08.2026 через REST /api/expert/save (MCP save_expert запрещён —
# молча пишет в чужой скоуп, см. build_agent_cabinet.py). Правило агенту
# чата — rule_id 50809 (global): контракт формы + закрепление устройства.
# ЗАКРЕПЛЕНИЕ: только targets МАССИВОМ — ["24f37e45-8c9f-4896-b64f-0dcd0cd8b0e4"]
# (MacBook Анвара); без него дефолтный таргет — VPS, и рисунок молча уезжает
# туда (замер 20.08.2026, первый прогон). kwargs: форма="", источник="чат".
# Грабля запуска: после перезапуска листенера нужен run_expert
# install_nohup_handler, иначе «'str' object is not callable».

import json, os, subprocess, tempfile

ф = """{{форма}}"""
ист = """{{источник}}"""
if not ист or ист.startswith("{{"):
    ист = "чат"
if not ф or ф.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра форма: передай JSON формы (связи/шаги/список)"}, ensure_ascii=False), flush=True)
else:
    try:
        д = json.loads(ф)
        врем = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(д, врем, ensure_ascii=False)
        врем.close()
        py = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
        if not os.path.exists(py):
            py = "python3"
        инстр = os.path.expanduser("~/Documents/Extella/extella-agent-standards/tools/на_доску.py")
        итог = subprocess.run([py, инстр, "--файл", врем.name, "--источник", ист],
                              capture_output=True, text=True, timeout=90)
        os.unlink(врем.name)
        print(json.dumps({"код": итог.returncode,
                          "вывод": ((итог.stdout or "") + (итог.stderr or "")).strip()[-1200:]},
                         ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
