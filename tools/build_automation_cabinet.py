#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кабинет АВТОМАТИЗАЦИИ собирается из паспорта автоматизации, а не пишется руками.

Замысел (Анвар, 26.07.2026): главный объект интерфейса — установленная автоматизация
(Агент 1С, Kazakh Lawyer, турагентство). Платформенные агенты внутри неё — СКРЫТЫЕ
технические компоненты: они показываются как состав, а не как объекты верхнего уровня.

Путь такой:
    заполнил automation_passport → проверялка пропустила → кабинет автоматизации появился сам
    → автоматизация видна в Evolution Console

Как пользоваться:
  python3 build_automation_cabinet.py паспорт.yaml                → JSON для интерфейса
  python3 build_automation_cabinet.py паспорт.yaml --markdown     → человекочитаемый вид
  python3 build_automation_cabinet.py паспорт.yaml --agent a.yaml → добавить кабинет агента-компонента
  python3 build_automation_cabinet.py --selftest

Коды выхода: 0 — собран, 1 — паспорт не проходит стандарт, 2 — файл не прочитан.

ЧЕСТНОСТЬ ВСТРОЕНА: состояние автоматизации НЕ выдумывается. Кабинет объявляет, по каким
адресам его брать (контракт `/api/health` + `/api/state`), и прямо перечисляет, что до
получения состояния показывать «неизвестно», а не «в порядке».
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import load_passport                      # единый разбор файла
from check_automation_passport import check_report, GOOD            # единый источник правил
from check_agent_passport import GOOD_JSON as AGENT_GOOD_JSON       # образец паспорта агента
import build_agent_cabinet as agent_cabinet                         # кабинет агента-компонента

CABINET_SCHEMA = "extella.automation_cabinet.v1"

# Чего кабинет автоматизации честно не показывает, пока платформа/продукт не дадут механизм.
AUTOMATION_LIMITS = {
    "ru": [
        "Состояние берётся только из контракта автоматизации: пока /api/state не ответил, показываем «неизвестно», а не «в порядке».",
        "«Порт отвечает» не означает «работает» — это разные состояния.",
        "Расходы — оценка по квитанциям, а не биллинговый факт.",
        "Действия, меняющие состояние (обновить, откатить, включить), появятся только после доказанного откатa.",
        "Между аккаунтами видимости нет: автоматизация видна в пределах своего аккаунта.",
    ],
    "en": [
        "State comes only from the automation contract: until /api/state answers, we show «unknown», not «healthy».",
        "«The port answers» does not mean «it works» — these are different states.",
        "Cost is an estimate from receipts, not a billing fact.",
        "State-changing actions (update, rollback, enable) appear only after rollback is proven.",
        "No cross-account visibility: an automation is visible within its own account.",
    ],
}


