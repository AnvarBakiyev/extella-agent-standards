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
правдоподобная подстановка**. Проверялка требует, чтобы поле ПРИСУТСТВОВАЛО; `null` в нём —
допустимый и честный ответ, отсутствие поля — ошибка.

Как пользоваться:
  python3 check_state_contract.py ответ.json
  python3 check_state_contract.py http://127.0.0.1:8766/api/state     # живая служба
  python3 check_state_contract.py ответ.json --json
  python3 check_state_contract.py --selftest

Коды выхода: 0 — контракт соблюдён, 1 — есть ошибки, 2 — ответ не прочитан.
"""
import json
import os
import re
import sys

# Поля верхнего уровня: должны присутствовать всегда, значение может быть null.
REQUIRED_STATE_FIELDS = ("enabled", "active_version", "last_run", "last_result",
                         "last_error", "schedules", "checked_at", "bound_to")
HOSTING_PROFILES = {"local", "server", "client_server"}
# bound_to: что именно клиент обязан увидеть про свою привязку.
REQUIRED_BOUND_FIELDS = ("hosting_profile", "host", "platform_profile_id",
                         "account_ref", "agent_ids", "since")
# Отпечаток аккаунта — короткий необратимый хвост, по которому видно «тот же/другой аккаунт».
# Сам токен в состоянии не появляется никогда: состояние отдаётся клиенту.
ACCOUNT_REF_RE = re.compile(r"^[0-9a-f]{8,32}$")
# Похоже на живой секрет: длинная непрерывная строка из «токенных» символов.
SECRET_LIKE_RE = re.compile(r"^[A-Za-z0-9_\-]{24,}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _issue(errors, code, path, ru, en):
    errors.append({"code": code, "severity": "error", "path": path,
                   "message_ru": ru, "message_en": en})


def _warn(warns, code, path, ru, en):
    warns.append({"code": code, "severity": "warning", "path": path,
                  "message_ru": ru, "message_en": en})


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
    if hosting is not None and str(hosting).strip().lower() not in HOSTING_PROFILES:
        _issue(errors, "BOUND_TO_HOSTING_INVALID", "bound_to.hosting_profile",
               "размещение «%s» неизвестно — допустимо: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))),
               "hosting_profile %r is unknown — allowed: %s"
               % (hosting, ", ".join(sorted(HOSTING_PROFILES))))

    ref = bound.get("account_ref")
    if ref is not None:
        if not ACCOUNT_REF_RE.match(str(ref)):
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

    since = bound.get("since")
    if since is not None and not ISO_RE.match(str(since)):
        _warn(warns, "BOUND_TO_SINCE_FORMAT", "bound_to.since",
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

    err = doc.get("last_error")
    if isinstance(err, dict):
        for field in ("code", "message_ru", "message_en"):
            if not str(err.get(field) or "").strip():
                _issue(errors, "STATE_ERROR_%s_REQUIRED" % field.upper(), "last_error." + field,
                       "у ошибки нет «%s» — ошибка обязана быть с кодом и на двух языках (§3.26)"
                       % field,
                       "the error has no «%s» — errors ship with a code and in both languages "
                       "(§3.26)" % field)
    elif err is not None:
        _issue(errors, "STATE_ERROR_SHAPE", "last_error",
               "last_error обязан быть объектом {code, message_ru, message_en} или null",
               "last_error must be an object {code, message_ru, message_en} or null")

    if "bound_to" in doc:
        _check_bound_to(doc.get("bound_to"), errors, warns)

    checked = doc.get("checked_at")
    if checked is not None and not ISO_RE.match(str(checked)):
        _warn(warns, "STATE_CHECKED_AT_FORMAT", "checked_at",
              "checked_at не в формате ISO 8601", "checked_at is not ISO 8601")

    return {"ready": not errors, "errors": errors, "warnings": warns}


GOOD = {
    "enabled": True,
    "active_version": "1.0.0",
    "last_run": {"at": "2026-07-28T09:14:00Z", "kind": "campaign"},
    "last_result": "ok",
    "last_error": None,
    "schedules": [{"id": "campaigns_birthday", "active": True}],
    "checked_at": "2026-07-28T09:20:00Z",
    "bound_to": {
        "hosting_profile": "local",
        "host": "127.0.0.1:8766",
        "platform_profile_id": "default",
        "account_ref": "3f9a1c04",
        "agent_ids": ["agent_eUSuv3enLqKkZd2lj0aeI"],
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

    for e in check_report(BAD)["errors"] + check_report(BAD)["warnings"]:
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
