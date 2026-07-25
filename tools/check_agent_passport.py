#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка паспорта агента Extella.

Как пользоваться:
  python3 check_agent_passport.py путь/к/паспорту.yaml   (поддерживается и .json)
  python3 check_agent_passport.py --selftest             (самопроверка без файлов)

Коды выхода: 0 — паспорт готов, 1 — есть ошибки, 2 — файл не прочитан.
"""
import json
import os
import sys

AUTONOMY = {"A0", "A1", "A2", "A3", "A4"}
SIDE_EFFECTS = {"none", "local", "external", "physical"}
CONFIRMATION = {"never", "conditional", "always"}
IDEMPOTENCY = {"supported", "unsupported"}
BUDGET_FIELDS = ("max_duration_ms", "max_llm_tokens", "max_delegation_depth", "max_external_actions")


def is_blank(value):
    """Пустое значение: None или строка из одних пробелов."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def check(doc):
    """Проверяет паспорт, возвращает (список ошибок, список предупреждений)."""
    errors, warns = [], []
    agent = doc.get("agent") if isinstance(doc.get("agent"), dict) else {}
    caps = doc.get("capabilities") if isinstance(doc.get("capabilities"), list) else []
    ops = doc.get("operations") if isinstance(doc.get("operations"), dict) else {}

    # Правило 10: пустой шаблон — говорим честно и не сыплем десятком ошибок
    if is_blank(agent.get("name")) and all(is_blank(c.get("name")) for c in caps if isinstance(c, dict)):
        errors.append("паспорт не заполнен — это пустой шаблон; впиши имя агента, владельца, "
                      "бизнес-цель и хотя бы одну способность, потом запусти проверку снова")
        return errors, warns

    # Правило 1: обязательные поля агента
    for field, label in (("name", "имя агента"), ("owner", "владелец"),
                         ("business_goal", "бизнес-цель"), ("version", "версия")):
        if is_blank(agent.get(field)):
            errors.append("agent.%s (%s) — поле пустое, заполни его" % (field, label))

    # Правило 2: только Qwen
    profile = str(agent.get("model_profile") or "").lower()
    if "claude" in profile or "anthropic" in profile:
        errors.append("agent.model_profile = «%s»: клиентские агенты работают только на Qwen"
                      % agent.get("model_profile"))

    # Правила 3–7: способности
    if not caps:
        errors.append("в паспорте нет ни одной способности (capabilities) — нужна минимум одна")
    for i, cap in enumerate(caps, 1):
        if not isinstance(cap, dict):
            errors.append("способность №%d: это не набор полей — проверь отступы в файле" % i)
            continue
        tag = "способность №%d" % i + ("" if is_blank(cap.get("name")) else " «%s»" % cap.get("name"))
        if is_blank(cap.get("name")):
            errors.append(tag + ": не заполнено имя (name)")
        if is_blank(cap.get("version")):
            errors.append(tag + ": не заполнена версия (version)")
        for field, allowed, hint in (("autonomy", AUTONOMY, "A0..A4"),
                                     ("side_effects", SIDE_EFFECTS, "none | local | external | physical"),
                                     ("confirmation", CONFIRMATION, "never | conditional | always"),
                                     ("idempotency", IDEMPOTENCY, "supported | unsupported")):
            if cap.get(field) not in allowed:
                errors.append("%s: %s = «%s» — допустимо только %s" % (tag, field, cap.get(field), hint))
        se, conf = cap.get("side_effects"), cap.get("confirmation")
        if se == "physical" and conf != "always":
            errors.append(tag + ": физическое действие (side_effects=physical) обязано подтверждаться "
                                "человеком — поставь confirmation: always")
        if se == "external" and conf == "never":
            errors.append(tag + ": внешнее действие (side_effects=external) нельзя выполнять "
                                "совсем без подтверждения — confirmation: never запрещён")
        if se in ("local", "external", "physical"):
            if is_blank(cap.get("rollback")):
                errors.append(tag + ": есть побочные эффекты, но не описан путь отката (rollback)")
            if is_blank(cap.get("evidence_schema")):
                errors.append(tag + ": есть побочные эффекты, но не описано доказательство "
                                    "исполнения (evidence_schema)")
        if cap.get("global") is True:
            if is_blank(cap.get("rollback")):
                errors.append(tag + ": global=true требует заполненного пути отката (rollback)")
            if not (cap.get("permissions") or cap.get("rules")):
                errors.append(tag + ": глобальный объект без владения запрещён — при global=true "
                                    "заполни permissions или rules")

    # Правило 8: бюджеты
    budgets = doc.get("budgets")
    if not isinstance(budgets, dict):
        errors.append("раздел budgets отсутствует — лимиты обязательны")
    else:
        for field in BUDGET_FIELDS:
            if field not in budgets:
                errors.append("budgets.%s отсутствует — лимит обязателен" % field)
            elif budgets[field] is None:
                errors.append("budgets.%s: 0 означает „запрещено“, null не допускается" % field)
            elif isinstance(budgets[field], bool) or not isinstance(budgets[field], int) or budgets[field] < 0:
                errors.append("budgets.%s = %r — нужно целое число от 0 и больше" % (field, budgets[field]))

    # Правило 9: эксплуатация
    if is_blank(ops.get("success_metric")):
        errors.append("operations.success_metric — не сказано, как понять, что агент работает хорошо")
    if is_blank(ops.get("owner_on_call")):
        errors.append("operations.owner_on_call — не назначен человек, отвечающий за агента")

    # Предупреждения (не блокируют выпуск)
    if is_blank(agent.get("immutable_bundle_id")):
        warns.append("agent.immutable_bundle_id пуст — без него не доказать, какая именно сборка стоит у клиента")
    if is_blank(agent.get("data_classification")):
        warns.append("agent.data_classification пуст — укажи, какие данные обрабатывает агент")
    return errors, warns


