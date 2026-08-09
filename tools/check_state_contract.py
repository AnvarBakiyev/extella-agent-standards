#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка КОНТРАКТА СОСТОЯНИЯ автоматизации Extella (ответ `/api/state`).

Зачем: паспорт объявляет, ГДЕ спрашивать состояние (`service.state`), но до сих пор ничто
не проверяло, ЧТО служба отвечает. Console показывала «порт отвечает» как «работает» ровно
потому, что ответ никто не валидировал.

Что нового в этой версии — блок `bound_to` (пункт A2). Клиент, купивший автоматизацию,
обязан видеть не «работает», а «работает, сервер такой-то, аккаунт такой-то, версия такая-то».
Без этого выдача платному клиенту бессмысленна: он не отличит свой контур от чужого.

Правило честности то же, что во всём продукте: **неизвестное значение — `null`, а не
правдоподобная подстановка**. Проверялка требует, чтобы поле ПРИСУТСТВОВАЛО. `null`
допустим только там, где его явно разрешает схема `extella.automation_state.v1`; в частности,
`enabled` всегда является boolean-фактом.

Как пользоваться:
  python3 check_state_contract.py ответ.json
  python3 check_state_contract.py http://127.0.0.1:8766/api/state     # живая служба
  python3 check_state_contract.py ответ.json --json
  python3 check_state_contract.py --selftest

Коды выхода: 0 — контракт соблюдён, 1 — есть ошибки, 2 — ответ не прочитан.
"""
import json
import math
import os
import re
import sys
from datetime import datetime

# Поля верхнего уровня присутствуют всегда; допустимость null задаётся правилом каждого поля.
REQUIRED_STATE_FIELDS = ("enabled", "active_version", "last_run", "last_result",
                         "last_error", "schedules", "checked_at", "bound_to")
HOSTING_PROFILES = {"local", "server", "client_server"}
LAST_RESULTS = {"ok", "failed", "partial"}
# bound_to: что именно клиент обязан увидеть про свою привязку.
REQUIRED_BOUND_FIELDS = ("hosting_profile", "host", "platform_profile_id",
                         "account_ref", "agent_ids", "since")
# Отпечаток аккаунта — короткий необратимый хвост, по которому видно «тот же/другой аккаунт».
# Сам токен в состоянии не появляется никогда: состояние отдаётся клиенту.
ACCOUNT_REF_RE = re.compile(r"^[0-9a-f]{8,32}$")
# Похоже на живой секрет: длинная непрерывная строка из «токенных» символов.
SECRET_LIKE_RE = re.compile(r"^[A-Za-z0-9_\-]{24,}$")
AGENT_ID_RE = re.compile(r"^agent_[A-Za-z0-9_\-]{6,64}$")
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?"
    r"(?:Z|[+-]\d{2}:\d{2})?$"
)
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def _issue(errors, code, path, ru, en):
    errors.append({"code": code, "severity": "error", "path": path,
                   "message_ru": ru, "message_en": en})


def _warn(warns, code, path, ru, en):
    warns.append({"code": code, "severity": "warning", "path": path,
                  "message_ru": ru, "message_en": en})


def _is_number(value):
    """JSON number, but never bool (bool is a subclass of int in Python)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _is_iso_timestamp(value):
    """The exact timestamp syntax used by Console, plus a real calendar-date check."""
    if (not isinstance(value, str) or value != value.strip()
            or len(value) > 160 or not ISO_RE.fullmatch(value)):
        return False
    try:
        # Keep compatibility with Python versions whose fromisoformat does not accept Z.
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return True


def _is_semver(value):
    """SemVer 2.0.0, aligned with the Console parser (including prerelease/build)."""
    if not isinstance(value, str) or value != value.strip():
        return False
    match = SEMVER_RE.fullmatch(value)
    if not match:
        return False
    for identifier in (match.group(4) or "").split("."):
        if identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"):
            return False
    return True


