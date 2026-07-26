#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка паспорта агента Extella.

Как пользоваться:
  python3 check_agent_passport.py путь/к/паспорту.yaml   (поддерживается и .json)
  python3 check_agent_passport.py путь/к/паспорту.yaml --json
  python3 check_agent_passport.py --selftest             (самопроверка без файлов)

Коды выхода: 0 — паспорт готов, 1 — есть ошибки, 2 — файл не прочитан.
"""
import json
import os
import re
import sys

AUTONOMY = {"A0", "A1", "A2", "A3", "A4"}
SIDE_EFFECTS = {"none", "local", "external", "physical"}
CONFIRMATION = {"never", "conditional", "always"}
IDEMPOTENCY = {"supported", "unsupported"}
BUDGET_FIELDS = ("max_duration_ms", "max_llm_tokens", "max_delegation_depth", "max_external_actions")
PLATFORM_AGENT_ID_RE = re.compile(r"^agent_[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")
SHARED_GENE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
SHARED_GENE_KINDS = {"knowledge", "rule", "expert", "handler"}
QWEN_PROFILE_RE = re.compile(
    r"^(?:(?:alibaba|aliyun|dashscope)\s*[/:\s]\s*)?"
    r"qwen(?:[0-9][a-z0-9._-]*|[\s._-][a-z0-9][a-z0-9._-]*)?$",
    re.IGNORECASE,
)
CHECK_REPORT_SCHEMA = "extella.agent_passport.check_report.v1"


def is_blank(value):
    """Пустое значение: None или строка из одних пробелов."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def _finish_report(issues):
    """Стабильный машинный отчёт: ошибки первыми, затем предупреждения."""
    ordered = ([x for x in issues if x["severity"] == "error"] +
               [x for x in issues if x["severity"] == "warning"])
    errors = sum(1 for x in ordered if x["severity"] == "error")
    warnings = len(ordered) - errors
    return {
        "schema": CHECK_REPORT_SCHEMA,
        "ready": errors == 0,
        "counts": {"errors": errors, "warnings": warnings, "issues": len(ordered)},
        "issues": ordered,
    }


