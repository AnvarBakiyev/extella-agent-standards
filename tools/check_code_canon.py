#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт канона в КОДЕ — там, где мы горим, а не в паспорте.

Паспорт описывает намерение, и его мы проверяем давно. Но самые дорогие поломки живут в коде и
до сих пор не проверялись ничем. Обе — из одного дня, 28.07.2026:

1. **Захардкоженный id агента как фолбэк.** В `ta_wa_inbound_tick` стоял жёсткий фолбэк на
   `agent_iVWWFbzjmNwxgZNB5chIr` — это «Extella Qwen fine-tuned» на модели `extella_test_llm`,
   то есть НЕ платформенный Qwen. На машине разработчика нужный id был задан в конфиге, фолбэк
   не срабатывал, и дефекта не было видно. У коллеги и у клиента автоматизация молча уехала бы
   на запрещённую каноном модель.

2. **Общий ключ, прочитанный из скоупа рабочего агента.** `global: true` НЕ гарантирует общего
   чтения: собственная копия ключа у агента побеждает общую. Реестр автоматизаций читался пустым
   у всех рабочих агентов, хотя 12 записей были целы — они лежали в скоупе
   `agent_extella_default`. Поэтому писатель и читатель общего ключа обязаны работать под одним
   и тем же агентом.

Оба случая ловятся чтением кода, и оба не давали никакой ошибки в рантайме.

Осознанное исключение помечается в самой строке: `# canon-ok: причина` (или `// canon-ok:`).
Пометка без причины не считается — иначе она станет способом отключить гейт молча.

Как пользоваться:
  python3 check_code_canon.py experts/ app/            # каталоги и файлы
  python3 check_code_canon.py --json experts/
  python3 check_code_canon.py --selftest

