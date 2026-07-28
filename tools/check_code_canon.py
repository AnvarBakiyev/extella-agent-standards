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
    "agent_extella_default",      # канонический скоуп общих объектов — пиннинг обязателен
    "agent_id", "agent_ids", "agent_name", "agent_run", "agent_get", "agent_list",
    "agent_create", "agent_update", "agent_delete", "agent_runs", "agent_passport",
    "agent_cabinet", "agent_extella_alibaba_default",
}
# Ключи, которые по смыслу общие для всего аккаунта.
SHARED_KEYS = ("_mkt_", "capability:registry", "composer:catalog", "capability:steps",
               "cspl:registry")
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

    # 2. Общий ключ, тронутый без канонического скоупа
    touches_shared = [k for k in SHARED_KEYS if k in src]
    if touches_shared and KV_CALL_RE.search(src):
        if "agent_extella_default" not in src and not CANON_OK_RE.search(src):
            issues.append({
                "code": "SHARED_KEY_WITHOUT_CANONICAL_SCOPE", "severity": "error",
                "path": name, "value": ", ".join(sorted(touches_shared)),
                "message_ru": "файл работает с общим ключом (%s), но нигде не закрепляет скоуп "
                              "agent_extella_default. `global: true` общего чтения НЕ даёт: своя "
                              "копия ключа у агента побеждает общую молча. Писатель и читатель "
                              "обязаны быть под одним агентом" % ", ".join(sorted(touches_shared)),
                "message_en": "the file works with a shared key (%s) but never pins the "
                              "agent_extella_default scope. `global: true` does NOT guarantee a "
                              "shared read: an agent's own copy silently wins. Writer and reader "
                              "must run under the same agent" % ", ".join(sorted(touches_shared)),
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
'''

OK_SCOPE_SRC = '''
def read_registry(token):
    hdr = {"X-Agent-Id": "agent_extella_default"}
    return api("/api/kv/get", {"key": "capability:registry"}, hdr)
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
        ("общий ключ без канонического скоупа — поймано", BAD_SCOPE_SRC,
         "SHARED_KEY_WITHOUT_CANONICAL_SCOPE"),
        ("общий ключ с закреплённым скоупом проходит", OK_SCOPE_SRC, None),
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

    # agent_extella_default — это и есть канон, он не нарушение.
    if not check_source("d.py", 'hdr = {"X-Agent-Id": "agent_extella_default"}'):
        print("PASS: канонический скоуп не считается нарушением")
    else:
        ok = False
        print("FAIL: канонический скоуп посчитан нарушением")

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