def build(doc, agent_passports=None):
    """Собирает кабинет автоматизации. Ничего не выдумывает: только заявленное в паспорте."""
    report = check_report(doc)
    if not report["ready"]:
        raise ValueError("Automation Cabinet requires a valid automation passport")

    a = doc.get("automation") or {}
    comp = doc.get("components") or {}
    ops = doc.get("operations") or {}
    svc = a.get("service") or {}
    reader = a.get("state_reader") or {}

    agents = []
    for item in comp.get("platform_agents") or []:
        agents.append({
            "platform_agent_id": item.get("platform_agent_id"),
            "role_ru": item.get("role") or "роль не описана",
            "role_en": item.get("role") or "role not described",
            "provider_expected": item.get("provider_expected"),
            # Агент — технический компонент: в интерфейсе он раскрывается по требованию.
            "surface": "component",
            "open_agent_cabinet": True,
        })

    # Кабинеты агентов-компонентов собираются ТЕМ ЖЕ генератором, что и раньше.
    component_cabinets = []
    for passport in (agent_passports or []):
        try:
            component_cabinets.append(agent_cabinet.build(passport))
        except ValueError as exc:
            component_cabinets.append({"error": str(exc)})

    return {
        "schema": CABINET_SCHEMA,
        "passport": {
            "automation_id": a.get("automation_id"),
            # Чем паспорт связан с установленной карточкой. Пусто — значит id совпадают.
            "registry_card_id": a.get("registry_card_id") or a.get("automation_id"),
            "name": a.get("name") or {},
            "owner": a.get("owner"),
            "business_goal": a.get("business_goal"),
            "version": a.get("version"),
            "languages": a.get("languages") or [],
            "limits": [x for x in (a.get("limits") or []) if x],
            "help_surface": a.get("help_surface"),
        },
        "composition": {
            # Главная мысль: агенты — состав, а не отдельные объекты верхнего уровня.
            "title_ru": "Из чего состоит автоматизация",
            "title_en": "What the automation is made of",
            "platform_agents": agents,
            "experts": comp.get("experts") or [],
            "schedules": comp.get("schedules") or [],
            "integrations": comp.get("integrations") or [],
            "knowledge": comp.get("knowledge") or [],
            "rules": comp.get("rules") or [],
            "note_ru": "Платформенные агенты — технические компоненты автоматизации; "
                       "управление одним агентом открывается в его Agent Cabinet.",
            "note_en": "Platform agents are technical components; managing a single agent opens "
                       "its Agent Cabinet.",
        },
        "state_contract": {
            # Как читать состояние. Порядок источников — это контракт для Console:
            # эксперт на устройстве сильнее localhost, потому что порт есть только у нас.
            "source": "expert" if reader.get("expert") else ("service" if svc.get("state") else None),
            "reader": {
                "expert": reader.get("expert"),
                "method": reader.get("method"),
                # Точный объект вызова: Console зовёт эксперта по нему, а не по имени продукта.
                "params": reader.get("params") or {},
                "schema": reader.get("schema"),
                "execution_device": reader.get("execution_device"),
                "data_device": reader.get("data_device"),
                "evidence": reader.get("evidence"),
                "note_ru": "Вызов закрепляется массивом targets, ответ обязан нести id устройства: "
                           "одиночный target платформа игнорирует молча, и ответ приходит с чужой машины.",
                "note_en": "The call is pinned with a targets array and the answer must carry the "
                           "device id: a single target is silently ignored and the answer may come "
                           "from a foreign machine.",
            } if reader.get("expert") else None,
            "health": svc.get("health"),
            "state": svc.get("state"),
            "port": svc.get("port"),
            "unknown_is_honest_ru": "Если состояние не получено — показывать «состояние недоступно» "
                                    "и блокировать действия, зависящие от состояния.",
            "unknown_is_honest_en": "If state is not received — show «state unavailable» and block "
                                    "state-dependent actions.",
            "fields": ["enabled", "active_version", "last_run", "last_result", "last_error",
                       "schedules", "checked_at"],
        },
        "attention": {
            # Считается автоматически, а не пишется руками.
            "external_writes": [i for i in (comp.get("integrations") or [])
                                if isinstance(i, dict) and i.get("external_writes")],
            "external_schedules": [s for s in (comp.get("schedules") or [])
                                   if isinstance(s, dict) and s.get("kind") == "external_cron"],
            "agents_count": len(agents),
        },
        "operations": {
            "owner_on_call": ops.get("owner_on_call"),
            "rollback": ops.get("rollback"),
            "success_metric": ops.get("success_metric"),
            "observability": ops.get("observability"),
        },
        "limits": AUTOMATION_LIMITS,
        "component_cabinets": component_cabinets,
        "warnings": report["warnings"],
    }


def as_markdown(cab):
    p, c = cab["passport"], cab["composition"]
    name = p.get("name") or {}
    out = ["# Automation Cabinet — кабинет автоматизации: %s" % agent_cabinet._markdown_text(name.get("ru") or ""), ""]
    out.append("**Владелец:** %s · **Версия:** %s · **Цель:** %s" % (
        agent_cabinet._markdown_text(p.get("owner") or "—"),
        agent_cabinet._markdown_text(p.get("version") or "—"),
        agent_cabinet._markdown_text(p.get("business_goal") or "—")))
    out += ["", "## %s" % c["title_ru"], ""]
    out.append("| Компонент | Что это | Подробности |")
    out.append("|---|---|---|")
    for ag in c["platform_agents"]:
        out.append("| платформенный агент | %s | технический компонент, открывается Agent Cabinet |"
                   % agent_cabinet._markdown_text(ag.get("role_ru") or "—"))
    for e in c["experts"]:
        nm = e.get("name") if isinstance(e, dict) else e
        out.append("| способность | %s | %s |" % (agent_cabinet._markdown_text(str(nm)),
                   "обязательная" if isinstance(e, dict) and e.get("required") else "—"))
    for s in c["schedules"]:
        out.append("| расписание | %s | %s |" % (agent_cabinet._markdown_text(str(s.get("id"))),
                                                 agent_cabinet._markdown_text(str(s.get("kind")))))
    for i in c["integrations"]:
        out.append("| интеграция | %s | %s |" % (
            agent_cabinet._markdown_text(str(i.get("kind"))),
            "пишет наружу" if i.get("external_writes") else "только чтение"))
    out += ["", "_%s_" % c["note_ru"], "", "## Состояние — только из контракта", ""]
    sc = cab["state_contract"]
    out.append("Адреса: `%s` и `%s` (порт %s). %s" % (sc.get("health"), sc.get("state"),
                                                      sc.get("port"), sc["unknown_is_honest_ru"]))
    out += ["", "## Границы (честно)", ""] + ["- " + x for x in cab["limits"]["ru"]]
    out += ["", "## Чего НЕ обещает автоматизация", ""] + ["- " + agent_cabinet._markdown_text(x) for x in p["limits"]]
    return "\n".join(out) + "\n"


