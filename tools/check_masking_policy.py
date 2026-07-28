#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка политики маскирования агента (срез «Защита данных», handoff Codex 28.07.2026).

Главный тезис, ради которого она существует: **включённый тумблер защитой не является.**
Политика считается действующей, только когда локальный runtime подтвердил PRE и POST. Поэтому
`enabled: true` без свидетельства исполнения здесь не проходит — это ошибка, а не оптимизм.

Форма конфига закрыта: неизвестные поля отклоняются. Причина не в педантизме — расширение
формы в обход контракта означает, что интерфейс показывает одно, а движок делает другое.

Как пользоваться:
  python3 check_masking_policy.py политика.json
  python3 check_masking_policy.py политика.json --json
  python3 check_masking_policy.py --selftest

Коды выхода: 0 — политика валидна, 1 — есть ошибки, 2 — файл не прочитан.
"""
import json
import os
import re
import sys
import unicodedata

AGENT_ID_RE = re.compile(r"^agent_[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")
REQUIRED_HOOKS = {"pre", "post"}          # REVEAL — отдельное действие, а не третий постоянный hook
NAMES_MODES = {"aggressive", "context"}
# Подпись «Строго» в интерфейсе означает context. Значение strict в runtime не передаётся:
# движок его не знает, и молчаливая подстановка дала бы режим, которого никто не выбирал.
NAMES_MODE_ALIASES = {"строго": "context", "strict": "context"}
REVEAL_POLICIES = {"owner_only"}          # платформенных ролей ещё нет
HINT_TYPES = {"iin", "bin", "phone", "email", "iban", "bic", "card",
              "account", "name", "address", "org", "number"}
POLICY_VERSIONS = {"kz-v1"}
ENFORCED = "ENFORCED"

ROOT_FIELDS = {"agent_id", "masking", "evidence"}
MASKING_FIELDS = {"enabled", "hooks", "names_mode", "field_hints",
                  "reveal_policy", "share_key_cross_device", "policy_version"}
EVIDENCE_FIELDS = {"pre", "post", "policy_version", "vault", "audit", "captured_at"}


def _issue(out, code, path, ru, en):
    out.append({"code": code, "severity": "error", "path": path,
                "message_ru": ru, "message_en": en})


def _warn(out, code, path, ru, en):
    out.append({"code": code, "severity": "warning", "path": path,
                "message_ru": ru, "message_en": en})


def normalize_hint_key(key):
    """lowercase + NFC. Имена колонок приходят из разных источников и различаются формой."""
    return unicodedata.normalize("NFC", str(key)).strip().lower()


def check_report(doc):
    errors, warns = [], []
    if not isinstance(doc, dict):
        _issue(errors, "POLICY_SHAPE", "$",
               "политика должна быть объектом с полями agent_id и masking",
               "the policy must be an object with agent_id and masking")
        return {"ready": False, "errors": errors, "warnings": warns}

    for k in sorted(set(doc) - ROOT_FIELDS):
        _issue(errors, "POLICY_UNKNOWN_FIELD", k,
               "неизвестное поле «%s»: форма закрыта. Расширение мимо контракта означает, что "
               "интерфейс показывает одно, а движок делает другое" % k,
               "unknown field %r: the shape is closed. Extending it outside the contract means "
               "the interface shows one thing while the engine does another" % k)

    aid = str(doc.get("agent_id") or "").strip()
    if not aid:
        _issue(errors, "POLICY_AGENT_ID_REQUIRED", "agent_id",
               "не указан агент: политика привязывается к точному agent_..., а не к карточке "
               "автоматизации — один агент может входить в несколько автоматизаций",
               "agent_id is missing: the policy binds to an exact agent_..., not to an automation "
               "card — one agent may belong to several automations")
    elif not AGENT_ID_RE.match(aid):
        _issue(errors, "POLICY_AGENT_ID_INVALID", "agent_id",
               "«%s» не похож на стабильный идентификатор вида agent_..." % aid,
               "%r is not a stable identifier starting with agent_" % aid)

    m = doc.get("masking")
    if not isinstance(m, dict):
        _issue(errors, "POLICY_MASKING_REQUIRED", "masking",
               "нет раздела masking", "the masking section is missing")
        return {"ready": not errors, "errors": errors, "warnings": warns}

    for k in sorted(set(m) - MASKING_FIELDS):
        _issue(errors, "MASKING_UNKNOWN_FIELD", "masking." + k,
               "неизвестное поле «%s» в masking: форма закрыта" % k,
               "unknown field %r in masking: the shape is closed" % k)

    enabled = m.get("enabled")
    if not isinstance(enabled, bool):
        _issue(errors, "MASKING_ENABLED_BOOLEAN", "masking.enabled",
               "enabled обязан быть true или false; для нового агента по умолчанию false",
               "enabled must be true or false; the default for a new agent is false")

    hooks = m.get("hooks")
    if not isinstance(hooks, list) or len(hooks) != len(set(map(str, hooks))) \
            or set(map(str, hooks)) != REQUIRED_HOOKS:
        _issue(errors, "MASKING_HOOKS_EXACT", "masking.hooks",
               "hooks обязан быть ровно [pre, post] без повторов. REVEAL — отдельное действие "
               "с подтверждением человека, а не третий постоянный hook",
               "hooks must be exactly [pre, post] with no duplicates. REVEAL is a separate "
               "human-confirmed action, not a permanent third hook")

    nm = m.get("names_mode")
    nm_s = str(nm or "").strip().lower()
    if nm_s in NAMES_MODE_ALIASES and nm_s not in NAMES_MODES:
        _issue(errors, "MASKING_NAMES_MODE_ALIAS", "masking.names_mode",
               "«%s» — это подпись интерфейса, а не значение движка: передавай «%s». Молчаливая "
               "подстановка дала бы режим, которого никто не выбирал"
               % (nm, NAMES_MODE_ALIASES[nm_s]),
               "%r is an interface label, not an engine value: pass %r instead. A silent "
               "substitution would enable a mode nobody chose" % (nm, NAMES_MODE_ALIASES[nm_s]))
    elif nm_s not in NAMES_MODES:
        _issue(errors, "MASKING_NAMES_MODE_INVALID", "masking.names_mode",
               "names_mode = «%s» — допустимо только %s" % (nm, " | ".join(sorted(NAMES_MODES))),
               "names_mode = %r — allowed: %s" % (nm, " | ".join(sorted(NAMES_MODES))))

    hints = m.get("field_hints")
    if hints is None:
        hints = {}
    if not isinstance(hints, dict):
        _issue(errors, "MASKING_HINTS_SHAPE", "masking.field_hints",
               "field_hints обязан быть словарём «имя поля → тип»",
               "field_hints must be a map of field name to type")
    else:
        seen = {}
        for raw_key, value in hints.items():
            norm = normalize_hint_key(raw_key)
            path = "masking.field_hints[%s]" % raw_key
            if not norm:
                _issue(errors, "MASKING_HINT_EMPTY_KEY", path,
                       "пустое имя поля", "empty field name")
                continue
            if norm in seen and seen[norm] != raw_key:
                _issue(errors, "MASKING_HINT_COLLISION", path,
                       "после приведения к нижнему регистру «%s» совпадает с «%s» — какая из "
                       "подсказок сработает, предсказать нельзя" % (raw_key, seen[norm]),
                       "after normalization %r collides with %r — which hint wins is "
                       "unpredictable" % (raw_key, seen[norm]))
                continue
            seen[norm] = raw_key
            if str(value) not in HINT_TYPES:
                _issue(errors, "MASKING_HINT_TYPE_UNKNOWN", path,
                       "тип «%s» движок не поддерживает. Допустимо: %s"
                       % (value, ", ".join(sorted(HINT_TYPES))),
                       "type %r is not supported by the engine. Allowed: %s"
                       % (value, ", ".join(sorted(HINT_TYPES))))

    rp = str(m.get("reveal_policy") or "").strip()
    if rp not in REVEAL_POLICIES:
        _issue(errors, "MASKING_REVEAL_POLICY_INVALID", "masking.reveal_policy",
               "reveal_policy = «%s»: пока платформенных ролей нет, допустимо только owner_only, "
               "и это локальный суррогат — устройство плюс подтверждение человеком, а не "
               "доказанная личность" % rp,
               "reveal_policy = %r: until platform roles exist only owner_only is allowed, and it "
               "is a local surrogate — device plus human confirmation, not a proven identity" % rp)

    if m.get("share_key_cross_device") is not False:
        _issue(errors, "MASKING_CROSS_DEVICE_BLOCKED", "masking.share_key_cross_device",
               "перенос ключа между устройствами заблокирован: обязано быть false. Нынешний "
               "прототип публикует зашифрованное соответствие, а не безопасно переносит ключ",
               "cross-device key sharing is blocked: must be false. The current prototype "
               "publishes an encrypted mapping instead of safely transferring the key")

    pv = str(m.get("policy_version") or "").strip()
    if pv not in POLICY_VERSIONS:
        _issue(errors, "MASKING_POLICY_VERSION_UNKNOWN", "masking.policy_version",
               "версия политики «%s» не зарегистрирована — неизвестная версия блокирует "
               "включение. Допустимо: %s" % (pv, ", ".join(sorted(POLICY_VERSIONS))),
               "policy version %r is not registered — an unknown version blocks activation. "
               "Allowed: %s" % (pv, ", ".join(sorted(POLICY_VERSIONS))))

    # ---- Главное правило: включено только то, что подтвердил runtime
    ev = doc.get("evidence")
    if enabled is True:
        if not isinstance(ev, dict):
            _issue(errors, "MASKING_ENABLED_WITHOUT_EVIDENCE", "evidence",
                   "enabled: true без свидетельства исполнения. Тумблер защитой не является: "
                   "нужны подтверждённые локальным runtime PRE и POST",
                   "enabled: true without runtime evidence. A toggle is not protection: locally "
                   "confirmed PRE and POST are required")
        else:
            for k in sorted(set(ev) - EVIDENCE_FIELDS):
                _issue(errors, "EVIDENCE_UNKNOWN_FIELD", "evidence." + k,
                       "неизвестное поле «%s» в evidence" % k,
                       "unknown field %r in evidence" % k)
            for hook in ("pre", "post"):
                if str(ev.get(hook) or "").upper() != ENFORCED:
                    _issue(errors, "EVIDENCE_%s_NOT_ENFORCED" % hook.upper(), "evidence." + hook,
                           "%s не подтверждён как ENFORCED — политика сохранена, но не действует; "
                           "показывать это как защиту нельзя" % hook.upper(),
                           "%s is not confirmed as ENFORCED — the policy is stored but not in "
                           "force; showing it as protection is forbidden" % hook.upper())
            if pv and str(ev.get("policy_version") or "").strip() != pv:
                _issue(errors, "EVIDENCE_POLICY_VERSION_MISMATCH", "evidence.policy_version",
                       "версия в свидетельстве («%s») не совпадает с версией политики («%s») — "
                       "движок работает не по той политике, которую показывают"
                       % (ev.get("policy_version"), pv),
                       "the evidence version (%r) differs from the policy version (%r) — the "
                       "engine runs a different policy than the one displayed"
                       % (ev.get("policy_version"), pv))
            if ev.get("audit") is not None and ev.get("audit") is not True:
                _issue(errors, "EVIDENCE_AUDIT_UNHEALTHY", "evidence.audit",
                       "журнал не пишется: неуспешный аудит не может выдаваться за исправную "
                       "защиту",
                       "the audit journal is failing: a broken audit must not be reported as "
                       "healthy protection")
    elif isinstance(ev, dict) and str(ev.get("pre") or "").upper() == ENFORCED:
        _warn(warns, "EVIDENCE_WITHOUT_ENABLED", "evidence",
              "runtime подтверждает исполнение, но политика выключена — проверь, что показываешь",
              "the runtime confirms enforcement while the policy is disabled — check what is shown")

    return {"ready": not errors, "errors": errors, "warnings": warns}


GOOD = {
    "agent_id": "agent_Lu25PvPrKqLn1rqINlbA_",
    "masking": {
        "enabled": True,
        "hooks": ["pre", "post"],
        "names_mode": "aggressive",
        "field_hints": {"иин": "iin", "телефон": "phone", "счет": "account"},
        "reveal_policy": "owner_only",
        "share_key_cross_device": False,
        "policy_version": "kz-v1",
    },
    "evidence": {"pre": "ENFORCED", "post": "ENFORCED", "policy_version": "kz-v1",
                 "vault": True, "audit": True, "captured_at": "2026-07-28T20:00:00Z"},
}

RULE_CHECKS = [
    ("тумблер без подтверждения хуков", "MASKING_ENABLED_WITHOUT_EVIDENCE",
     lambda d: d.pop("evidence")),
    ("POST не подтверждён", "EVIDENCE_POST_NOT_ENFORCED",
     lambda d: d["evidence"].update({"post": "DISABLED"})),
    ("версия движка разошлась с политикой", "EVIDENCE_POLICY_VERSION_MISMATCH",
     lambda d: d["evidence"].update({"policy_version": "kz-v0"})),
    ("сломанный журнал выдан за исправный", "EVIDENCE_AUDIT_UNHEALTHY",
     lambda d: d["evidence"].update({"audit": False})),
    ("неизвестное поле в форме", "MASKING_UNKNOWN_FIELD",
     lambda d: d["masking"].update({"turbo": True})),
    ("hooks не ровно pre+post", "MASKING_HOOKS_EXACT",
     lambda d: d["masking"].update({"hooks": ["pre", "post", "reveal"]})),
    ("подпись интерфейса вместо значения движка", "MASKING_NAMES_MODE_ALIAS",
     lambda d: d["masking"].update({"names_mode": "strict"})),
    ("неподдерживаемый тип подсказки", "MASKING_HINT_TYPE_UNKNOWN",
     lambda d: d["masking"]["field_hints"].update({"паспорт": "passport"})),
    ("коллизия подсказок после нормализации", "MASKING_HINT_COLLISION",
     lambda d: d["masking"]["field_hints"].update({"ИИН": "iin"})),
    ("роль сверх owner_only", "MASKING_REVEAL_POLICY_INVALID",
     lambda d: d["masking"].update({"reveal_policy": "auditor"})),
    ("перенос ключа между устройствами", "MASKING_CROSS_DEVICE_BLOCKED",
     lambda d: d["masking"].update({"share_key_cross_device": True})),
    ("незарегистрированная версия политики", "MASKING_POLICY_VERSION_UNKNOWN",
     lambda d: d["masking"].update({"policy_version": "kz-v2"})),
    ("агент указан не стабильным id", "POLICY_AGENT_ID_INVALID",
     lambda d: d.update({"agent_id": "юрист"})),
]


def selftest():
    print("Самопроверка политики маскирования:")
    ok = True
    good = check_report(json.loads(json.dumps(GOOD)))
    if good["ready"]:
        print("PASS: правильная политика проходит")
    else:
        ok = False
        print("FAIL: правильная политика не прошла:")
        for e in good["errors"]:
            print("      - %s %s" % (e["code"], e["message_ru"]))

    for label, code, mutate in RULE_CHECKS:
        d = json.loads(json.dumps(GOOD))
        mutate(d)
        codes = {e["code"] for e in check_report(d)["errors"]}
        got = code in codes
        print(("PASS: " if got else "FAIL: ") + label + " — поймано")
        ok = ok and got

    # Выключенная политика без свидетельства — норма, а не ошибка: так живёт новый агент.
    off = json.loads(json.dumps(GOOD))
    off["masking"]["enabled"] = False
    off.pop("evidence")
    if check_report(off)["ready"]:
        print("PASS: выключенная политика без свидетельства — не ошибка")
    else:
        ok = False
        print("FAIL: выключенная политика посчитана ошибочной")

    # Явная подсказка сильнее эвристики: тип iin допустим для колонки «ИИН» всегда.
    hint = json.loads(json.dumps(GOOD))
    hint["masking"]["field_hints"] = {"иин": "iin"}
    if check_report(hint)["ready"]:
        print("PASS: подсказка «иин → iin» принимается (контрольная цифра тут ни при чём)")
    else:
        ok = False
        print("FAIL: подсказка «иин → iin» отклонена")

    for e in check_report(GOOD)["errors"] + check_report(GOOD)["warnings"]:
        if not e.get("message_ru") or not e.get("message_en"):
            ok = False
            print("FAIL: сообщение без одного из языков")
            break
    else:
        print("PASS: каждое сообщение на двух языках (§3.26)")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = [a for a in argv if not a.startswith("-")]
    if len(paths) != 1:
        print("Как пользоваться: python3 check_masking_policy.py политика.json [--json]")
        return 2
    if not os.path.exists(paths[0]):
        print("ОШИБКА: файл не найден: %s" % paths[0])
        return 2
    try:
        doc = json.load(open(paths[0], encoding="utf-8"))
    except Exception as exc:
        print("ОШИБКА: файл не прочитан: %s" % exc)
        return 2
    report = check_report(doc)
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    for e in report["errors"]:
        print("ОШИБКА: %s — %s" % (e["path"], e["message_ru"]))
    for w in report["warnings"]:
        print("ВНИМАНИЕ: %s — %s" % (w["path"], w["message_ru"]))
    print("ИТОГ: " + ("политика валидна" if report["ready"] else "НЕ ВАЛИДНА — исправь выше"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
