#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регистратор: находит агентов, у которых нет паспорта, и заводит черновик.

ЗАЧЕМ. Ночная сверка `check_agent_drift.py` обходит ПАСПОРТА и сравнивает их с живыми
агентами. Значит агент, у которого паспорта нет, для неё не существует: он появился —
и остался невидимым навсегда. Замер 30.07 на нашем же аккаунте: живых агентов 20,
паспортов 5. Пятнадцать агентов не видит никто.

Пока агентов делаем мы вдвоём, это терпимо. Как только их начнут делать многие — а к
этому мы и идём, — «кто это создал и что оно умеет» перестанет быть вопросом памяти.
Поэтому обход разворачивается: идём ОТ ЖИВЫХ АГЕНТОВ, а не от паспортов.

ЧТО ДЕЛАЕТ. На платформе — только читает (`agent/list`). Локально пишет черновики в
`passports/_drafts/`, отдельно от настоящих паспортов: ни гейт паспортов, ни сверка
их не подхватывают (оба берут `passports/*.yaml`, подкаталог туда не попадает).

ЧЕГО НЕ ДЕЛАЕТ И ПОЧЕМУ. Машина заполняет ТОЛЬКО наблюдаемое: имя, id, модель, права,
даты. Поля «что делает для клиента», «границы», «как откатить» остаются пустыми с
пометкой, что их пишет человек. Соблазн дать их выдумать модели велик, но паспорт с
правдоподобной выдумкой хуже отсутствия паспорта: весь наш гейт на входе построен
против ровно такой лжи. Пустое поле честно говорит «никто ещё не сказал», выдуманное
врёт с уверенным лицом.

Как пользоваться:
  python3 tools/register_new_agents.py             отчёт + завести черновики
  python3 tools/register_new_agents.py --dry-run   только отчёт, ничего не писать
  python3 tools/register_new_agents.py --selftest  самопроверка без сети

