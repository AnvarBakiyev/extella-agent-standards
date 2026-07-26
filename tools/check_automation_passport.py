#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка паспорта АВТОМАТИЗАЦИИ Extella.

Автоматизация — то, что клиент установил и чем пользуется (Агент 1С, Kazakh Lawyer,
турагентство). Платформенные агенты внутри неё — технические компоненты.

Зачем отдельная проверялка: паспорт агента (`check_agent_passport.py`) описывает ОДИН
агент, и его поле `platform_agent_id` — одна строка. Составная автоматизация из
нескольких агентов этим паспортом не описывается — пробел зафиксирован в
`AGENT_CABINET_STANDARD.md` и в ТЗ «автоматизация как главный объект».

Как пользоваться:
  python3 check_automation_passport.py путь/к/паспорту.yaml   (или .json)
  python3 check_automation_passport.py путь/к/паспорту.yaml --json
  python3 check_automation_passport.py --selftest

Коды выхода: 0 — готов к выпуску, 1 — есть ошибки, 2 — файл не прочитан.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import load_passport, is_blank   # единый разбор файла и понятие «пусто»

AGENT_ID_RE = re.compile(r"^agent_[A-Za-z0-9_\-]{6,}$")
SCHEDULE_KINDS = {"external_cron", "internal", "in_service"}
# Канон: клиентские автоматизации работают на платформенном Qwen (провайдер alibaba).
ALLOWED_PROVIDER = "alibaba"


def _issue(errors, code, path, ru, en):
    errors.append({"code": code, "severity": "error", "path": path,
                   "message_ru": ru, "message_en": en})


def _warn(warns, code, path, ru, en):
    warns.append({"code": code, "severity": "warning", "path": path,
                  "message_ru": ru, "message_en": en})


