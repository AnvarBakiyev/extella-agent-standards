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
# A2: где живёт автоматизация. server/client_server джанитор не трогает — каталога на диске нет.
HOSTING_PROFILES = {"local", "server", "client_server"}
# A4: как ПДн проходят через коннектор. Умолчания нет — «не сказано» это не «не трогает».
PERSONAL_DATA_MODES = {"none", "reads", "stores"}
# Ссылка на секрет выглядит как «где лежит», а не как сам секрет. Живой секрет в паспорте —
# это утечка в git и в кабинет клиента, поэтому ошибка, а не предупреждение.
SECRET_VALUE_RE = re.compile(r"[A-Za-z0-9_\-]{24,}")


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

    # 2.1. Где живёт автоматизация (A2). Без этого джанитор снесёт серверную карточку как
    # «мёртвую» — у неё нет и не должно быть каталога на диске.
    hosting = str(a.get("hosting_profile") or "").strip().lower()
    if not hosting:
        _issue(errors, "AUTOMATION_HOSTING_REQUIRED", "automation.hosting_profile",
               "не указано, где живёт автоматизация (local | server | client_server). Без этого "
               "джанитор удалит серверную карточку как «мёртвую», а клиент не увидит, где его агент",
               "hosting_profile is missing (local | server | client_server). Without it the janitor "
               "deletes a server-hosted card as «dead» and the client cannot see where the agent lives")
    elif hosting not in HOSTING_PROFILES:
        _issue(errors, "AUTOMATION_HOSTING_INVALID", "automation.hosting_profile",
               "размещение «%s» неизвестно — допустимо: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))),
               "hosting_profile %r is unknown — allowed: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))))

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

    # 5.1. Права коннекторов (A4). Корпоративный клиент проходит ИБ-проверку по паспорту,
    # не читая наш код: что за доступ, что именно разрешено, идут ли через него ПДн и где секрет.
    for i, it in enumerate(comp.get("integrations") or []):
        base = "components.integrations[%d]" % i
        if not isinstance(it, dict):
            _issue(errors, "INTEGRATION_SHAPE", base,
                   "интеграция должна быть объектом с kind, scopes и personal_data",
                   "each integration must be an object with kind, scopes and personal_data")
            continue
        kind = str(it.get("kind") or "").strip()
        if not kind:
            _issue(errors, "INTEGRATION_KIND_REQUIRED", base + ".kind",
                   "не сказано, что это за внешняя система",
                   "the external system kind is missing")

        scopes = [s for s in (it.get("scopes") or []) if not is_blank(s)] \
            if isinstance(it.get("scopes"), list) else []
        if not scopes:
            _issue(errors, "INTEGRATION_SCOPES_REQUIRED", base + ".scopes",
                   "права коннектора «%s» не видны: перечисли, что именно ему разрешено "
                   "(например messages.read, messages.send). Без этого клиент не может пройти "
                   "проверку безопасности по паспорту" % (kind or "?"),
                   "connector %r has no visible rights: list what exactly it may do (e.g. "
                   "messages.read, messages.send). Without it the client cannot run a security "
                   "review from the passport" % (kind or "?"))

        pd = str(it.get("personal_data") or "").strip().lower()
        if not pd:
            _issue(errors, "INTEGRATION_PERSONAL_DATA_REQUIRED", base + ".personal_data",
                   "не объявлено, как коннектор «%s» обращается с персональными данными "
                   "(none | reads | stores). «Не сказано» — это не «не трогает»" % (kind or "?"),
                   "it is not declared how connector %r handles personal data (none | reads | "
                   "stores). «Not stated» does not mean «does not touch»" % (kind or "?"))
        elif pd not in PERSONAL_DATA_MODES:
            _issue(errors, "INTEGRATION_PERSONAL_DATA_INVALID", base + ".personal_data",
                   "режим персональных данных «%s» неизвестен — допустимо: %s"
                   % (pd, ", ".join(sorted(PERSONAL_DATA_MODES))),
                   "personal_data mode %r is unknown — allowed: %s"
                   % (pd, ", ".join(sorted(PERSONAL_DATA_MODES))))
        elif pd == "stores" and is_blank(it.get("retention")):
            _issue(errors, "INTEGRATION_RETENTION_REQUIRED", base + ".retention",
                   "коннектор «%s» ХРАНИТ персональные данные, но не сказано сколько — "
                   "срок хранения обязателен для договора об обработке" % (kind or "?"),
                   "connector %r STORES personal data but no retention is stated — the retention "
                   "period is required for the data-processing agreement" % (kind or "?"))

        # Запись наружу: подтверждает ли её человек — объявляется явно, оба ответа допустимы.
        if it.get("external_writes") is True and it.get("human_in_loop") is None:
            _issue(errors, "INTEGRATION_HUMAN_IN_LOOP_REQUIRED", base + ".human_in_loop",
                   "коннектор «%s» пишет наружу, но не объявлено, подтверждает ли запись человек. "
                   "Ответ «нет» допустим — умолчание нет" % (kind or "?"),
                   "connector %r writes externally but human_in_loop is not declared. «false» is a "
                   "valid answer — silence is not" % (kind or "?"))

        # Секрет в паспорте = утечка в git и в кабинет клиента.
        ref = str(it.get("secret_ref") or "").strip()
        if ref and ":" not in ref and SECRET_VALUE_RE.fullmatch(ref):
            _issue(errors, "INTEGRATION_SECRET_INLINE", base + ".secret_ref",
                   "в secret_ref похоже лежит сам секрет, а не ссылка на него. Пиши, ГДЕ он "
                   "хранится (например «config.json:greenapi_token»)",
                   "secret_ref looks like the secret itself rather than a reference. State WHERE "
                   "it is stored (e.g. «config.json:greenapi_token»)")
        if not ref and scopes:
            _warn(warns, "INTEGRATION_SECRET_REF_EMPTY", base + ".secret_ref",
                  "не сказано, где лежит секрет коннектора «%s» — при передаче клиенту его "
                  "негде искать" % (kind or "?"),
                  "the location of connector %r secret is not stated — nobody can find it during "
                  "hand-over to the client" % (kind or "?"))

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
        "version": "1.0.0", "languages": ["ru", "en"], "hosting_profile": "local",
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
        "integrations": [{"kind": "whatsapp", "account": "GreenAPI instance 1101…",
                          "scopes": ["messages.read", "messages.send"], "external_writes": True,
                          "human_in_loop": True, "personal_data": "reads",
                          "secret_ref": "config.json:greenapi_token"}],
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
        "hosting_profile": "облако",
        "service": {"port": 8767, "health": "", "state": ""},
        "limits": [], "help_surface": "",
    },
    "components": {
        "platform_agents": [
            {"platform_agent_id": "по имени", "role": "", "provider_expected": "custom"},
        ],
        "schedules": [{"id": "nightly", "kind": "cron"}],
        "integrations": [
            {"kind": "email", "external_writes": True},                    # нет прав, нет ПДн, нет человека
            {"kind": "crm", "scopes": ["contacts.read"], "personal_data": "stores"},   # хранит, но нет срока
            {"kind": "sheets", "scopes": ["rows.write"], "personal_data": "нет",
             "secret_ref": "ya29AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"},    # режим неизвестен + секрет внутри
        ],
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
    ("размещение неизвестно", "AUTOMATION_HOSTING_INVALID"),
    ("права коннектора не видны", "INTEGRATION_SCOPES_REQUIRED"),
    ("не объявлены персональные данные", "INTEGRATION_PERSONAL_DATA_REQUIRED"),
    ("режим персональных данных неизвестен", "INTEGRATION_PERSONAL_DATA_INVALID"),
    ("хранит ПДн без срока хранения", "INTEGRATION_RETENTION_REQUIRED"),
    ("пишет наружу без ответа про человека", "INTEGRATION_HUMAN_IN_LOOP_REQUIRED"),
    ("секрет лежит прямо в паспорте", "INTEGRATION_SECRET_INLINE"),
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
    # Молчание — не ответ: отсутствующее поле обязано ловиться отдельно от неверного значения.
    for field, code, label in (
        ("hosting_profile", "AUTOMATION_HOSTING_REQUIRED", "размещение не указано вовсе"),
    ):
        miss = json.loads(json.dumps(GOOD))
        miss["automation"].pop(field, None)
        if any(e["code"] == code for e in check_report(miss)["errors"]):
            print("PASS: %s — поймано" % label)
        else:
            ok = False
            print("FAIL: %s — НЕ поймано (%s)" % (label, code))

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