Коды выхода: 0 — чисто, 1 — есть нарушения, 2 — нечего проверять.
"""
import json
import os
import re
import sys

# Стабильный id платформенного агента в коде. Восемь символов и больше — чтобы не ловить
# слова вроде agent_id или agent_name.
AGENT_ID_RE = re.compile(r"\bagent_[A-Za-z0-9][A-Za-z0-9_-]{7,}\b")
# Имена, которые агентом не являются: это параметры и ключи конфигурации, а не живой id.
AGENT_ID_ALLOWED = {
    "agent_extella_default",      # исторический скоуп общих объектов; ловится гейтом account-scope
    "agent_XXXXXXXX",             # намеренная заглушка тулбара: НЕ настоящий id, поставлена, чтобы
                                  # заголовок был синтаксически заполнен без чужого агента
    "agent_id", "agent_ids", "agent_name", "agent_run", "agent_get", "agent_list",
    "agent_create", "agent_update", "agent_delete", "agent_runs", "agent_passport",
    "agent_cabinet", "agent_extella_alibaba_default",
}
# Старые имена общих реестров и их свободная замена (перенос 28.07.2026).
LEGACY_SHARED_KEYS = {
    "_mkt_automations": "extella:automations:v2",
    "_mkt_installed": "extella:installed:v2",
    "capability:registry": "capability:registry:v2",
}
KV_CALL_RE = re.compile(r"kv[_/](set|get|search|remove)|/api/kv/")
CANON_OK_RE = re.compile(r"(#|//)\s*canon-ok:\s*\S+")
CODE_EXT = (".py", ".js")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def _files(paths):
    out = []
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isfile(p) and p.endswith(CODE_EXT):
            out.append(p)
        elif os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                dn[:] = [d for d in dn if d not in SKIP_DIRS]
                out += [os.path.join(dp, f) for f in fn if f.endswith(CODE_EXT)]
    return sorted(set(out))


def check_source(name, src):
    """Нарушения канона в одном файле. Возвращает список issue со стабильными кодами."""
    issues = []
    lines = src.splitlines()

    # 1. Живой id агента, зашитый в код
    for n, line in enumerate(lines, 1):
        if CANON_OK_RE.search(line):
            continue
        for m in AGENT_ID_RE.finditer(line):
            ident = m.group(0)
            if ident in AGENT_ID_ALLOWED:
                continue
            # Имя-префикс, а не идентификатор: agent_passport_, agent_control_ и подобные.
            if ident.endswith("_"):
                continue
            # Заглушки из одинаковых символов (agent_XXXXXXXX, agent_00000000) настоящими не бывают.
            tail = ident[len("agent_"):]
            if len(set(tail.lower())) <= 1:
                continue
            issues.append({
                "code": "HARDCODED_AGENT_ID", "severity": "error",
                "path": "%s:%d" % (name, n), "value": ident,
                "message_ru": "в коде зашит живой id агента «%s». Если это фолбэк — он молча "
                              "уведёт клиента на чужого агента и, возможно, на запрещённую "
                              "модель. Нет обязательного — честный отказ, а не подмена" % ident,
                "message_en": "a live agent id %r is hardcoded. If this is a fallback, it will "
                              "silently route the client to someone else's agent and possibly a "
                              "forbidden model. Missing required input means an honest refusal, "
                              "not a substitution" % ident,
            })

    # 2. Чтение ОТРАВЛЕННОГО старого имени общего реестра.
    # ПОПРАВКА 28.07 ночью: прежняя редакция требовала закреплять agent_extella_default. Это был
    # правильный обход, но не лечение — и он конфликтовал с запретом платного Claude в тулбаре.
    # Опыт показал, что `global: true` исправен у имени БЕЗ истории, а ломали его близнецы.
    # Поэтому канон теперь другой: общие реестры живут в свободных именах и читаются обычным
    # общим чтением. Ловим не отсутствие пиннинга, а чтение старых имён.
    # Старое имя — это ИМЕННО оно, а не префикс нового: `capability:registry:v2` содержит
    # `capability:registry` подстрокой, и наивное вхождение ловило бы правильный код.
    touched = [k for k in LEGACY_SHARED_KEYS
               if re.search(re.escape(k) + r"(?![:\w-])", src)]
    # Файл, который знает и НОВОЕ имя, участвует в переносе осознанно: он либо зеркалит старое
    # в новое, либо держит старое честным запасным путём. Такие не трогаем — иначе гейт валит
    # ровно тот код, который и делает переход. Ловим тех, кто про перенос не знает вовсе.
    migration_aware = any(v in src for v in LEGACY_SHARED_KEYS.values())
    if touched and KV_CALL_RE.search(src) and not migration_aware \
            and not CANON_OK_RE.search(src):
        issues.append({
            "code": "LEGACY_SHARED_KEY_READ", "severity": "error",
            "path": name, "value": ", ".join(sorted(touched)),
            "message_ru": "файл читает старое имя общего реестра (%s). У этих имён накопились "
                          "близнецы в разных областях, и платформа отдаёт не ту запись: живая "
                          "проверка 28.07 дала 0 записей при 12 целых. Читай свободное имя — "
                          "%s" % (", ".join(sorted(touched)),
                                  ", ".join("%s → %s" % (k, v) for k, v in
                                            sorted(LEGACY_SHARED_KEYS.items()) if k in touched)),
            "message_en": "the file reads a legacy shared registry name (%s). Those names have "
                          "twins across scopes and the platform returns the wrong record: a live "
                          "check on 28.07 returned 0 records while 12 were intact. Read the free "
                          "name instead — %s" % (", ".join(sorted(touched)),
                                                 ", ".join("%s -> %s" % (k, v) for k, v in
                                                           sorted(LEGACY_SHARED_KEYS.items())
                                                           if k in touched)),
        })
    return issues


def check_paths(paths):
    files = _files(paths)
    issues = []
    for f in files:
        try:
            src = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        issues += check_source(os.path.relpath(f), src)
    return {"files": len(files), "issues": issues,
            "ready": not any(i["severity"] == "error" for i in issues)}


GOOD_SRC = '''
# expert: demo
def demo(agent_id=""):
    """Честный отказ вместо подмены."""
    if not agent_id:
        return {"status": "error", "message_ru": "не задан агент", "message_en": "no agent"}
    return {"status": "success"}
'''

BAD_AGENT_SRC = '''
def demo(agent_id=""):
    qwen = agent_id or "agent_iVWWFbzjmNwxgZNB5chIr"
    return qwen
'''

BAD_SCOPE_SRC = '''
def read_registry(token):
    return api("/api/kv/get", {"key": "capability:registry", "global": True})
'''   # старое отравленное имя

OK_SCOPE_SRC = '''
def read_registry(token):
    return api("/api/kv/get", {"key": "capability:registry:v2", "global": True})
'''

# Зеркалирование и честный запасной путь — это и есть перенос, а не его нарушение.
MIGRATING_SRC = '''
def rebuild(api):
    data = api("/api/kv/get", {"key": "capability:registry"})
    api("/api/kv/set", {"key": "capability:registry:v2", "value": data, "global": True})
'''

OK_MARKED_SRC = '''
def legacy(agent_id=""):
    return agent_id or "agent_hM0qLHwu-Hw_4sjydTU1g"  # canon-ok: фикстура теста, не фолбэк
'''


def selftest():
    print("Самопроверка канона кода:")
    ok = True
    cases = [
        ("честный отказ проходит", GOOD_SRC, None),
        ("зашитый id агента — поймано", BAD_AGENT_SRC, "HARDCODED_AGENT_ID"),
        ("чтение старого отравленного имени — поймано", BAD_SCOPE_SRC,
         "LEGACY_SHARED_KEY_READ"),
        ("чтение свободного имени проходит", OK_SCOPE_SRC, None),
        ("файл, знающий про перенос, не считается нарушением", MIGRATING_SRC, None),
        ("осознанное исключение с причиной проходит", OK_MARKED_SRC, None),
    ]
    for label, src, expected in cases:
        codes = {i["code"] for i in check_source("demo.py", src)}
        got = (expected in codes) if expected else (not codes)
        print(("PASS: " if got else "FAIL: ") + label)
        ok = ok and got

    # Пометка без причины не должна выключать гейт — иначе её начнут ставить молча.
    empty_mark = 'x = "agent_iVWWFbzjmNwxgZNB5chIr"  # canon-ok:'
    if "HARDCODED_AGENT_ID" in {i["code"] for i in check_source("d.py", empty_mark)}:
        print("PASS: пометка без причины гейт не выключает")
    else:
        ok = False
        print("FAIL: пометка без причины выключила гейт")

    # Заглушка тулбара — не идентификатор агента, она поставлена ВМЕСТО чужого id.
    if not check_source("d.js", "var BOOTSTRAP_AGENT_SCOPE = 'agent_XXXXXXXX';"):
        print("PASS: намеренная заглушка нарушением не считается")
    else:
        ok = False
        print("FAIL: заглушка посчитана нарушением")

    for i in check_source("d.py", BAD_AGENT_SRC) + check_source("d.py", BAD_SCOPE_SRC):
        if not i.get("message_ru") or not i.get("message_en"):
            ok = False
            print("FAIL: сообщение без одного из языков: %s" % i["code"])
            break
    else:
        print("PASS: каждое сообщение на двух языках (§3.26)")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        print("Как пользоваться: python3 check_code_canon.py [--json] <файлы или каталоги>")
        return 2
    report = check_paths(paths)
    if not report["files"]:
        print("ОШИБКА: не найдено ни одного файла .py/.js")
        return 2
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    for i in report["issues"]:
        print("ОШИБКА: %s — %s" % (i["path"], i["message_ru"]))
    print("ИТОГ: " + ("канон соблюдён (файлов %d)" % report["files"] if report["ready"]
                      else "нарушений %d — исправь выше" % len(report["issues"])))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