def check_report(doc):
    """Возвращает единый структурированный отчёт: {ready, errors, warnings}."""
    errors, warns = [], []
    a = doc.get("automation") if isinstance(doc.get("automation"), dict) else {}
    comp = doc.get("components") if isinstance(doc.get("components"), dict) else {}
    ops = doc.get("operations") if isinstance(doc.get("operations"), dict) else {}
    budgets = doc.get("budgets") if isinstance(doc.get("budgets"), dict) else {}

    # Пустой шаблон — говорим это одной фразой, а не двадцатью ошибками.
    name = a.get("name") if isinstance(a.get("name"), dict) else {}
    if is_blank(a.get("automation_id")) and is_blank(name.get("ru")) and is_blank(name.get("en")):
        _issue(errors, "AUTOMATION_TEMPLATE_EMPTY", "automation",
               "паспорт не заполнен — это пустой шаблон; впиши id, название, владельца, цель "
               "и хотя бы один компонент, потом запусти проверку снова",
               "the passport is an empty template — fill in id, name, owner, goal and at least "
               "one component, then run the check again")
        return {"ready": False, "errors": errors, "warnings": warns}

    # 1. Тождество автоматизации
    if is_blank(a.get("automation_id")):
        _issue(errors, "AUTOMATION_ID_REQUIRED", "automation.automation_id",
               "не указан стабильный id автоматизации — по имени связывать запрещено",
               "a stable automation_id is required — linking by display name is forbidden")
    for lang in ("ru", "en"):
        if is_blank(name.get(lang)):
            _issue(errors, "AUTOMATION_NAME_%s_REQUIRED" % lang.upper(),
                   "automation.name.%s" % lang,
                   "нет названия на языке «%s» — интерфейс обязан быть на двух языках (§3.26)" % lang,
                   "the %s name is missing — the product ships in both languages (§3.26)" % lang)
    for field, ru, en in (
        ("owner", "не назначен владелец автоматизации", "the automation has no owner"),
        ("business_goal", "не сказано, какую задачу автоматизация закрывает",
         "the business goal is not stated"),
        ("version", "не указана версия автоматизации", "the automation version is missing"),
    ):
        if is_blank(a.get(field)):
            _issue(errors, "AUTOMATION_%s_REQUIRED" % field.upper(), "automation." + field, ru, en)

    langs = a.get("languages") if isinstance(a.get("languages"), list) else []
    if not ({"ru", "en"} <= set(langs)):
        _issue(errors, "AUTOMATION_LANGUAGES_REQUIRED", "automation.languages",
               "languages обязан содержать ru и en (§3.26)",
               "languages must contain both ru and en (§3.26)")

    # 2. Границы и пояснение — те же обязательные правила, что у агента
    limits = a.get("limits") if isinstance(a.get("limits"), list) else []
    if not [x for x in limits if not is_blank(x)]:
        _issue(errors, "AUTOMATION_LIMITS_REQUIRED", "automation.limits",
               "не названы границы: напиши хотя бы одну честную строку «чего эта автоматизация "
               "НЕ делает». Без границ выпуск запрещён",
               "limits are missing: state at least one honest line about what this automation "
               "does NOT do. Without limits the release is forbidden")
    if is_blank(a.get("help_surface")):
        _issue(errors, "AUTOMATION_HELP_REQUIRED", "automation.help_surface",
               "не указано, где на экране живёт пояснение «? Как это работает» (§3.20)",
               "help_surface is missing: where the «? How it works» panel lives (§3.20)")

    # 3. Контракт состояния — та причина, по которой Console не будет врать
    svc = a.get("service") if isinstance(a.get("service"), dict) else {}
    for field, default in (("health", "/api/health"), ("state", "/api/state")):
        if is_blank(svc.get(field)):
            _issue(errors, "AUTOMATION_SERVICE_%s_REQUIRED" % field.upper(),
                   "automation.service." + field,
                   "не указан адрес «%s» — без контракта состояния Console покажет «порт отвечает» "
                   "как «работает» (ожидается %s)" % (field, default),
                   "the «%s» endpoint is missing — without the state contract the Console would "
                   "report «port answers» as «works» (expected %s)" % (field, default))

    # 4. Состав: платформенные агенты — компоненты, и каждый проверяется как агент
    agents = comp.get("platform_agents") if isinstance(comp.get("platform_agents"), list) else []
    if not agents:
        _issue(errors, "AUTOMATION_AGENTS_REQUIRED", "components.platform_agents",
               "не перечислен ни один платформенный агент автоматизации",
               "no platform agent is listed for the automation")
    seen = set()
    for i, ag in enumerate(agents):
        base = "components.platform_agents[%d]" % i
        if not isinstance(ag, dict):
            _issue(errors, "AUTOMATION_AGENT_SHAPE", base,
                   "элемент состава должен быть объектом с platform_agent_id",
                   "each component must be an object with platform_agent_id")
            continue
        aid = str(ag.get("platform_agent_id") or "").strip()
        if not aid:
            _issue(errors, "AUTOMATION_AGENT_ID_REQUIRED", base + ".platform_agent_id",
                   "у компонента нет стабильного id агента",
                   "the component has no stable agent id")
        elif not AGENT_ID_RE.match(aid):
            _issue(errors, "AUTOMATION_AGENT_ID_INVALID", base + ".platform_agent_id",
                   "id «%s» не похож на стабильный идентификатор вида agent_..." % aid,
                   "id %r is not a stable identifier starting with agent_" % aid)
        elif aid in seen:
            _issue(errors, "AUTOMATION_AGENT_DUPLICATE", base + ".platform_agent_id",
                   "агент указан в составе дважды — потребители считаются по id, дубль ломает счёт",
                   "the agent is listed twice — consumers are counted by id, a duplicate breaks it")
        else:
            seen.add(aid)
        provider = str(ag.get("provider_expected") or "").strip().lower()
        if provider and provider != ALLOWED_PROVIDER:
            _issue(errors, "AUTOMATION_AGENT_PROVIDER_FORBIDDEN", base + ".provider_expected",
                   "провайдер «%s» запрещён: клиентские автоматизации работают на платформенном "
                   "Qwen (alibaba)" % provider,
                   "provider %r is forbidden: client automations run on the platform Qwen "
                   "(alibaba)" % provider)
        elif not provider:
            _warn(warns, "AUTOMATION_AGENT_PROVIDER_EMPTY", base + ".provider_expected",
                  "не указан ожидаемый провайдер — проверка «только Qwen» не сработает",
                  "provider_expected is empty — the «Qwen only» check cannot run")
        if is_blank(ag.get("role")):
            _warn(warns, "AUTOMATION_AGENT_ROLE_EMPTY", base + ".role",
                  "не сказано, зачем этот агент в автоматизации",
                  "the component role is not stated")

    # 5. Расписания: вид обязателен — Console должна знать, где тик живёт
    for i, s in enumerate(comp.get("schedules") or []):
        base = "components.schedules[%d]" % i
        if not isinstance(s, dict) or is_blank(s.get("id")):
            _issue(errors, "AUTOMATION_SCHEDULE_ID_REQUIRED", base,
                   "у расписания нет id", "the schedule has no id")
            continue
        kind = str(s.get("kind") or "").strip()
        if kind not in SCHEDULE_KINDS:
            _issue(errors, "AUTOMATION_SCHEDULE_KIND_INVALID", base + ".kind",
                   "вид расписания «%s» неизвестен — допустимо: %s"
                   % (kind, ", ".join(sorted(SCHEDULE_KINDS))),
                   "schedule kind %r is unknown — allowed: %s"
                   % (kind, ", ".join(sorted(SCHEDULE_KINDS))))

    # 6. Эксплуатация и бюджеты
    for field, ru, en in (
        ("owner_on_call", "не назначен дежурный", "no on-call owner"),
        ("rollback", "не описан путь отката", "no rollback path"),
        ("success_metric", "не сказано, как понять, что автоматизация работает хорошо",
         "no success metric"),
    ):
        if is_blank(ops.get(field)):
            _issue(errors, "AUTOMATION_OPS_%s_REQUIRED" % field.upper(), "operations." + field, ru, en)
    for field in ("max_duration_ms", "max_llm_tokens", "max_external_actions"):
        v = budgets.get(field)
        if v is None or (isinstance(v, (int, float)) and v <= 0 and field != "max_external_actions"):
            _warn(warns, "AUTOMATION_BUDGET_EMPTY", "budgets." + field,
                  "бюджет «%s» не задан — расходы и время не ограничены" % field,
                  "budget %r is not set — cost and duration are unbounded" % field)

    return {"ready": not errors, "errors": errors, "warnings": warns}