def check_report(doc):
    """Проверяет паспорт и возвращает структурированный двуязычный отчёт.

    Это единый источник расчёта соответствия для CLI, Evolution Console и
    генератора Agent Cabinet. Потребители используют ``code`` и ``path``, а не
    разбирают человекочитаемый текст.
    """
    issues = []

    def add(code, severity, path, message_ru, message_en):
        issues.append({
            "code": code,
            "severity": severity,
            "path": path,
            "message_ru": message_ru,
            "message_en": message_en,
        })

    if not isinstance(doc, dict):
        add(
            "PASSPORT_DOCUMENT_INVALID", "error", "$",
            "внутри файла не паспорт — ожидаются разделы agent, capabilities, budgets, operations",
            "the document is not an Agent Passport — expected agent, capabilities, budgets, and operations sections",
        )
        return _finish_report(issues)

    agent = doc.get("agent") if isinstance(doc.get("agent"), dict) else {}
    caps = doc.get("capabilities") if isinstance(doc.get("capabilities"), list) else []
    ops = doc.get("operations") if isinstance(doc.get("operations"), dict) else {}

    # Правило 10: пустой шаблон — говорим честно и не сыплем десятком ошибок
    if is_blank(agent.get("name")) and all(is_blank(c.get("name")) for c in caps if isinstance(c, dict)):
        add(
            "PASSPORT_TEMPLATE_EMPTY", "error", "$",
            "паспорт не заполнен — это пустой шаблон; впиши имя агента, владельца, "
            "бизнес-цель и хотя бы одну способность, потом запусти проверку снова",
            "the Agent Passport is an empty template; add the agent name, owner, business goal, "
            "and at least one capability, then run the check again",
        )
        return _finish_report(issues)

    # Правило 1: обязательные поля агента
    required_agent_fields = (
        ("name", "имя агента", "agent name", "AGENT_NAME_REQUIRED"),
        ("owner", "владелец", "owner", "AGENT_OWNER_REQUIRED"),
        ("business_goal", "бизнес-цель", "business goal", "AGENT_BUSINESS_GOAL_REQUIRED"),
        ("version", "версия", "version", "AGENT_VERSION_REQUIRED"),
    )
    for field, label_ru, label_en, code in required_agent_fields:
        if is_blank(agent.get(field)):
            add(
                code, "error", "agent.%s" % field,
                "agent.%s (%s) — поле пустое, заполни его" % (field, label_ru),
                "agent.%s (%s) is blank — fill it in" % (field, label_en),
            )

    # Стабильная привязка Agent Passport к живому агенту. Имена не уникальны и
    # не могут использоваться Evolution Console как ключ сверки.
    platform_agent_id = str(agent.get("platform_agent_id") or "").strip()
    if not platform_agent_id:
        add(
            "AGENT_PLATFORM_ID_REQUIRED", "error", "agent.platform_agent_id",
            "agent.platform_agent_id — не указан стабильный идентификатор агента на платформе. "
            "Исправление: в Evolution Console выбери живого агента и нажми "
            "«Создать черновик Agent Passport».",
            "agent.platform_agent_id is required to bind the Agent Passport to a stable platform agent. "
            "To fix it, open Evolution Console, select the live agent, and choose "
            "“Create Agent Passport draft”.",
        )
    elif not PLATFORM_AGENT_ID_RE.fullmatch(platform_agent_id):
        add(
            "AGENT_PLATFORM_ID_INVALID", "error", "agent.platform_agent_id",
            "agent.platform_agent_id = «%s» — ожидается стабильный идентификатор вида agent_..."
            % agent.get("platform_agent_id"),
            "agent.platform_agent_id = %r is invalid — expected a stable identifier beginning with agent_"
            % agent.get("platform_agent_id"),
        )

    # Optional live-platform metadata used when Evolution Console prepares an
    # Agent Passport draft. Human-owned fields (owner, goal, limits, budgets)
    # remain blank until a person completes them.
    if "platform_provider" in agent and not isinstance(agent.get("platform_provider"), str):
        add(
            "AGENT_PLATFORM_PROVIDER_STRING_REQUIRED", "error", "agent.platform_provider",
            "agent.platform_provider — ожидается строка с поставщиком модели из platform agent/get",
            "agent.platform_provider must be a string copied from platform agent/get",
        )
    if "declared_instructions" in agent and not isinstance(agent.get("declared_instructions"), str):
        add(
            "AGENT_DECLARED_INSTRUCTIONS_STRING_REQUIRED", "error", "agent.declared_instructions",
            "agent.declared_instructions — ожидается строка с заявленными инструкциями агента",
            "agent.declared_instructions must be a string containing the declared agent instructions",
        )

    # Правило 2: только Qwen
    profile = str(agent.get("model_profile") or "").strip()
    if not QWEN_PROFILE_RE.fullmatch(profile):
        add(
            "AGENT_MODEL_PROFILE_QWEN_REQUIRED", "error", "agent.model_profile",
            "agent.model_profile = «%s»: клиентские агенты работают только на Qwen"
            % agent.get("model_profile"),
            "agent.model_profile = %r: client agents must use Qwen"
            % agent.get("model_profile"),
        )

    # Правила 3–7: способности
    if not caps:
        add(
            "CAPABILITIES_REQUIRED", "error", "capabilities",
            "в паспорте нет ни одной способности (capabilities) — нужна минимум одна",
            "the Agent Passport has no capabilities — at least one is required",
        )
    for i, cap in enumerate(caps, 1):
        path = "capabilities[%d]" % (i - 1)
        if not isinstance(cap, dict):
            add(
                "CAPABILITY_DOCUMENT_INVALID", "error", path,
                "способность №%d: это не набор полей — проверь отступы в файле" % i,
                "capability #%d is not an object — check the document indentation" % i,
            )
            continue
        tag = "способность №%d" % i + ("" if is_blank(cap.get("name")) else " «%s»" % cap.get("name"))
        if is_blank(cap.get("name")):
            add(
                "CAPABILITY_NAME_REQUIRED", "error", path + ".name",
                tag + ": не заполнено имя (name)",
                "capability #%d: name is blank" % i,
            )
        if is_blank(cap.get("version")):
            add(
                "CAPABILITY_VERSION_REQUIRED", "error", path + ".version",
                tag + ": не заполнена версия (version)",
                "capability #%d: version is blank" % i,
            )
        allowed_fields = (
            ("autonomy", AUTONOMY, "A0..A4", "CAPABILITY_AUTONOMY_INVALID"),
            ("side_effects", SIDE_EFFECTS, "none | local | external | physical",
             "CAPABILITY_SIDE_EFFECTS_INVALID"),
            ("confirmation", CONFIRMATION, "never | conditional | always",
             "CAPABILITY_CONFIRMATION_INVALID"),
            ("idempotency", IDEMPOTENCY, "supported | unsupported",
             "CAPABILITY_IDEMPOTENCY_INVALID"),
        )
        for field, allowed, hint, code in allowed_fields:
            if cap.get(field) not in allowed:
                add(
                    code, "error", path + "." + field,
                    "%s: %s = «%s» — допустимо только %s" % (tag, field, cap.get(field), hint),
                    "capability #%d: %s = %r — allowed values: %s"
                    % (i, field, cap.get(field), hint),
                )
        se, conf = cap.get("side_effects"), cap.get("confirmation")
        if se == "physical" and conf != "always":
            add(
                "CAPABILITY_PHYSICAL_CONFIRMATION_REQUIRED", "error", path + ".confirmation",
                tag + ": физическое действие (side_effects=physical) обязано подтверждаться "
                "человеком — поставь confirmation: always",
                "capability #%d: a physical action must always be confirmed by a person; "
                "set confirmation: always" % i,
            )
        if se == "external" and conf == "never":
            add(
                "CAPABILITY_EXTERNAL_CONFIRMATION_REQUIRED", "error", path + ".confirmation",
                tag + ": внешнее действие (side_effects=external) нельзя выполнять "
                "совсем без подтверждения — confirmation: never запрещён",
                "capability #%d: an external action cannot run with no confirmation; "
                "confirmation: never is forbidden" % i,
            )
        if se in ("local", "external", "physical"):
            if is_blank(cap.get("rollback")):
                add(
                    "CAPABILITY_ROLLBACK_REQUIRED", "error", path + ".rollback",
                    tag + ": есть побочные эффекты, но не описан путь отката (rollback)",
                    "capability #%d has side effects but no rollback path" % i,
                )
            if is_blank(cap.get("evidence_schema")):
                add(
                    "CAPABILITY_EVIDENCE_REQUIRED", "error", path + ".evidence_schema",
                    tag + ": есть побочные эффекты, но не описано доказательство "
                    "исполнения (evidence_schema)",
                    "capability #%d has side effects but no execution evidence_schema" % i,
                )
        if cap.get("global") is True:
            if is_blank(cap.get("rollback")):
                add(
                    "LEGACY_GLOBAL_ROLLBACK_REQUIRED", "error", path + ".rollback",
                    tag + ": global=true требует заполненного пути отката (rollback)",
                    "capability #%d: legacy global=true requires a rollback path" % i,
                )
            if not (cap.get("permissions") or cap.get("rules")):
                add(
                    "LEGACY_GLOBAL_OWNERSHIP_REQUIRED", "error", path,
                    tag + ": глобальный объект без владения запрещён — при global=true "
                    "заполни permissions или rules",
                    "capability #%d: an unowned global object is forbidden; with global=true, "
                    "fill permissions or rules" % i,
                )
        # Правило 11: ГРАНИЦЫ обязательны. Возможность без честно названного предела нельзя выпускать:
        # предел клиент узнаёт от нас заранее, а не в работе постфактум (§3.20 стандарта).
        limits = cap.get("limits")
        if not isinstance(limits, list) or not [x for x in limits if not is_blank(x)]:
            add(
                "CAPABILITY_LIMITS_REQUIRED", "error", path + ".limits",
                tag + ": не названы границы (limits) — напиши хотя бы одну честную строку "
                "«чего эта возможность НЕ делает»; без границ выпуск запрещён",
                "capability #%d has no limits; add at least one honest statement of what it does NOT do"
                % i,
            )
        # Правило 12: пояснение на экране. Пользователь обязан понять возможность сам.
        # Значение internal допустимо только для служебных способностей без своего экрана.
        surface = str(cap.get("help_surface") or "").strip()
        if not surface:
            add(
                "CAPABILITY_HELP_SURFACE_REQUIRED", "error", path + ".help_surface",
                tag + ": не указано пояснение на экране (help_surface) — где человек прочитает "
                "«как это работает». Для служебной способности без экрана напиши internal",
                "capability #%d has no help_surface showing where the user can learn how it works; "
                "use internal only for a service capability with no screen" % i,
            )
        elif surface.lower() == "internal":
            add(
                "CAPABILITY_HELP_SURFACE_INTERNAL", "warning", path + ".help_surface",
                tag + ": help_surface=internal — у способности нет пользовательского экрана; "
                "убедись, что она действительно служебная",
                "capability #%d has help_surface=internal and no user-facing screen; "
                "confirm that it is truly an internal capability" % i,
            )

    # Canonical Shared Genes. Legacy capability.global remains supported for
    # existing passports, but Evolution Console counts consumers only by the
    # stable gene_id records below, never by display names.
    shared_genes = doc.get("shared_genes", []) if "shared_genes" in doc else []
    if not isinstance(shared_genes, list):
        add(
            "SHARED_GENES_LIST_REQUIRED", "error", "shared_genes",
            "shared_genes должен быть списком общих элементов Agent Genome",
            "shared_genes must be a list of shared Agent Genome elements",
        )
        shared_genes = []
    seen_gene_ids = set()
    for i, gene in enumerate(shared_genes):
        path = "shared_genes[%d]" % i
        if not isinstance(gene, dict):
            add(
                "SHARED_GENE_DOCUMENT_INVALID", "error", path,
                "Shared Gene №%d: ожидается набор полей" % (i + 1),
                "Shared Gene #%d must be an object" % (i + 1),
            )
            continue
        gene_id = str(gene.get("gene_id") or "").strip()
        if not gene_id:
            add(
                "SHARED_GENE_ID_REQUIRED", "error", path + ".gene_id",
                "Shared Gene №%d: не заполнен стабильный gene_id" % (i + 1),
                "Shared Gene #%d is missing its stable gene_id" % (i + 1),
            )
        elif not SHARED_GENE_ID_RE.fullmatch(gene_id):
            add(
                "SHARED_GENE_ID_INVALID", "error", path + ".gene_id",
                "Shared Gene №%d: gene_id = «%s» — допустимы 3–128 символов "
                "A–Z, a–z, 0–9, точка, подчёркивание, двоеточие и дефис"
                % (i + 1, gene.get("gene_id")),
                "Shared Gene #%d has invalid gene_id %r; use 3–128 characters from "
                "A–Z, a–z, 0–9, dot, underscore, colon, and hyphen"
                % (i + 1, gene.get("gene_id")),
            )
        elif gene_id in seen_gene_ids:
            add(
                "SHARED_GENE_ID_DUPLICATE", "error", path + ".gene_id",
                "Shared Gene №%d: gene_id «%s» повторяется в этом Agent Passport"
                % (i + 1, gene_id),
                "Shared Gene #%d repeats gene_id %r in this Agent Passport"
                % (i + 1, gene_id),
            )
        else:
            seen_gene_ids.add(gene_id)

        kind = gene.get("kind")
        if kind not in SHARED_GENE_KINDS:
            add(
                "SHARED_GENE_KIND_INVALID", "error", path + ".kind",
                "Shared Gene №%d: kind = «%s» — допустимо только knowledge | rule | expert | handler"
                % (i + 1, kind),
                "Shared Gene #%d has kind = %r; allowed values are knowledge | rule | expert | handler"
                % (i + 1, kind),
            )
        if is_blank(gene.get("name")):
            add(
                "SHARED_GENE_NAME_REQUIRED", "error", path + ".name",
                "Shared Gene №%d: не заполнено имя (name)" % (i + 1),
                "Shared Gene #%d is missing name" % (i + 1),
            )
        if is_blank(gene.get("version")):
            add(
                "SHARED_GENE_VERSION_REQUIRED", "error", path + ".version",
                "Shared Gene №%d: не заполнена версия (version)" % (i + 1),
                "Shared Gene #%d is missing version" % (i + 1),
            )
        if gene.get("provenance") != "global":
            add(
                "SHARED_GENE_PROVENANCE_GLOBAL_REQUIRED", "error", path + ".provenance",
                "Shared Gene №%d: provenance должен быть global" % (i + 1),
                "Shared Gene #%d must have provenance=global" % (i + 1),
            )

    # Правило 13: ДВА ЯЗЫКА обязательны. Продукт делается сразу на русском и английском:
    # интерфейс, пояснения «как это работает», сообщения об ошибках. Доперевод «когда-нибудь»
    # на практике не наступает, а англоязычный клиент видит полуфабрикат.
    langs = agent.get("languages")
    have = {str(x).strip().lower() for x in langs} if isinstance(langs, list) else set()
    if not {"ru", "en"} <= have:
        add(
            "AGENT_LANGUAGES_RU_EN_REQUIRED", "error", "agent.languages",
            "agent.languages должен содержать оба языка: [\"ru\", \"en\"] — интерфейс, "
            "пояснения и ошибки делаются сразу на двух языках, доперевод потом не считается",
            "agent.languages must contain both languages: [\"ru\", \"en\"]; the interface, "
            "help, and errors must ship in both languages",
        )

    # Правило 8: бюджеты
    budgets = doc.get("budgets")
    if not isinstance(budgets, dict):
        add(
            "BUDGETS_REQUIRED", "error", "budgets",
            "раздел budgets отсутствует — лимиты обязательны",
            "the budgets section is missing — limits are required",
        )
    else:
        for field in BUDGET_FIELDS:
            if field not in budgets:
                add(
                    "BUDGET_FIELD_REQUIRED", "error", "budgets.%s" % field,
                    "budgets.%s отсутствует — лимит обязателен" % field,
                    "budgets.%s is missing — the limit is required" % field,
                )
            elif budgets[field] is None:
                add(
                    "BUDGET_NULL_FORBIDDEN", "error", "budgets.%s" % field,
                    "budgets.%s: 0 означает „запрещено“, null не допускается" % field,
                    "budgets.%s: 0 means forbidden; null is not allowed" % field,
                )
            elif isinstance(budgets[field], bool) or not isinstance(budgets[field], int) or budgets[field] < 0:
                add(
                    "BUDGET_NONNEGATIVE_INTEGER_REQUIRED", "error", "budgets.%s" % field,
                    "budgets.%s = %r — нужно целое число от 0 и больше" % (field, budgets[field]),
                    "budgets.%s = %r — expected an integer greater than or equal to 0"
                    % (field, budgets[field]),
                )

    # Правило 9: эксплуатация
    if is_blank(ops.get("success_metric")):
        add(
            "OPERATIONS_SUCCESS_METRIC_REQUIRED", "error", "operations.success_metric",
            "operations.success_metric — не сказано, как понять, что агент работает хорошо",
            "operations.success_metric does not say how to tell whether the agent works well",
        )
    if is_blank(ops.get("owner_on_call")):
        add(
            "OPERATIONS_OWNER_ON_CALL_REQUIRED", "error", "operations.owner_on_call",
            "operations.owner_on_call — не назначен человек, отвечающий за агента",
            "operations.owner_on_call does not name the person responsible for the agent",
        )

    # Предупреждения (не блокируют выпуск)
    if is_blank(agent.get("immutable_bundle_id")):
        add(
            "AGENT_IMMUTABLE_BUNDLE_ID_RECOMMENDED", "warning", "agent.immutable_bundle_id",
            "agent.immutable_bundle_id пуст — без него не доказать, какая именно сборка стоит у клиента",
            "agent.immutable_bundle_id is blank — without it, the exact deployed bundle cannot be proven",
        )
    if is_blank(agent.get("data_classification")):
        add(
            "AGENT_DATA_CLASSIFICATION_RECOMMENDED", "warning", "agent.data_classification",
            "agent.data_classification пуст — укажи, какие данные обрабатывает агент",
            "agent.data_classification is blank — state which data the agent processes",
        )
    return _finish_report(issues)