def load_passport(path):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("ОШИБКА: не смог прочитать файл %s: %s" % (path, exc))
        sys.exit(2)
    if path.lower().endswith(".json"):
        try:
            return json.loads(text)
        except ValueError as exc:
            print("ОШИБКА: файл %s — не корректный JSON: %s" % (path, exc))
            sys.exit(2)
    try:
        import yaml
    except ImportError:
        print("Чтобы читать YAML-файлы, нужна библиотека pyyaml.")
        print("Поставь pyyaml: python3 -m pip install pyyaml")
        print("Или сохрани паспорт как .json — JSON проверяется без установки.")
        sys.exit(2)
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError as exc:
        print("ОШИБКА: файл %s — не корректный YAML: %s" % (path, exc))
        sys.exit(2)
    if not docs:
        print("ОШИБКА: файл %s пуст" % path)
        sys.exit(2)
    return docs[0]


# --- Встроенные примеры для --selftest (JSON, чтобы работать без pyyaml) ---
GOOD_JSON = """{
  "agent": {"name": "ET-Tech | Сводка заявок", "owner": "Анвар", "business_goal": "Утренняя сводка заявок",
            "model_profile": "qwen-3.7", "version": "1.0.0", "immutable_bundle_id": "bundle-20260725",
            "data_classification": "внутренние данные"},
  "capabilities": [{"name": "daily_digest", "version": "1.0.0", "autonomy": "A1", "side_effects": "none",
                    "confirmation": "never", "idempotency": "supported", "global": false,
                    "rollback": "", "evidence_schema": "", "permissions": [], "rules": []}],
  "budgets": {"max_duration_ms": 30000, "max_llm_tokens": 8000, "max_delegation_depth": 1, "max_external_actions": 0},
  "operations": {"success_metric": "сводка доставлена до 09:00", "owner_on_call": "Анвар"}
}"""

BAD_JSON = """{
  "agent": {"name": "Плохой агент", "owner": "", "business_goal": "Демонстрация ошибок",
            "model_profile": "claude-sonnet-4", "version": "0.1.0", "immutable_bundle_id": "x",
            "data_classification": "тест"},
  "capabilities": [{"name": "send_emails", "version": "1.0.0", "autonomy": "A9", "side_effects": "external",
                    "confirmation": "never", "idempotency": "supported", "global": false,
                    "rollback": "шлём только черновики, отправляет человек",
                    "evidence_schema": "лог отправки", "permissions": [], "rules": []}],
  "budgets": {"max_duration_ms": 30000, "max_llm_tokens": null, "max_delegation_depth": 0, "max_external_actions": 1},
  "operations": {"success_metric": "письмо согласовано", "owner_on_call": "Анвар"}
}"""

RULE_CHECKS = (
    ("Правило 1 (обязательные поля агента)", "agent.owner"),
    ("Правило 2 (только Qwen, не Claude)", "только на Qwen"),
    ("Правило 4 (autonomy строго A0..A4)", "допустимо только A0..A4"),
    ("Правило 5 (external без подтверждения запрещён)", "совсем без подтверждения"),
    ("Правило 8 (null в бюджетах запрещён)", "null не допускается"),
)


def selftest():
    print("Самопроверка инструмента (файлы не нужны, примеры встроены как JSON):")
    ok = True
    good_errors, _ = check(json.loads(GOOD_JSON))
    if good_errors:
        ok = False
        print("FAIL: правильный паспорт — нашлись лишние ошибки:")
        for err in good_errors:
            print("      - " + err)
    else:
        print("PASS: правильный паспорт проходит без ошибок")
    bad_errors, _ = check(json.loads(BAD_JSON))
    for label, needle in RULE_CHECKS:
        if any(needle in err for err in bad_errors):
            print("PASS: %s — ошибка поймана" % label)
        else:
            ok = False
            print("FAIL: %s — ошибка НЕ поймана" % label)
    if len(bad_errors) != len(RULE_CHECKS):
        ok = False
        print("FAIL: в плохом паспорте ожидалось %d ошибок, найдено %d" % (len(RULE_CHECKS), len(bad_errors)))
        for err in bad_errors:
            print("      - " + err)
    else:
        print("PASS: в плохом паспорте ровно %d ошибок, лишних нет" % len(RULE_CHECKS))
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) != 1 or argv[0].startswith("-"):
        print("Как пользоваться:")
        print("  python3 check_agent_passport.py путь/к/паспорту.yaml   (или .json)")
        print("  python3 check_agent_passport.py --selftest")
        return 2
    path = argv[0]
    if not os.path.exists(path):
        print("ОШИБКА: файл не найден: %s" % path)
        return 2
    doc = load_passport(path)
    if not isinstance(doc, dict):
        print("ОШИБКА: внутри файла не паспорт — ожидаются разделы agent, capabilities, budgets, operations")
        print("ИТОГ: НЕ ГОТОВ — исправь ошибки выше")
        return 1
    errors, warns = check(doc)
    for err in errors:
        print("ОШИБКА: " + err)
    for warn in warns:
        print("ВНИМАНИЕ: " + warn)
    if errors:
        print("ИТОГ: НЕ ГОТОВ — исправь ошибки выше")
        return 1
    print("ИТОГ: ГОТОВ К ВЫПУСКУ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