GOOD = {
    "automation": {
        "automation_id": "extella_travel_agency",
        "name": {"ru": "Турагентство: лиды и подогрев базы", "en": "Travel agency: leads and nurture"},
        "owner": "Анвар", "business_goal": "возвращать спящую базу туристов без ручного обзвона",
        "version": "1.0.0", "languages": ["ru", "en"],
        "service": {"port": 8766, "health": "/api/health", "state": "/api/state"},
        "limits": ["не отправляет сообщения без человека", "не обещает наличие тура без Tourvisor"],
        "help_surface": "панель автоматизации, кнопка «? Как это работает»",
    },
    "components": {
        "platform_agents": [{"platform_agent_id": "agent_eUSxxxxxxxxxx", "role": "квалификация лида",
                             "provider_expected": "alibaba"}],
        "experts": [{"name": "ta_birthday_scan", "required": True}],
        "schedules": [{"id": "campaigns_birthday", "kind": "external_cron", "cadence": "daily"},
                      {"id": "inbound_poller", "kind": "internal", "cadence": "~20s"}],
        "integrations": [{"kind": "whatsapp", "external_writes": True}],
        "knowledge": ["скрипты подогрева"], "rules": ["подтверждение человеком перед отправкой"],
    },
    "budgets": {"max_duration_ms": 600000, "max_llm_tokens": 50000,
                "max_delegation_depth": 2, "max_external_actions": 20},
    "operations": {"observability": "квитанции в панели", "owner_on_call": "Анвар",
                   "rollout": "поэтапно", "rollback": "версия -1 + бэкап конфига",
                   "success_metric": "доля отвеченных лидов за сутки"},
}

BAD = {
    "automation": {
        "automation_id": "x", "name": {"ru": "Юрист", "en": ""},
        "owner": "", "business_goal": "", "version": "1.0", "languages": ["ru"],
        "service": {"port": 8767, "health": "", "state": ""},
        "limits": [], "help_surface": "",
    },
    "components": {
        "platform_agents": [
            {"platform_agent_id": "по имени", "role": "", "provider_expected": "custom"},
        ],
        "schedules": [{"id": "nightly", "kind": "cron"}],
    },
    "budgets": {}, "operations": {},
}