def _is_nonblank_string(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _is_timestamp(value):
    return _is_number(value) or _is_iso_timestamp(value)


def _check_last_run(value, errors):
    if value is None or _is_timestamp(value):
        return
    if isinstance(value, dict):
        # Console gives `at` precedence when both keys exist. Invalid `at` therefore cannot be
        # hidden behind a valid `ts` fallback.
        key = "at" if "at" in value else "ts" if "ts" in value else None
        if key and _is_timestamp(value.get(key)):
            return
        path = "last_run." + key if key else "last_run"
        _issue(errors, "STATE_LAST_RUN_INVALID", path,
               "last_run-объект обязан содержать корректную ISO 8601/числовую метку at или ts",
               "a last_run object must contain a valid ISO 8601/numeric at or ts timestamp")
        return
    _issue(errors, "STATE_LAST_RUN_INVALID", "last_run",
           "last_run обязан быть ISO 8601 строкой, конечным числом, объектом с at/ts или null",
           "last_run must be an ISO 8601 string, finite number, object with at/ts, or null")


def _check_last_error(value, errors):
    if value is None:
        return
    if not isinstance(value, dict):
        _issue(errors, "STATE_ERROR_SHAPE", "last_error",
               "last_error обязан быть объектом {code, message_ru, message_en} или null",
               "last_error must be an object {code, message_ru, message_en} or null")
        return
    for field in ("code", "message_ru", "message_en"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            _issue(errors, "STATE_ERROR_%s_REQUIRED" % field.upper(),
                   "last_error." + field,
                   "у ошибки нет строкового «%s» — ошибка обязана быть с кодом и на двух "
                   "языках (§3.26)" % field,
                   "the error has no string «%s» — errors ship with a code and in both "
                   "languages (§3.26)" % field)


def _check_schedules(value, errors):
    if not isinstance(value, list):
        _issue(errors, "STATE_SCHEDULES_SHAPE", "schedules",
               "schedules обязан быть массивом", "schedules must be an array")
        return
    for index, schedule in enumerate(value):
        base = "schedules[%d]" % index
        if not isinstance(schedule, dict):
            _issue(errors, "STATE_SCHEDULE_SHAPE", base,
                   "расписание обязано быть объектом",
                   "each schedule must be an object")
            continue
        if not _is_nonblank_string(schedule.get("id")):
            _issue(errors, "STATE_SCHEDULE_ID_REQUIRED", base + ".id",
                   "у расписания нет стабильного строкового id",
                   "the schedule has no stable string id")
        if not isinstance(schedule.get("active"), bool):
            _issue(errors, "STATE_SCHEDULE_ACTIVE_REQUIRED", base + ".active",
                   "active обязан быть boolean-фактом",
                   "active must be a boolean fact")
        if "next_run" not in schedule:
            _issue(errors, "STATE_SCHEDULE_NEXT_RUN_REQUIRED", base + ".next_run",
                   "next_run обязан присутствовать; неизвестное значение передаётся как null",
                   "next_run must be present; an unknown value is represented as null")
        else:
            next_run = schedule.get("next_run")
            valid_string = isinstance(next_run, str) and bool(next_run.strip())
            if next_run is not None and not _is_number(next_run) and not valid_string:
                _issue(errors, "STATE_SCHEDULE_NEXT_RUN_INVALID", base + ".next_run",
                       "next_run обязан быть непустой строкой, конечным числом или null",
                       "next_run must be a non-empty string, finite number, or null")


def _check_bound_to(bound, errors, warns):
    """Блок привязки (A2). Присутствие полей обязательно, null внутри — честный ответ."""
    if bound is None:
        _issue(errors, "BOUND_TO_NULL", "bound_to",
               "блок привязки пуст: клиент не увидит, к какому серверу и аккаунту подключена "
               "его автоматизация. Даже когда фактов нет, блок обязан быть с null внутри",
               "the binding block is null: the client cannot see which server and account the "
               "automation is bound to. Even with no facts the block must exist with nulls inside")
        return
    if not isinstance(bound, dict):
        _issue(errors, "BOUND_TO_SHAPE", "bound_to",
               "bound_to обязан быть объектом", "bound_to must be an object")
        return

    for field in REQUIRED_BOUND_FIELDS:
        if field not in bound:
            _issue(errors, "BOUND_TO_%s_MISSING" % field.upper(), "bound_to." + field,
                   "в привязке нет поля «%s» — отсутствие поля и честное «неизвестно» это разные "
                   "вещи: пиши null" % field,
                   "the binding has no «%s» field — a missing field and an honest «unknown» are "
                   "different things: write null" % field)

    hosting = bound.get("hosting_profile")
    if hosting is not None and (
            not isinstance(hosting, str) or hosting not in HOSTING_PROFILES):
        _issue(errors, "BOUND_TO_HOSTING_INVALID", "bound_to.hosting_profile",
               "размещение «%s» неизвестно — допустимо: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))),
               "hosting_profile %r is unknown — allowed: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))))

    for field in ("host", "platform_profile_id"):
        value = bound.get(field)
        if value is not None and not _is_nonblank_string(value):
            _issue(errors, "BOUND_TO_%s_INVALID" % field.upper(), "bound_to." + field,
                   "«%s» обязан быть непустой строкой или null" % field,
                   "«%s» must be a non-empty string or null" % field)

    ref = bound.get("account_ref")
    if ref is not None and (
            not isinstance(ref, str) or not ACCOUNT_REF_RE.fullmatch(ref)):
        _issue(errors, "BOUND_TO_ACCOUNT_REF_INVALID", "bound_to.account_ref",
               "account_ref обязан быть коротким необратимым отпечатком аккаунта (8–32 hex), "
               "а не токеном и не адресом почты — состояние отдаётся клиенту",
               "account_ref must be a short irreversible account fingerprint (8–32 hex), not a "
               "token and not an e-mail — the state is served to the client")

    # Секрет в состоянии — утечка клиенту. Проверяем весь блок, а не одно поле.
    for key, value in bound.items():
        if isinstance(value, str) and key != "account_ref" and SECRET_LIKE_RE.match(value):
            _issue(errors, "BOUND_TO_SECRET_LEAK", "bound_to." + key,
                   "в поле «%s» лежит строка, похожая на живой секрет. Состояние видит клиент — "
                   "секретам тут не место" % key,
                   "field %r holds a string that looks like a live secret. The state is visible to "
                   "the client — secrets do not belong here" % key)

    agent_ids = bound.get("agent_ids")
    if agent_ids is not None:
        if not isinstance(agent_ids, list):
            _issue(errors, "BOUND_TO_AGENT_IDS_SHAPE", "bound_to.agent_ids",
                   "agent_ids обязан быть списком стабильных id",
                   "agent_ids must be a list of stable ids")
        elif not agent_ids:
            _warn(warns, "BOUND_TO_AGENT_IDS_EMPTY", "bound_to.agent_ids",
                  "список агентов пуст — клиент не увидит, чей мозг работает в его автоматизации",
                  "the agent list is empty — the client cannot see which agent runs the automation")
        else:
            seen = set()
            for index, agent_id in enumerate(agent_ids):
                path = "bound_to.agent_ids[%d]" % index
                if not isinstance(agent_id, str) or not AGENT_ID_RE.fullmatch(agent_id):
                    _issue(errors, "BOUND_TO_AGENT_ID_INVALID", path,
                           "agent_ids содержит не стабильный platform agent id вида agent_...",
                           "agent_ids contains a value that is not a stable agent_... platform id")
                elif agent_id in seen:
                    _issue(errors, "BOUND_TO_AGENT_ID_DUPLICATE", path,
                           "один platform agent id указан в привязке дважды",
                           "the same platform agent id appears in the binding twice")
                else:
                    seen.add(agent_id)

    since = bound.get("since")
    if since is not None and not _is_iso_timestamp(since):
        _issue(errors, "BOUND_TO_SINCE_FORMAT", "bound_to.since",
               "дата привязки не в формате ISO 8601 — Console не сможет её сравнить",
               "the binding date is not ISO 8601 — the Console cannot compare it")


def check_report(doc):
    """Единый структурированный отчёт: {ready, errors, warnings}."""
    errors, warns = [], []
    if not isinstance(doc, dict):
        _issue(errors, "STATE_SHAPE", "",
               "ответ /api/state обязан быть объектом", "the /api/state response must be an object")
        return {"ready": False, "errors": errors, "warnings": warns}

    for field in REQUIRED_STATE_FIELDS:
        if field not in doc:
            _issue(errors, "STATE_%s_MISSING" % field.upper(), field,
                   "в состоянии нет поля «%s» — Console обязана различать «неизвестно» и «нет», "
                   "поэтому поле обязано быть, пусть и с null" % field,
                   "the state has no «%s» field — the Console must tell «unknown» from «none», so "
                   "the field must exist even when null" % field)

    if "enabled" in doc and not isinstance(doc.get("enabled"), bool):
        _issue(errors, "STATE_ENABLED_TYPE", "enabled",
               "enabled обязан быть boolean-фактом true/false",
               "enabled must be a true/false boolean fact")

    if "active_version" in doc:
        version = doc.get("active_version")
        if version is not None and not _is_semver(version):
            _issue(errors, "STATE_ACTIVE_VERSION_INVALID", "active_version",
                   "active_version обязан быть SemVer 2.0.0 строкой или null",
                   "active_version must be a SemVer 2.0.0 string or null")

    if "last_run" in doc:
        _check_last_run(doc.get("last_run"), errors)

    if "last_result" in doc:
        result = doc.get("last_result")
        if result is not None and (
                not isinstance(result, str) or result not in LAST_RESULTS):
            _issue(errors, "STATE_LAST_RESULT_INVALID", "last_result",
                   "last_result обязан быть ok, failed, partial или null",
                   "last_result must be ok, failed, partial, or null")

    if "last_error" in doc:
        _check_last_error(doc.get("last_error"), errors)

    if "schedules" in doc:
        _check_schedules(doc.get("schedules"), errors)

    if "bound_to" in doc:
        _check_bound_to(doc.get("bound_to"), errors, warns)

    if "checked_at" in doc:
        checked = doc.get("checked_at")
        if checked is not None and not _is_iso_timestamp(checked):
            _issue(errors, "STATE_CHECKED_AT_FORMAT", "checked_at",
                   "checked_at не в формате ISO 8601 или не null",
                   "checked_at is neither an ISO 8601 timestamp nor null")

    return {"ready": not errors, "errors": errors, "warnings": warns}


GOOD = {
    "enabled": True,
    "active_version": "1.0.0",
    "last_run": {"at": "2026-07-28T09:14:00Z", "kind": "campaign"},
    "last_result": "ok",
    "last_error": None,
    "schedules": [{"id": "campaigns_birthday", "active": True,
                   "next_run": "2026-07-29T09:00:00Z"}],
    "checked_at": "2026-07-28T09:20:00Z",
    "bound_to": {
        "hosting_profile": "local",
        "host": "127.0.0.1:8766",
        "platform_profile_id": "default",
        "account_ref": "3f9a1c04",
        "agent_ids": ["agent_eUSuv3enLqKkZd2lj0aeI"],  # canon-ok: фикстура самопроверки контракта
        "since": "2026-07-09T12:00:00Z",
    },
}

BAD = {
    "enabled": True,
    "active_version": "1.0.0",
    "last_run": None,
    "last_result": None,
    "last_error": {"code": "no_tourvisor", "message_ru": "нет ключа"},   # нет английского
    "schedules": [],
    # checked_at отсутствует целиком
    "bound_to": {
        "hosting_profile": "облако",                       # неизвестное размещение
        "host": "127.0.0.1:8766",
        "account_ref": "abakiyev@gmail.com",               # не отпечаток
        "api_token": "sk1234567890abcdefghijklmnop",       # утечка секрета клиенту
        # platform_profile_id, agent_ids, since отсутствуют
    },
}

RULE_CHECKS = [
    ("нет checked_at", "STATE_CHECKED_AT_MISSING"),
    ("ошибка без английского", "STATE_ERROR_MESSAGE_EN_REQUIRED"),
    ("размещение неизвестно", "BOUND_TO_HOSTING_INVALID"),
    ("account_ref не отпечаток", "BOUND_TO_ACCOUNT_REF_INVALID"),
    ("секрет утёк в состояние", "BOUND_TO_SECRET_LEAK"),
    ("нет профиля платформы", "BOUND_TO_PLATFORM_PROFILE_ID_MISSING"),
    ("нет списка агентов", "BOUND_TO_AGENT_IDS_MISSING"),
    ("нет даты привязки", "BOUND_TO_SINCE_MISSING"),
]

# Regression fixture for the exact hole this revision closes. Before strict validation every
# value below passed because only top-level field presence was checked.
STRICT_BAD = {
    "enabled": "yes",
    "active_version": {},
    "last_run": {"garbage": 1},
    "last_result": "error",
    "last_error": {"code": 17, "message_ru": "ошибка", "message_en": "error"},
    "schedules": [{"id": "nightly", "active": "true"}],
    "checked_at": 1770000000,
    "bound_to": {
        "hosting_profile": "LOCAL",
        "host": 8766,
        "platform_profile_id": "",
        "account_ref": 12345678,
        "agent_ids": ["not-an-agent"],
        "since": 1770000000,
    },
}

STRICT_RULE_CHECKS = [
    ("enabled не boolean", "STATE_ENABLED_TYPE"),
    ("active_version не SemVer", "STATE_ACTIVE_VERSION_INVALID"),
    ("last_run без at/ts", "STATE_LAST_RUN_INVALID"),
    ("last_result вне enum", "STATE_LAST_RESULT_INVALID"),
    ("код last_error не строка", "STATE_ERROR_CODE_REQUIRED"),
    ("active расписания не boolean", "STATE_SCHEDULE_ACTIVE_REQUIRED"),
    ("у расписания нет next_run", "STATE_SCHEDULE_NEXT_RUN_REQUIRED"),
    ("hosting_profile не точный enum", "BOUND_TO_HOSTING_INVALID"),
    ("host не строка", "BOUND_TO_HOST_INVALID"),
    ("platform_profile_id пуст", "BOUND_TO_PLATFORM_PROFILE_ID_INVALID"),
    ("account_ref не hex-строка", "BOUND_TO_ACCOUNT_REF_INVALID"),
    ("agent_ids содержит не platform id", "BOUND_TO_AGENT_ID_INVALID"),
    ("since не ISO 8601", "BOUND_TO_SINCE_FORMAT"),
    ("checked_at не ISO 8601", "STATE_CHECKED_AT_FORMAT"),
]


def selftest():
    print("Самопроверка контракта состояния (включая привязку bound_to):")
    ok = True
    good = check_report(json.loads(json.dumps(GOOD)))
    if good["ready"]:
        print("PASS: правильное состояние проходит (ошибок 0)")
    else:
        ok = False
        print("FAIL: правильное состояние не прошло:")
        for e in good["errors"]:
            print("      - %s %s" % (e["code"], e["message_ru"]))

    bad_codes = {e["code"] for e in check_report(json.loads(json.dumps(BAD)))["errors"]}
    for label, code in RULE_CHECKS:
        if code in bad_codes:
            print("PASS: %s — поймано" % label)
        else:
            ok = False
            print("FAIL: %s — НЕ поймано (%s)" % (label, code))

    strict_codes = {
        e["code"] for e in check_report(json.loads(json.dumps(STRICT_BAD)))["errors"]
    }
    for label, code in STRICT_RULE_CHECKS:
        if code in strict_codes:
            print("PASS: %s — поймано" % label)
        else:
            ok = False
            print("FAIL: %s — НЕ поймано (%s)" % (label, code))

    # Главный случай A2: состояние без привязки вообще.
    no_bind = json.loads(json.dumps(GOOD))
    no_bind.pop("bound_to")
    if any(e["code"] == "STATE_BOUND_TO_MISSING" for e in check_report(no_bind)["errors"]):
        print("PASS: состояние без привязки — поймано")
    else:
        ok = False
        print("FAIL: состояние без привязки — НЕ поймано")

    # Честное «неизвестно» обязано проходить: null внутри блока — не ошибка.
    honest = json.loads(json.dumps(GOOD))
    honest["bound_to"] = {k: None for k in REQUIRED_BOUND_FIELDS}
    if check_report(honest)["ready"]:
        print("PASS: честное «неизвестно» (null в каждом поле) проходит")
    else:
        ok = False
        print("FAIL: честное «неизвестно» не прошло — правило подмены значений нарушено")

    # А вот пустой блок целиком — не честность, а умолчание.
    empty = json.loads(json.dumps(GOOD))
    empty["bound_to"] = None
    if any(e["code"] == "BOUND_TO_NULL" for e in check_report(empty)["errors"]):
        print("PASS: bound_to: null целиком — поймано")
    else:
        ok = False
        print("FAIL: bound_to: null целиком — НЕ поймано")

    bilingual_issues = (check_report(BAD)["errors"] + check_report(BAD)["warnings"]
                        + check_report(STRICT_BAD)["errors"]
                        + check_report(STRICT_BAD)["warnings"])
    for e in bilingual_issues:
        if not e.get("message_ru") or not e.get("message_en"):
            ok = False
            print("FAIL: сообщение без одного из языков: %s" % e["code"])
            break
    else:
        print("PASS: каждое сообщение на двух языках (§3.26)")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def _load(source):
    """Файл или живая служба — одинаково."""
    if source.startswith("http://") or source.startswith("https://"):
        import urllib.request
        with urllib.request.urlopen(source, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("-")]
    if len(paths) != 1:
        print("Как пользоваться:")
        print("  python3 check_state_contract.py ответ.json | http://127.0.0.1:8766/api/state [--json]")
        print("  python3 check_state_contract.py --selftest")
        return 2
    src = paths[0]
    if not src.startswith("http") and not os.path.exists(src):
        print("ОШИБКА: файл не найден: %s" % src)
        return 2
    try:
        doc = _load(src)
    except Exception as exc:
        print("ОШИБКА: состояние не прочитано: %s" % exc)
        return 2

    report = check_report(doc)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    for e in report["errors"]:
        print("ОШИБКА: %s — %s" % (e["path"], e["message_ru"]))
    for w in report["warnings"]:
        print("ВНИМАНИЕ: %s — %s" % (w["path"], w["message_ru"]))
    print("ИТОГ: " + ("КОНТРАКТ СОБЛЮДЁН" if report["ready"] else "НЕ СОБЛЮДЁН — исправь выше"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
