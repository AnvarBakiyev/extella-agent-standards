#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Права клиентского агента: эталон урезанного набора инструментов (№9).

ЗАЧЕМ. Клиентский продуктовый агент делает работу через СВОИХ экспертов
(`run_expert`) — управлять аккаунтом ему не нужно. Прежний эталон («Агент 1С,
шесть инструментов, ни одного опасного») устарел молча: у одноимённого двойника
на аккаунте оказалось 45 инструментов, включая `delete_agent` и `delete_profile`.
Эталон, который никто не проверяет, перестаёт быть эталоном.

ГЛАВНОЕ, ЧТО ЗДЕСЬ ПРОВЕРЯЕТСЯ — не длина списка, а **сплошной допуск**
`sys__all__sys_mcp_extella`. Это не инструмент, а весь платформенный MCP-сервер
целиком. Проверено вживую 05.08.2026: у агента «Kazakh Lawyer» в списке 16
безобидных галочек, среди них НЕТ `list_agents`, — и он всё равно вызвал
`list_agents_mcp_extella` и вернул точные id агентов аккаунта. Значит галочки
рядом со сплошным допуском — украшение: агент клиента фактически держит и
`delete_agent`, и `delete_profile`, и `delete_expert`.

Эталон продуктового агента (набор «Агента 1С», проверен на живом продукте):
    rules_list, concept_search, run_expert, check_task, get_default_target,
    health_check                                   — и НИ ОДНОГО сплошного допуска.
Продукту с собственной памятью добавляются kv_get / kv_set / kv_search / kv_list
и list_experts / get_expert. Всё остальное — обоснование в паспорте агента.

Запуск:
    python3 tools/check_agent_tools.py                 # все агенты аккаунта
    python3 tools/check_agent_tools.py agent_XXXX ...  # только указанные
    python3 tools/check_agent_tools.py --selftest      # без сети

Коды выхода: 0 — опасных прав у клиентских агентов нет, 1 — есть.
"""
import sys
from pathlib import Path

CANON_APP = Path.home() / "Documents/Extella/extella-recruiting-agent/app"

# Сплошной допуск: одна строка вместо всего сервера. Ловим по префиксу — платформа
# уже показала два написания (`sys__all__`, `sys__server__`), появится третье.
BLANKET_PREFIXES = ("sys__all__", "sys__server__")

# Опасное = может снести чужую работу или выпустить ключ наружу. Имена у платформы
# в двух поколениях (`agent_delete` и `delete_agent`), поэтому сверяем по корням.
DANGEROUS_ROOTS = (
    "delete_agent", "agent_delete", "delete_profile", "profile_delete",
    "delete_expert", "expert_delete", "save_expert", "expert_save",
    "delete_rule", "rules_remove", "delete_concept", "concept_remove",
    "delete_kv", "kv_remove", "delete_target", "targets_remove",
    "create_token", "token_generate", "revoke_token", "token_revoke",
    "create_agent", "agent_create", "create_profile", "profile_create",
)

# Минимум, без которого продуктовый агент не работает вовсе.
REQUIRED_ROOTS = ("run_expert", "check_task")


def _root(tool: str) -> str:
    return tool[: -len("_mcp_extella")] if tool.endswith("_mcp_extella") else tool


def audit(agent: dict) -> dict:
    """Разбор прав одного агента. Без сети — чтобы это можно было проверить тестом."""
    tools = [str(t) for t in (agent.get("tools") or [])]
    roots = [_root(t) for t in tools]
    blanket = [t for t in tools if t.startswith(BLANKET_PREFIXES)]
    dangerous = sorted({r for r in roots if r in DANGEROUS_ROOTS})
    missing = [r for r in REQUIRED_ROOTS if r not in roots]
    return {
        "id": agent.get("id"), "name": agent.get("name"), "count": len(tools),
        "blanket": blanket, "dangerous": dangerous, "missing": missing,
        # Сплошной допуск делает список галочек недействительным: фактические права —
        # весь сервер, а значит и всё опасное в нём.
        "effective_full_access": bool(blanket),
    }


def report(result: dict) -> bool:
    """Печать вердикта. True = у агента есть чем навредить аккаунту."""
    bad = result["effective_full_access"] or bool(result["dangerous"])
    mark = "✗" if bad else "✓"
    print("  %s %-34s %s (инструментов: %d)" % (mark, result["name"], result["id"], result["count"]))
    if result["blanket"]:
        print("      СПЛОШНОЙ ДОПУСК: %s — галочки рядом с ним не ограничивают ничего;"
              % ", ".join(result["blanket"]))
        print("      фактически агент держит весь платформенный MCP, включая удаление агентов")
    if result["dangerous"]:
        print("      опасные галочки: " + ", ".join(result["dangerous"]))
    if result["missing"]:
        print("      нет обязательного: " + ", ".join(result["missing"]))
    return bad


def selftest() -> int:
    cases = [
        ({"id": "a1", "name": "эталон", "tools": [
            "rules_list_mcp_extella", "concept_search_mcp_extella", "run_expert_mcp_extella",
            "check_task_mcp_extella", "get_default_target_mcp_extella", "health_check_mcp_extella"]},
         False),
        ({"id": "a2", "name": "со сплошным допуском", "tools": [
            "sys__all__sys_mcp_extella", "run_expert_mcp_extella", "check_task_mcp_extella"]},
         True),
        ({"id": "a3", "name": "с удалением", "tools": [
            "run_expert_mcp_extella", "check_task_mcp_extella", "agent_delete_mcp_extella"]},
         True),
    ]
    for agent, expect in cases:
        got = audit(agent)
        bad = got["effective_full_access"] or bool(got["dangerous"])
        if bad != expect:
            print("FAIL: «%s» оценён как %s, ожидалось %s" % (agent["name"], bad, expect))
            return 1
    print("селфтест: сплошной допуск и удаление ловятся, эталон проходит")
    return 0


def main(argv) -> int:
    if "--selftest" in argv:
        return selftest()
    if not (CANON_APP / "platform_client.py").is_file():
        print("  ~ канона platform_client нет на этой машине — читать аккаунт нечем")
        return 0
    sys.path.insert(0, str(CANON_APP))
    import platform_client                                    # noqa: E402

    wanted = [a for a in argv if a.startswith("agent_")]
    agents = platform_client.list_agents()
    if wanted:
        agents = [a for a in agents if a.get("id") in wanted]
    print("Права агентов аккаунта (эталон — набор «Агента 1С», без сплошного допуска)\n")
    bad = 0
    for agent in agents:
        if report(audit(agent)):
            bad += 1
    print("")
    if bad:
        print("АГЕНТОВ С ПРАВАМИ ВЫШЕ ЭТАЛОНА: %d из %d." % (bad, len(agents)))
        print("Клиентскому агенту достаточно run_expert + check_task + чтение.")
        return 1
    print("Все агенты в пределах эталона (%d)." % len(agents))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