Коды выхода: 0 — новых агентов нет; 2 — есть агенты без паспорта (это не ошибка,
а повод дописать; для крона отличается от настоящего сбоя, у которого код 1).
"""
import json
import os
import re
import subprocess
import sys

API = "https://api.extella.ai"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "passports", "_drafts")
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


def live_agents(token):
    """Список агентов аккаунта. Пустой список — не то же самое, что «нет доступа»:
    при сбое возвращаем None, чтобы крон не отрапортовал «всё чисто» на молчании."""
    out = subprocess.run([
        "curl", "-s", "--max-time", "40", "-X", "POST", API + "/api/agent/list",
        "-H", "X-Auth-Token: " + token, "-H", "X-Profile-Id: default",
        # X-Agent-Id обязателен синтаксически даже для самого agent/list; значение
        # сервером не проверяется (живая проверка 26.07), поэтому здесь заглушка,
        # а НЕ чей-то настоящий id — на чужом аккаунте его всё равно нет.
        "-H", "X-Agent-Id: agent_XXXXXXXX", "-H", "Content-Type: application/json",
        "-d", "{}",
    ], capture_output=True, text=True).stdout
    try:
        return json.loads(out).get("agents")
    except Exception:
        return None


def passported_ids():
    """id, у которых паспорт уже есть. Читаем регуляркой, а не PyYAML: регистратор
    должен работать и там, где зависимости не поставлены."""
    import glob
    ids = set()
    for f in glob.glob(os.path.join(ROOT, "passports", "*.yaml")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            m = re.search(r'platform_agent_id:\s*["\']?([A-Za-z0-9_-]+)', fh.read())
            if m:
                ids.add(m.group(1))
    return ids


def slug(name, agent_id):
    """Имя файла = имя агента + хвост id.

    Хвост обязателен: на живом аккаунте два разных агента называются «Extella Qwen
    fine-tuned», и по одному имени второй черновик молча не завёлся бы — файл ведь
    «уже есть». Имя агента вообще не обязано быть уникальным, id обязан."""
    # Кириллицу НЕ выкидываем: почти все наши агенты названы по-русски, и на
    # [^a-z0-9] их имя стиралось целиком — файл получался «Sw9PEb.yaml», по которому
    # человек не найдёт ничего. Поймано на первом же живом прогоне.
    s = re.sub(r"[^a-zа-яё0-9]+", "_", str(name or "").lower()).strip("_")[:40]
    tail = re.sub(r"[^A-Za-z0-9]+", "", str(agent_id or ""))[-6:] or "noid"
    return (s + "__" + tail) if s else tail


def draft_text(agent):
    tools = [t for t in (agent.get("tools") or []) if isinstance(t, str)]
    dangerous = sorted({d for d in DANGER for t in tools if d in t})
    q = lambda v: json.dumps(str(v or ""), ensure_ascii=False)
    lines = [
        "# ЧЕРНОВИК ПАСПОРТА — заведён регистратором, человеком не подтверждён.",
        "#",
        "# Машина вписала только то, что видит на платформе: имя, id, модель, права, даты.",
        "# Пустые поля ниже machine НЕ заполняет сознательно — она не знает, что этот агент",
        "# делает для клиента и где его границы. Выдуманный паспорт хуже отсутствующего:",
        "# он врёт с уверенным лицом, а на входе у нас стоит гейт ровно против этого.",
        "#",
        "# Заполни пустые поля и перенеси файл в passports/ — тогда его подхватят гейт",
        "# паспортов и ночная сверка прав.",
        "---",
        "status: draft",
        "agent:",
        "  name: %s" % q(agent.get("name")),
        "  platform_agent_id: %s" % q(agent.get("id")),
        '  owner: ""                 # кто отвечает за агента после запуска',
        '  business_goal: ""         # какую задачу закрывает — словами человека',
        "  model_profile: %s" % q(agent.get("model")),
        "  provider_observed: %s" % q(agent.get("provider")),
        "  created_at_observed: %s" % q(agent.get("created_at")),
        "  updated_at_observed: %s" % q(agent.get("updated_at")),
        "",
        "observed:",
        "  tools_count: %d" % len(tools),
        "  dangerous_tools: [%s]" % ", ".join(q(d) for d in dangerous),
        "",
        "limits:",
        '  - ""                      # чего агент НЕ делает — минимум одна честная строка',
        "",
        "rollback:",
        '  how: ""                   # как вернуть состояние; только читает — так и напиши',
        "",
    ]
    return "\n".join(lines)


def selftest():
    print("Самопроверка регистратора:")
    ok = True

    def case(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond

    a = {"id": "agent_Test123", "name": "Проверка", "model": "qwen3.7-max",
         "provider": "alibaba", "tools": ["run_expert_mcp_extella", "delete_agent_mcp_extella"]}
    t = draft_text(a)
    case("черновик помечен как черновик", "status: draft" in t and "ЧЕРНОВИК" in t)
    case("опасное право замечено", '"delete_agent"' in t)
    case("бизнес-цель НЕ выдумана", 'business_goal: ""' in t)
    case("границы оставлены человеку", "limits:" in t and 'чего агент НЕ делает' in t)
    case("id перенесён", "agent_Test123" in t)
    case("имя попадает в слаг", slug("Travel agent", "agent_eUSuv3").startswith("travel_agent__"))
    case("тёзки не сталкиваются",
         slug("Extella Qwen fine-tuned", "agent_94LlJKUmGsIYoZa2Imbuc")
         != slug("Extella Qwen fine-tuned", "agent_iVWWFbzjmNwxgZNB5chIr"))
    case("агент без имени не теряется", slug("", "agent_zzz999") != "")
    case("русское имя остаётся в имени файла",
         slug("Агент 1С", "agent_aYgv8O").startswith("агент_1с__"))
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    dry = "--dry-run" in argv
    token = _token()
    if not token:
        print("ОШИБКА: токен Extella не найден")
        return 1
    agents = live_agents(token)
    if agents is None:
        print("ОШИБКА: платформа не ответила — список агентов не получен")
        return 1
    known = passported_ids()
    missing = [a for a in agents if a.get("id") not in known]
    print("Живых агентов: %d · с паспортом: %d · без паспорта: %d"
          % (len(agents), len(agents) - len(missing), len(missing)))
    if not missing:
        return 0
    if not dry:
        os.makedirs(DRAFTS, exist_ok=True)
    for a in missing:
        path = os.path.join(DRAFTS, slug(a.get("name"), a.get("id")) + ".yaml")
        exists = os.path.exists(path)
        mark = "уже есть" if exists else ("завёл бы" if dry else "черновик заведён")
        tools = [t for t in (a.get("tools") or []) if isinstance(t, str)]
        danger = sorted({d for d in DANGER for t in tools if d in t})
        print("  • %-34s %s%s" % (str(a.get("name"))[:34], mark,
                                  ("  ⚠ опасных прав: " + ", ".join(danger)) if danger else ""))
        # Существующий черновик НЕ трогаем: человек мог начать его заполнять,
        # и перезапись стёрла бы его работу — ровно то, за что мы ругаем чужой код.
        if not dry and not exists:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(draft_text(a))
    print("\nЧерновики: %s" % os.path.relpath(DRAFTS, ROOT))
    print("Заполни пустые поля и перенеси в passports/ — дальше их подхватят гейт и сверка.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