RULE_CHECKS = [
    ("нет английского названия", "AUTOMATION_NAME_EN_REQUIRED"),
    ("нет владельца", "AUTOMATION_OWNER_REQUIRED"),
    ("нет бизнес-цели", "AUTOMATION_BUSINESS_GOAL_REQUIRED"),
    ("нет двух языков", "AUTOMATION_LANGUAGES_REQUIRED"),
    ("нет границ", "AUTOMATION_LIMITS_REQUIRED"),
    ("нет пояснения", "AUTOMATION_HELP_REQUIRED"),
    ("нет адреса health", "AUTOMATION_SERVICE_HEALTH_REQUIRED"),
    ("нет адреса state", "AUTOMATION_SERVICE_STATE_REQUIRED"),
    ("id агента не стабильный", "AUTOMATION_AGENT_ID_INVALID"),
    ("провайдер не Qwen запрещён", "AUTOMATION_AGENT_PROVIDER_FORBIDDEN"),
    ("вид расписания неизвестен", "AUTOMATION_SCHEDULE_KIND_INVALID"),
    ("нет дежурного", "AUTOMATION_OPS_OWNER_ON_CALL_REQUIRED"),
    ("нет отката", "AUTOMATION_OPS_ROLLBACK_REQUIRED"),
    ("нет метрики успеха", "AUTOMATION_OPS_SUCCESS_METRIC_REQUIRED"),
]


def selftest():
    print("Самопроверка проверялки паспорта автоматизации:")
    ok = True
    good = check_report(json.loads(json.dumps(GOOD)))
    if good["ready"]:
        print("PASS: правильный паспорт проходит (ошибок 0)")
    else:
        ok = False
        print("FAIL: правильный паспорт не прошёл:")
        for e in good["errors"]:
            print("      - %s %s" % (e["code"], e["message_ru"]))
    bad = check_report(json.loads(json.dumps(BAD)))
    codes = {e["code"] for e in bad["errors"]}
    for label, code in RULE_CHECKS:
        if code in codes:
            print("PASS: %s — поймано" % label)
        else:
            ok = False
            print("FAIL: %s — НЕ поймано (%s)" % (label, code))
    empty = check_report({"automation": {"automation_id": "", "name": {"ru": "", "en": ""}}})
    if any(e["code"] == "AUTOMATION_TEMPLATE_EMPTY" for e in empty["errors"]) and len(empty["errors"]) == 1:
        print("PASS: пустой шаблон — одна понятная ошибка, а не двадцать")
    else:
        ok = False
        print("FAIL: пустой шаблон обработан неверно")
    dup = json.loads(json.dumps(GOOD))
    dup["components"]["platform_agents"].append(dup["components"]["platform_agents"][0])
    if any(e["code"] == "AUTOMATION_AGENT_DUPLICATE" for e in check_report(dup)["errors"]):
        print("PASS: дубль агента в составе — поймано")
    else:
        ok = False
        print("FAIL: дубль агента в составе — НЕ поймано")
    for e in check_report(BAD)["errors"] + check_report(BAD)["warnings"]:
        if not e.get("message_ru") or not e.get("message_en"):
            ok = False
            print("FAIL: сообщение без одного из языков: %s" % e["code"])
            break
    else:
        print("PASS: каждое сообщение на двух языках (§3.26)")
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("-")]
    if len(paths) != 1:
        print("Как пользоваться:")
        print("  python3 check_automation_passport.py путь/к/паспорту.yaml [--json]")
        print("  python3 check_automation_passport.py --selftest")
        return 2
    if not os.path.exists(paths[0]):
        print("ОШИБКА: файл не найден: %s" % paths[0])
        return 2
    doc = load_passport(paths[0])
    if not isinstance(doc, dict):
        print("ОШИБКА: внутри файла не паспорт автоматизации — ожидаются разделы automation, "
              "components, budgets, operations")
        return 2
    report = check_report(doc)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    for e in report["errors"]:
        print("ОШИБКА: %s — %s" % (e["path"], e["message_ru"]))
    for w in report["warnings"]:
        print("ВНИМАНИЕ: %s — %s" % (w["path"], w["message_ru"]))
    print("ИТОГ: " + ("ГОТОВА К ВЫПУСКУ" if report["ready"] else "НЕ ГОТОВА — исправь ошибки выше"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