def check(doc):
    """Совместимый API: возвращает русские списки (ошибки, предупреждения)."""
    report = check_report(doc)
    errors = [x["message_ru"] for x in report["issues"] if x["severity"] == "error"]
    warns = [x["message_ru"] for x in report["issues"] if x["severity"] == "warning"]
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
            "platform_agent_id": "agent_qwen_daily_digest_20260725",
            "platform_provider": "alibaba",
            "declared_instructions": "Prepare a read-only daily digest.",
            "languages": ["ru", "en"],
            "data_classification": "внутренние данные"},
  "capabilities": [{"name": "daily_digest", "version": "1.0.0", "autonomy": "A1", "side_effects": "none",
                    "confirmation": "never", "idempotency": "supported", "global": false,
                    "rollback": "", "evidence_schema": "", "permissions": [], "rules": [],
                    "help_surface": "карточка процесса → кнопка «? Как это работает»",
                    "limits": ["не подключается к живой CRM — работает по выгрузке",
                               "сканы и картинки не читает"]}],
  "shared_genes": [{"gene_id": "rule.daily-digest-policy", "kind": "rule",
                    "name": "Daily digest policy", "version": "1.0.0", "provenance": "global"}],
  "budgets": {"max_duration_ms": 30000, "max_llm_tokens": 8000, "max_delegation_depth": 1, "max_external_actions": 0},
  "operations": {"success_metric": "сводка доставлена до 09:00", "owner_on_call": "Анвар"}
}"""

BAD_JSON = """{
  "agent": {"name": "Плохой агент", "owner": "", "business_goal": "Демонстрация ошибок",
            "model_profile": "claude-sonnet-4", "version": "0.1.0", "immutable_bundle_id": "x",
            "platform_agent_id": "agent_bad_example_20260725",
            "data_classification": "тест"},
  "capabilities": [{"name": "send_emails", "version": "1.0.0", "autonomy": "A9", "side_effects": "external",
                    "confirmation": "never", "idempotency": "supported", "global": false,
                    "rollback": "шлём только черновики, отправляет человек",
                    "evidence_schema": "лог отправки", "permissions": [], "rules": [],
                    "limits": [], "help_surface": ""}],
  "budgets": {"max_duration_ms": 30000, "max_llm_tokens": null, "max_delegation_depth": 0, "max_external_actions": 1},
  "operations": {"success_metric": "письмо согласовано", "owner_on_call": "Анвар"}
}"""

RULE_CHECKS = (
    ("Правило 1 (обязательные поля агента)", "agent.owner"),
    ("Правило 2 (только Qwen, не Claude)", "только на Qwen"),
    ("Правило 4 (autonomy строго A0..A4)", "допустимо только A0..A4"),
    ("Правило 5 (external без подтверждения запрещён)", "совсем без подтверждения"),
    ("Правило 8 (null в бюджетах запрещён)", "null не допускается"),
    ("Правило 11 (границы обязательны)", "не названы границы"),
    ("Правило 12 (пояснение на экране обязательно)", "не указано пояснение на экране"),
    ("Правило 13 (русский и английский сразу)", "должен содержать оба языка"),
)

REPORT_CODES = {
    "AGENT_OWNER_REQUIRED",
    "AGENT_MODEL_PROFILE_QWEN_REQUIRED",
    "CAPABILITY_AUTONOMY_INVALID",
    "CAPABILITY_EXTERNAL_CONFIRMATION_REQUIRED",
    "BUDGET_NULL_FORBIDDEN",
    "CAPABILITY_LIMITS_REQUIRED",
    "CAPABILITY_HELP_SURFACE_REQUIRED",
    "AGENT_LANGUAGES_RU_EN_REQUIRED",
}


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

    good_report = check_report(json.loads(GOOD_JSON))
    bad_report = check_report(json.loads(BAD_JSON))
    report_checks = [
        ("структурированный отчёт имеет стабильную схему",
         good_report["schema"] == CHECK_REPORT_SCHEMA),
        ("готовность отчёта совпадает с legacy check()",
         good_report["ready"] and not good_errors),
        ("счётчики отчёта совпадают с legacy errors/warnings",
         bad_report["counts"]["errors"] == len(bad_errors)
         and bad_report["counts"]["warnings"] == len(check(json.loads(BAD_JSON))[1])),
        ("коды плохого паспорта стабильны и полны",
         {x["code"] for x in bad_report["issues"]} == REPORT_CODES),
        ("каждая issue двуязычна и имеет severity/path",
         all(x.get("severity") in ("error", "warning") and x.get("path")
             and x.get("message_ru") and x.get("message_en")
             for x in bad_report["issues"])),
    ]
    for label, passed in report_checks:
        print(("PASS: " if passed else "FAIL: ") + label)
        ok = ok and passed

    for profile in ("gpt-4o", "", "anthropic/claude", "claude/qwen", "not-qwen", "qwenfake"):
        non_qwen = json.loads(GOOD_JSON)
        non_qwen["agent"]["model_profile"] = profile
        codes = {x["code"] for x in check_report(non_qwen)["issues"]}
        passed = "AGENT_MODEL_PROFILE_QWEN_REQUIRED" in codes
        print(("PASS: " if passed else "FAIL: ") +
              "строгий Qwen-гейт отклоняет model_profile=%r" % profile)
        ok = ok and passed
    valid_profiles = ("qwen-3.7", "Qwen3.7", "alibaba/qwen-max", "dashscope: qwen_test")
    valid_qwen_ok = all(
        "AGENT_MODEL_PROFILE_QWEN_REQUIRED" not in
        {x["code"] for x in check_report(
            dict(json.loads(GOOD_JSON),
                 agent=dict(json.loads(GOOD_JSON)["agent"], model_profile=profile))
        )["issues"]}
        for profile in valid_profiles
    )
    print(("PASS: " if valid_qwen_ok else "FAIL: ") +
          "строгий Qwen-гейт принимает canonical Qwen profile variants")
    ok = ok and valid_qwen_ok

    missing_id = json.loads(GOOD_JSON)
    missing_id["agent"]["platform_agent_id"] = ""
    missing_id_issue = next(
        (x for x in check_report(missing_id)["issues"]
         if x["code"] == "AGENT_PLATFORM_ID_REQUIRED"),
        None,
    )
    invalid_id = json.loads(GOOD_JSON)
    invalid_id["agent"]["platform_agent_id"] = "not-an-agent-id"
    id_checks = [
        ("отсутствующий platform_agent_id отклонён",
         missing_id_issue is not None),
        ("исправление отсутствующего platform_agent_id объяснено для RU и EN",
         missing_id_issue is not None
         and "Evolution Console" in missing_id_issue["message_ru"]
         and "живого агента" in missing_id_issue["message_ru"]
         and "«Создать черновик Agent Passport»" in missing_id_issue["message_ru"]
         and "Evolution Console" in missing_id_issue["message_en"]
         and "live agent" in missing_id_issue["message_en"]
         and "“Create Agent Passport draft”" in missing_id_issue["message_en"]),
        ("нестабильный platform_agent_id отклонён",
         "AGENT_PLATFORM_ID_INVALID" in
         {x["code"] for x in check_report(invalid_id)["issues"]}),
    ]
    for label, passed in id_checks:
        print(("PASS: " if passed else "FAIL: ") + label)
        ok = ok and passed

    invalid_live_metadata = json.loads(GOOD_JSON)
    invalid_live_metadata["agent"]["platform_provider"] = ["alibaba"]
    invalid_live_metadata["agent"]["declared_instructions"] = {"text": "unsafe shape"}
    metadata_codes = {x["code"] for x in check_report(invalid_live_metadata)["issues"]}
    metadata_ok = {
        "AGENT_PLATFORM_PROVIDER_STRING_REQUIRED",
        "AGENT_DECLARED_INSTRUCTIONS_STRING_REQUIRED",
    } <= metadata_codes
    print(("PASS: " if metadata_ok else "FAIL: ") +
          "optional live provider/instructions имеют строгий строковый контракт")
    ok = ok and metadata_ok

    duplicate_gene = json.loads(GOOD_JSON)
    duplicate_gene["shared_genes"].append(dict(duplicate_gene["shared_genes"][0]))
    invalid_gene = json.loads(GOOD_JSON)
    invalid_gene["shared_genes"][0].update({
        "gene_id": "bad id",
        "kind": "other",
        "name": "",
        "version": "",
        "provenance": "agent",
    })
    shared_checks = [
        ("canonical Shared Gene проходит единый гейт",
         not {x["code"] for x in good_report["issues"] if x["code"].startswith("SHARED_GENE")}),
        ("повтор stable gene_id отклонён",
         "SHARED_GENE_ID_DUPLICATE" in
         {x["code"] for x in check_report(duplicate_gene)["issues"]}),
        ("невалидный Shared Gene даёт все field-level codes",
         {
             "SHARED_GENE_ID_INVALID",
             "SHARED_GENE_KIND_INVALID",
             "SHARED_GENE_NAME_REQUIRED",
             "SHARED_GENE_VERSION_REQUIRED",
             "SHARED_GENE_PROVENANCE_GLOBAL_REQUIRED",
         } <= {x["code"] for x in check_report(invalid_gene)["issues"]}),
    ]
    for label, passed in shared_checks:
        print(("PASS: " if passed else "FAIL: ") + label)
        ok = ok and passed

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    json_mode = "--json" in argv
    unknown_flags = [a for a in argv if a.startswith("-") and a != "--json"]
    args = [a for a in argv if not a.startswith("-")]
    if len(args) != 1 or unknown_flags:
        print("Как пользоваться:")
        print("  python3 check_agent_passport.py путь/к/паспорту.yaml [--json]   (или .json)")
        print("  python3 check_agent_passport.py --selftest")
        return 2
    path = args[0]
    if not os.path.exists(path):
        print("ОШИБКА: файл не найден: %s" % path)
        return 2
    doc = load_passport(path)
    if not isinstance(doc, dict):
        print("ОШИБКА: внутри файла не паспорт — ожидаются разделы agent, capabilities, budgets, operations")
        print("ИТОГ: НЕ ГОТОВ — исправь ошибки выше")
        return 1
    report = check_report(doc)
    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["ready"] else 1
    errors = [x["message_ru"] for x in report["issues"] if x["severity"] == "error"]
    warns = [x["message_ru"] for x in report["issues"] if x["severity"] == "warning"]
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
