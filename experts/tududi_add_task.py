# Эксперт платформы: tududi_add_task (global, cspl=nohup)
# «Поставь задачу…» из чата любого агента → задача в «Задачи и календарь»
# (tududi) на устройстве. Параметры: название · срок YYYY-MM-DD (опц.) ·
# заметка (опц.; встреча = задача со сроком и временем в заметке — сущности
# «событие» у tududi нет, честно записано в карточке продукта).
# Токен API живёт файлом ~/extella-cabinet/docker/tududi/токен_api (600) и
# ЧИТАЕТСЯ НА УСТРОЙСТВЕ — параметром не передаётся, в платформу не уезжает.
# Точка создания — POST /api/task (единственное число!) на внутренний порт
# 44789 с Bearer; /api/v1/tasks — только чтение (замер 21.08.2026, Swagger
# у сборки не отдаётся, путь добыт пробами). Правило агентам — rule_id 50809.
# Закрепление targets массивом ["24f37e45-8c9f-4896-b64f-0dcd0cd8b0e4"].
# Прогон: id=2 «Настроить Telegram-бота…» на 23.08 — виден в приложении.

import json, os, urllib.request

название = """{{название}}"""
срок = """{{срок}}"""
заметка = """{{заметка}}"""
if not название or название.startswith("{{"):
    print(json.dumps({"ошибка": "нет параметра название"}, ensure_ascii=False), flush=True)
else:
    try:
        ф = os.path.expanduser("~/extella-cabinet/docker/tududi/токен_api")
        токен = open(ф).read().strip()
        тело = {"name": название[:200]}
        if срок and not срок.startswith("{{"):
            тело["due_date"] = срок[:10]
        if заметка and not заметка.startswith("{{"):
            тело["note"] = заметка[:1000]
        з = urllib.request.Request("http://127.0.0.1:44789/api/task",
            data=json.dumps(тело, ensure_ascii=False).encode(),
            headers={"Authorization": "Bearer " + токен,
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(з, timeout=30) as о:
            д = json.loads(о.read().decode())
        print(json.dumps({"ок": True, "id": д.get("id"), "название": д.get("name"),
                          "срок": д.get("due_date")}, ensure_ascii=False), flush=True)
    except Exception as е:
        print(json.dumps({"ошибка": str(е)[:300]}, ensure_ascii=False), flush=True)