def selftest():
    print("Самопроверка генератора кабинета автоматизации:")
    ok = True
    cab = build(json.loads(json.dumps(GOOD)))
    checks = [
        ("схема кабинета автоматизации", cab["schema"] == CABINET_SCHEMA),
        ("агенты показаны как СОСТАВ, а не как объекты верхнего уровня",
         all(a["surface"] == "component" for a in cab["composition"]["platform_agents"])),
        ("у каждого агента-компонента есть вход в его Agent Cabinet",
         all(a["open_agent_cabinet"] for a in cab["composition"]["platform_agents"])),
        ("состав перечислен целиком (агенты, способности, расписания, интеграции)",
         cab["composition"]["platform_agents"] and cab["composition"]["experts"]
         and len(cab["composition"]["schedules"]) == 2 and cab["composition"]["integrations"]),
        ("контракт состояния объявлен адресами и полями",
         cab["state_contract"]["health"] == "/api/health"
         and cab["state_contract"]["state"] == "/api/state"
         and "last_error" in cab["state_contract"]["fields"]),
        ("«состояние недоступно» объявлено честным на двух языках",
         "состояние недоступно" in cab["state_contract"]["unknown_is_honest_ru"]
         and "state unavailable" in cab["state_contract"]["unknown_is_honest_en"]),
        ("границы кабинета на двух языках",
         len(cab["limits"]["ru"]) == len(cab["limits"]["en"]) == 5),
        ("внимание считается само: запись наружу и внешний cron найдены",
         len(cab["attention"]["external_writes"]) == 1
         and len(cab["attention"]["external_schedules"]) == 1),
        ("границы автоматизации из паспорта перенесены", len(cab["passport"]["limits"]) == 2),
        ("markdown собирается", "Automation Cabinet" in as_markdown(cab)),
    ]
    for label, cond in checks:
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and bool(cond)

    bad = json.loads(json.dumps(GOOD))
    bad["automation"]["limits"] = []
    try:
        build(bad)
        ok = False
        print("FAIL: паспорт без границ не должен давать кабинет")
    except ValueError:
        print("PASS: паспорт без границ — кабинет не собирается (тот же гейт, что на выпуске)")

    mixed = json.loads(json.dumps(GOOD))
    mixed["components"]["platform_agents"][0]["provider_expected"] = "anthropic"
    try:
        build(mixed)
        ok = False
        print("FAIL: агент на чужом провайдере не должен давать кабинет")
    except ValueError:
        print("PASS: агент-компонент не на Qwen — кабинет не собирается (канон)")

    comp = build(json.loads(json.dumps(GOOD)),
                 agent_passports=[json.loads(AGENT_GOOD_JSON)])
    if comp["component_cabinets"] and comp["component_cabinets"][0].get("schema", "").startswith("extella.agent_cabinet"):
        print("PASS: кабинет агента-компонента собран ТЕМ ЖЕ генератором (композиция)")
    else:
        ok = False
        print("FAIL: композиция кабинетов не работает")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    paths = [a for a in argv if not a.startswith("-")]
    agent_files = []
    if "--agent" in argv:
        idx = argv.index("--agent")
        agent_files = [a for a in argv[idx + 1:] if not a.startswith("-")]
        paths = [p for p in paths if p not in agent_files]
    if len(paths) != 1:
        print("Как пользоваться:")
        print("  python3 build_automation_cabinet.py паспорт.yaml [--markdown] [--agent паспорт_агента.yaml]")
        print("  python3 build_automation_cabinet.py --selftest")
        return 2
    if not os.path.exists(paths[0]):
        print("ОШИБКА: файл не найден: %s" % paths[0])
        return 2
    doc = load_passport(paths[0])
    agents = [load_passport(f) for f in agent_files if os.path.exists(f)]
    try:
        cab = build(doc, agent_passports=agents)
    except ValueError:
        report = check_report(doc if isinstance(doc, dict) else {})
        for e in report["errors"]:
            print("ОШИБКА: %s — %s" % (e["path"], e["message_ru"]))
        print("ИТОГ: кабинет не собран — паспорт автоматизации не проходит стандарт")
        return 1
    print(as_markdown(cab) if "--markdown" in argv else json.dumps(cab, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
