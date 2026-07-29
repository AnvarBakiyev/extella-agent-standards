#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверка живого агента с его паспортом: права разошлись — скажи когда и кто.

ЗАЧЕМ. 29.07.2026 выяснилось, что системы диагностики у нас нет. Платформа хранит полную
историю версий агента — кто, когда и что менял, — и мы не использовали её ни разу. Правка
прав, сделанная 28.07, пролежала сутки и всплыла случайно, при чтении ответа на другую
операцию. Ни одна из семи находок дня не пришла сама.

Мы продаём «агента как управляемый объект», не имея этого у себя. Все три куска уже лежат:
платформа даёт историю, паспорт даёт эталон, Console даёт экран. Не хватало сравнения.

ЧТО ДЕЛАЕТ. Только читает. Для каждого паспорта из `passports/*.yaml`:

  • берёт живые права через `agent/get`;
  • сравнивает с зафиксированными в паспорте (`optional.agent.observed_tools_count`
    и `observed_dangerous_tools`);
  • если разошлись — ищет в истории версий МОМЕНТ расхождения: какая версия первой
    принесла новое право, когда и кто её сохранил.

Разошлось — это НЕ обязательно плохо. 28.07 право `create_token` выдал владелец осознанно,
изменив заодно инструкцию агента. Смысл сверки не «запретить», а «не дать измениться
молча»: изменение прав прода обязано быть видимым, а не всплывать через сутки случайно.

Как пользоваться:
  python3 check_agent_drift.py            сверить все паспорта
  python3 check_agent_drift.py --selftest самопроверка без сети

Коды выхода: 0 — расхождений нет, 1 — есть (или паспорт не читается).
"""
import json
import os
import re
import subprocess
import sys

API = "https://api.extella.ai"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DANGER = ("delete_agent", "delete_profile", "token_generate", "create_token", "revoke_token")


def _token():
    p = os.path.expanduser("~/.claude/extella_mcp_server.py")
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            m = re.search(r'AUTH_TOKEN\s*=\s*["\']([^"\']{16,})["\']', fh.read())
            if m:
                return m.group(1)
    p = os.path.expanduser("~/extella_wizard/app/config.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh).get("auth_token")
    return None


def live_agent(agent_id, token):
    out = subprocess.run([
        "curl", "-s", "--max-time", "40", "-X", "POST", API + "/api/agent/get",
        "-H", "X-Auth-Token: " + token, "-H", "X-Profile-Id: default",
        "-H", "X-Agent-Id: " + agent_id, "-H", "Content-Type: application/json",
        "-d", json.dumps({"agent_id": agent_id}),
    ], capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except Exception:
        return None
    return d.get("agent") or d


def tool_names(agent):
    return [x if isinstance(x, str) else x.get("name", "")
            for x in ((agent or {}).get("tools") or [])]


def when_appeared(agent, tool):
    """Первая версия, принёсшая право. Возвращает (когда, кто) или None.

    Ради этого сверка и писалась: расхождение без «когда и кто» заставляет гадать.
    """
    for v in (agent or {}).get("versions") or []:
        if tool in (v.get("tools") or []):
            return (v.get("updatedAt") or v.get("createdAt") or "?",
                    v.get("updatedBy") or "?")
    return None


def compare(passport, agent):
    """Разошлось ли. Возвращает список строк-расхождений."""
    opt = ((passport.get("optional") or {}).get("agent")) or {}
    fixed_count = opt.get("observed_tools_count")
    fixed_danger = set(opt.get("observed_dangerous_tools") or [])
    live = tool_names(agent)
    live_danger = set(n for n in live if any(k in n for k in DANGER))
    out = []
    if isinstance(fixed_count, int) and fixed_count != len(live):
        out.append("прав было %d, стало %d" % (fixed_count, len(live)))
    for extra in sorted(live_danger - fixed_danger):
        out.append("ПОЯВИЛОСЬ опасное право «%s»" % extra)
    for gone in sorted(fixed_danger - live_danger):
        out.append("снято опасное право «%s»" % gone)
    return out


def selftest():
    print("Самопроверка сверки:")
    ok = True

    def case(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond

    p = {"optional": {"agent": {"observed_tools_count": 2,
                                "observed_dangerous_tools": ["delete_agent_mcp_extella"]}}}
    same = {"tools": ["a", "delete_agent_mcp_extella"]}
    case("совпадение — расхождений нет", compare(p, same) == [])
    grew = {"tools": ["a", "delete_agent_mcp_extella", "create_token_mcp_extella"]}
    d = compare(p, grew)
    case("новое опасное право поймано", any("ПОЯВИЛОСЬ" in x and "create_token" in x for x in d))
    case("изменение числа прав поймано", any("стало 3" in x for x in d))
    shrunk = {"tools": ["a"]}
    case("снятие права видно", any("снято" in x for x in compare(p, shrunk)))
    hist = {"versions": [{"tools": ["create_token_mcp_extella"],
                          "updatedAt": "2026-07-28T16:55:49Z", "updatedBy": "u1"}]}
    case("момент появления найден в истории",
         when_appeared(hist, "create_token_mcp_extella") == ("2026-07-28T16:55:49Z", "u1"))
    case("отсутствующее право истории не имеет",
         when_appeared(hist, "delete_agent_mcp_extella") is None)
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    try:
        import yaml
    except ImportError:
        print("ОШИБКА: нужен PyYAML")
        return 1
    token = _token()
    if not token:
        print("ОШИБКА: токен Extella не найден")
        return 1
    import glob
    drifted = 0
    files = sorted(glob.glob(os.path.join(ROOT, "passports", "*.yaml")))
    if not files:
        print("паспортов нет — сверять не с чем")
        return 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        aid = ((doc.get("agent") or {}).get("platform_agent_id") or "").strip()
        name = (doc.get("agent") or {}).get("name") or os.path.basename(f)
        if not aid:
            print("  ? %-26s в паспорте нет platform_agent_id" % name[:26])
            drifted += 1
            continue
        agent = live_agent(aid, token)
        if agent is None:
            print("  ? %-26s платформа не ответила" % name[:26])
            drifted += 1
            continue
        diffs = compare(doc, agent)
        if not diffs:
            print("  ✓ %-26s совпадает с паспортом" % name[:26])
            continue
        drifted += 1
        print("  ✗ %-26s РАСХОЖДЕНИЕ:" % name[:26])
        for d in diffs:
            print("      " + d)
            m = re.search(r"«([^»]+)»", d)
            if m and "ПОЯВИЛОСЬ" in d:
                w = when_appeared(agent, m.group(1))
                if w:
                    print("        когда: %s · кто: %s" % w)
    print("\nИТОГ: расхождений %d из %d" % (drifted, len(files)))
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
