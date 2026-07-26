#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Базовая технология кабинета агента: КАБИНЕТ СОБИРАЕТСЯ ИЗ ПАСПОРТА, а не пишется руками.

Замысел (Анвар, 26.07.2026): у каждого агента должен быть свой кабинет — «Паспорт» (что это за
агент и как он работает сейчас) и «Эволюция» (изменение через черновик → тест → публикацию →
откат). Чтобы это не делали руками для каждого агента, кабинет ГЕНЕРИРУЕТСЯ из паспорта агента,
который уже обязателен по стандарту и уже проверяется `check_agent_passport.py`.

Путь агента получается такой:
    заполнил Agent Passport → проверялка пропустила → Agent Cabinet появился сам →
    агент виден в Evolution Console

Как пользоваться:
  python3 build_agent_cabinet.py мой_агент.yaml            → кабинет в JSON (для интерфейса)
  python3 build_agent_cabinet.py мой_агент.yaml --markdown → человекочитаемый вид
  python3 build_agent_cabinet.py --selftest                → самопроверка без файлов

Коды выхода: 0 — кабинет собран, 1 — паспорт не проходит стандарт (кабинет не собираем), 2 — файл не прочитан.

ЧЕСТНОСТЬ ВСТРОЕНА: раздел «Как работает фактически» перечисляет ТОЛЬКО те источники доказательств,
которые реально есть, и рядом — границы (чего мы не видим). Кабинет, обещающий полную картину без
неё, — это ровно та ложь, против которой задумано разделение «заявленное / фактическое».
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import check_report, load_passport, is_blank   # единый источник правил стандарта

CABINET_SCHEMA = "extella.agent_cabinet.v1.1"

# Что кабинет ЧЕСТНО не может показать, пока платформа не даст механизмы (эскалации A4/#7/#11).
PLATFORM_LIMITS = {
    "ru": [
        "Видны только запуски через управляемый контур: прямые разговоры с агентом в чате платформы не отслеживаются (нативной трассировки нет).",
        "Расходы и токены — оценка по нашим квитанциям, а не биллинговый факт.",
        "Журнал не защищён от подделки: tamper-evident аудита платформа пока не даёт.",
        "Ролей «только смотреть» / «только запускать» нет — разграничение доступа ждёт платформенной модели ролей.",
        "Цепочки «агент вызвал агента» видны частично — сквозной трассировки между агентами нет.",
    ],
    "en": [
        "Only runs through the managed loop are visible: direct chats with the agent on the platform are not traced (no native tracing).",
        "Cost and tokens are an estimate from our own receipts, not a billing fact.",
        "The log is not tamper-evident: the platform does not provide that yet.",
        "There are no «view only» / «run only» roles — access separation awaits a platform role model.",
        "Agent-to-agent chains are only partly visible — there is no end-to-end tracing between agents.",
    ],
}

EVIDENCE_SOURCES = [
    ("run_history",
     "История прогонов процессов (что запускалось, когда, с каким результатом)",
     "Process run history (what ran, when, and with which result)"),
    ("upc_steps",
     "Пошаговые журналы процесса: какие шаги выполнялись и что вернули",
     "Step-by-step process logs: which steps ran and what they returned"),
    ("ledger_receipts",
     "Evolution Receipts управляемого журнала: черновик, тест, публикация, откат",
     "Evolution Receipts from the managed ledger: draft, test, publication, rollback"),
    ("activity_center",
     "Журнал активности устройства",
     "Device activity log"),
]

EVOLUTION_CYCLE = [
    ("describe", "Описать желаемое изменение обычным языком",
     "Describe the desired change in plain language"),
    ("classify", "Определить, что меняется: знание, правило, способность или Shared Gene",
     "Classify what changes: knowledge, rule, capability, or Shared Gene"),
    ("scope", "Выбрать область: только этот агент / группа / все связанные агенты",
     "Choose the scope: this agent only / group / all connected agents"),
    ("draft", "Создать новую версию как черновик (в production не исполняется)",
     "Create a new version as a draft (it does not run in production)"),
    ("impact", "Показать затрагиваемые этапы, зависимости и ВСЕХ затронутых агентов",
     "Show affected steps, dependencies, and ALL affected agents"),
    ("compare", "Прогнать прежнюю и новую версии на одинаковых кейсах, сравнить решения/стоимость/ошибки",
     "Run old and new versions on identical cases and compare decisions, cost, and errors"),
    ("publish", "Опубликовать изменение (только неизменившийся черновик с успешным тестом)",
     "Publish the change (only an unchanged draft with a successful test)"),
    ("observe", "Наблюдать результат на реальных запусках",
     "Observe the result on real managed runs"),
    ("rollback", "Вернуть точную предыдущую версию",
     "Restore the exact previous version"),
]


def _provenance(cap):
    """Откуда пришёл элемент состояния: собственный агента или общий (влияет на класс)."""
    return "global" if cap.get("global") is True else "agent"


def build(doc):
    """Собирает структуру кабинета из паспорта. Ничего не выдумывает: только то, что заявлено."""
    report = check_report(doc)
    if not report["ready"]:
        raise ValueError("Agent Cabinet requires a valid Agent Passport")
    agent = doc.get("agent") or {}
    caps = [c for c in (doc.get("capabilities") or []) if isinstance(c, dict)]
    shared_genes = [g for g in (doc.get("shared_genes") or []) if isinstance(g, dict)]
    ops = doc.get("operations") or {}

    legacy_shared = [c for c in caps if _provenance(c) == "global"]
    writes = [c for c in caps if c.get("side_effects") in ("external", "physical")]
    needs_human = [c for c in caps if c.get("confirmation") == "always"]
    consumer_agent_id = agent.get("platform_agent_id")

    capability_genome = [{
        "element_type": "capability", "gene_id": None,
        "name": c.get("name"), "capability": c.get("name"), "version": c.get("version"),
        "autonomy": c.get("autonomy"), "provenance": _provenance(c),
        "side_effects": c.get("side_effects"), "confirmation": c.get("confirmation"),
        "expert": c.get("expert") or None, "shared_handler": c.get("cspl") or None,
        "rules": c.get("rules") or [], "concepts": c.get("concepts") or [],
        "permissions": c.get("permissions") or [], "targets": c.get("targets") or [],
        "rollback": c.get("rollback") or None, "evidence": c.get("evidence_schema") or None,
        "limits": [x for x in (c.get("limits") or []) if not is_blank(x)],
        "help_surface": c.get("help_surface") or None,
    } for c in caps]
    canonical_shared_genes = [{
        "element_type": g.get("kind"), "gene_id": g.get("gene_id"),
        "name": g.get("name"), "capability": None, "version": g.get("version"),
        "autonomy": None, "provenance": "global",
        "side_effects": None, "confirmation": None,
        "expert": None, "shared_handler": None, "rules": [], "concepts": [],
        "permissions": [], "targets": [], "rollback": None, "evidence": None,
        "limits": [], "help_surface": None,
        "consumer_agent_id": consumer_agent_id,
    } for g in shared_genes]

    passport = {
        "identity": {
            "name": agent.get("name"), "owner": agent.get("owner"),
            "platform_agent_id": consumer_agent_id,
            "platform_provider": agent.get("platform_provider") or None,
            "declared_instructions": agent.get("declared_instructions") or None,
            "business_goal": agent.get("business_goal"),
            "model_profile": agent.get("model_profile"),
            "active_version": agent.get("version"),
            "bundle_id": agent.get("immutable_bundle_id") or None,
            "dependency_lock": agent.get("dependency_lock_sha256") or None,
            "languages": agent.get("languages") or [],
            "data_classification": agent.get("data_classification") or None,
            "interfaces": agent.get("interfaces") or [],
            "hosting": agent.get("hosting_profile") or None,
        },
        # Agent Genome (NAMING.md): изменяемое содержание агента — не сырой список,
        # а элементы с происхождением, версиями и stable IDs. Canonical
        # Shared Genes идут отдельными element_type и считаются только по gene_id.
        "genome": capability_genome + canonical_shared_genes,
        "budgets": doc.get("budgets") or {},
        "operations": {"success_metric": ops.get("success_metric"),
                       "owner_on_call": ops.get("owner_on_call"),
                       "evidence_retention": ops.get("evidence_retention") or None},
        "attention": {
            "shared_genes": [{
                "gene_id": g.get("gene_id"), "kind": g.get("kind"),
                "name": g.get("name"), "version": g.get("version"),
                "provenance": "global", "consumer_agent_id": consumer_agent_id,
            } for g in shared_genes],
            # Старое capability.global остаётся видимым для миграции, но не
            # участвует в точном N потребителей Evolution Console.
            "legacy_global_capabilities": [c.get("name") for c in legacy_shared],
            "external_or_physical": [c.get("name") for c in writes],
            "human_required": [c.get("name") for c in needs_human],
        },
    }

    declared = {"steps": [{"capability": c.get("name"), "autonomy": c.get("autonomy"),
                           "side_effects": c.get("side_effects")} for c in caps]}

    actual = {
        "evidence_sources": [{"id": k, "what_ru": ru, "what_en": en}
                             for k, ru, en in EVIDENCE_SOURCES],
        "shown_ru": "маршруты последних управляемых запусков: какие правила сработали, "
                    "какие способности вызывались, где агент отклонился от заявленного пути",
        "shown_en": "routes from the latest managed runs: which rules fired, which capabilities "
                    "were called, and where the agent diverged from the declared path",
        "limits": PLATFORM_LIMITS,
    }

    evolution = {
        "cycle": [{"step": k, "what_ru": ru, "what_en": en}
                  for k, ru, en in EVOLUTION_CYCLE],
        "shared_change_guard": {
            "trigger": "изменение объекта с provenance=global",
            "must_show_ru": "список ВСЕХ затронутых агентов и выбор: локальная копия или изменение всего класса",
            "must_show_en": "the list of ALL affected agents and a choice: local copy or whole-class change",
            "candidates": [{
                "gene_id": g.get("gene_id"), "kind": g.get("kind"),
                "name": g.get("name"), "version": g.get("version"),
            } for g in shared_genes],
            "legacy_candidates": [c.get("name") for c in legacy_shared],
            # Буквальный вопрос пользователю: без него защита остаётся благим пожеланием.
            # N подставляется на живых данных (сколько агентов реально используют механизм).
            "prompt_ru": "Этот механизм используют ещё {N} агентов. Создать локальную версию только "
                         "для этого агента или изменить весь класс?",
            "prompt_en": "This mechanism is used by {N} more agents. Create a local version for this "
                         "agent only, or change the whole class?",
            "choices_ru": ["Создать локальную версию", "Изменить весь класс", "Отмена"],
            "choices_en": ["Create a local version", "Change the whole class", "Cancel"],
        },
        "ledger_ru": "тот же управляемый журнал версий, что в Evolution Console "
                     "(Agent Cabinet — его проекция по одному агенту, а не второй механизм версий)",
        "ledger_en": "the same managed version ledger as Evolution Console "
                     "(Agent Cabinet is its single-agent projection, not a second version mechanism)",
    }

    return {"schema": CABINET_SCHEMA, "passport": passport,
            "declared_behaviour": declared, "actual_behaviour": actual, "evolution": evolution}


def _markdown_text(value):
    """Escape untrusted Agent Passport text for HTML-capable Markdown renderers."""
    return html.escape(str(value if value not in (None, "") else "—"), quote=True).replace(
        "|", r"\|"
    ).replace("\r", " ").replace("\n", " ")


def as_markdown(cab):
    p = cab["passport"]; i = p["identity"]
    out = ["# Agent Cabinet — кабинет агента: %s" % _markdown_text(i.get("name")), ""]
    out += ["**Владелец:** %s · **Цель:** %s" %
            (_markdown_text(i.get("owner")), _markdown_text(i.get("business_goal"))),
            "**Platform Agent ID:** %s · **Активная версия:** %s · **Модель:** %s · **Языки:** %s" %
            (_markdown_text(i.get("platform_agent_id")), _markdown_text(i.get("active_version")),
             _markdown_text(i.get("model_profile")),
             ", ".join(_markdown_text(x) for x in (i.get("languages") or [])) or "—"), ""]
    out += ["## Agent Genome — геном агента (что определяет поведение)", "",
            "| Элемент | Тип | Stable ID | Версия | Откуда | Самостоятельность | Эффекты | Границ |",
            "|---|---|---|---|---|---|---|---|"]
    for s in p["genome"]:
        out.append("| %s | %s | %s | %s | %s | %s | %s | %d |" % (
            _markdown_text(s.get("name") or s.get("capability")),
            _markdown_text(s.get("element_type")),
            _markdown_text(s.get("gene_id")), _markdown_text(s.get("version")),
            "общий (влияет на класс)" if s["provenance"] == "global" else "только этот агент",
            _markdown_text(s.get("autonomy")),
            ("%s / %s" % (_markdown_text(s.get("side_effects")),
                          _markdown_text(s.get("confirmation"))))
            if s.get("side_effects") else "—",
            len(s.get("limits") or [])))
    att = p["attention"]
    out += ["", "## Требует внимания", ""]
    shared_labels = ["%s [%s]" % (_markdown_text(g.get("name")),
                                  _markdown_text(g.get("gene_id")))
                     for g in att["shared_genes"]]
    out += ["- Shared Genes — общие элементы (изменение затронет других агентов): %s"
            % (", ".join(shared_labels) or "нет")]
    out += ["- Legacy capability.global (не используется для точного N): %s"
            % (", ".join(_markdown_text(x) for x in att["legacy_global_capabilities"]) or "нет")]
    out += ["- Действия наружу или с техникой: %s"
            % (", ".join(_markdown_text(x) for x in att["external_or_physical"]) or "нет")]
    out += ["- Обязателен человек: %s"
            % (", ".join(_markdown_text(x) for x in att["human_required"]) or "нет")]
    out += ["", "## Как работает фактически — источники", ""]
    out += ["- " + s["what_ru"] for s in cab["actual_behaviour"]["evidence_sources"]]
    out += ["", "### Чего Agent Cabinet НЕ показывает (честные границы)", ""]
    out += ["- " + x for x in cab["actual_behaviour"]["limits"]["ru"]]
    out += ["", "## Evolution Loop — цикл управляемого изменения", ""]
    out += ["%d. %s" % (n, s["what_ru"]) for n, s in enumerate(cab["evolution"]["cycle"], 1)]
    return "\n".join(out) + "\n"


GOOD = {
    "agent": {"name": "Дебиторка 28 филиалов", "owner": "Анвар", "business_goal": "Еженедельная сводка просрочки",
              "model_profile": "qwen-3.7", "version": "1.2.0", "languages": ["ru", "en"],
              "platform_agent_id": "agent_qwen_receivables_20260726",
              "platform_provider": "alibaba",
              "declared_instructions": "Prepare a read-only receivables summary.",
              "immutable_bundle_id": "b-1", "data_classification": "внутренние"},
    "capabilities": [
        {"name": "Собрать сводку", "version": "1.2.0", "autonomy": "A2", "side_effects": "local",
         "confirmation": "conditional", "idempotency": "supported", "global": False,
         "rollback": "удалить отчёт", "evidence_schema": "run_receipt_v1",
         "limits": ["работает по выгрузке, не по живой 1С"], "help_surface": "кабинет → «? Как это работает»"},
        {"name": "Отправить письмо", "version": "1.0.0", "autonomy": "A2", "side_effects": "external",
         "confirmation": "always", "idempotency": "unsupported", "global": True,
         "rollback": "письмо остаётся черновиком", "evidence_schema": "mail_receipt_v1",
         "permissions": ["send_draft"], "rules": ["не слать без подтверждения"],
         "limits": ["не отправляет без человека"], "help_surface": "кабинет → «? Как это работает»"}],
    "shared_genes": [
        {"gene_id": "rule.receivables-policy", "kind": "rule",
         "name": "Receivables policy", "version": "2.1.0", "provenance": "global"},
    ],
    "budgets": {"max_duration_ms": 60000, "max_llm_tokens": 20000, "max_delegation_depth": 1, "max_external_actions": 1},
    "operations": {"success_metric": "сводка до 09:00 пн", "owner_on_call": "Анвар", "evidence_retention": "90d"},
}


def selftest():
    print("Самопроверка генератора кабинета:")
    ok = True
    report = check_report(GOOD)
    if not report["ready"]:
        ok = False; print("FAIL: эталонный паспорт не проходит стандарт:")
        [print("      - " + x["message_ru"]) for x in report["issues"]
         if x["severity"] == "error"]
    else:
        print("PASS: эталонный паспорт проходит стандарт")
    cab = build(GOOD)
    checks = [
        ("Agent Cabinet сохраняет схему v1.1", cab.get("schema") == CABINET_SCHEMA),
        ("Agent Passport связан со stable platform agent ID",
         cab["passport"]["identity"]["platform_agent_id"]
         == "agent_qwen_receivables_20260726"),
        ("live provider/instructions сохраняются как декларация Agent Passport",
         cab["passport"]["identity"]["platform_provider"] == "alibaba"
         and cab["passport"]["identity"]["declared_instructions"]
         == "Prepare a read-only receivables summary."),
        ("паспорт содержит активную версию", cab["passport"]["identity"]["active_version"] == "1.2.0"),
        ("Agent Genome: 2 способности + 1 canonical Shared Gene",
         len(cab["passport"]["genome"]) == 3),
        ("canonical Shared Gene имеет stable ID и consumer",
         cab["passport"]["genome"][2]["gene_id"] == "rule.receivables-policy"
         and cab["passport"]["genome"][2]["consumer_agent_id"]
         == "agent_qwen_receivables_20260726"),
        ("Shared Gene попал в «требует внимания»",
         cab["passport"]["attention"]["shared_genes"][0]["gene_id"]
         == "rule.receivables-policy"),
        ("legacy capability.global сохранён отдельно и не подменяет canonical Shared Gene",
         cab["passport"]["attention"]["legacy_global_capabilities"] == ["Отправить письмо"]),
        ("действие наружу отмечено", cab["passport"]["attention"]["external_or_physical"] == ["Отправить письмо"]),
        ("обязателен человек отмечен", cab["passport"]["attention"]["human_required"] == ["Отправить письмо"]),
        ("заявленное поведение отделено от фактического",
         "declared_behaviour" in cab and "actual_behaviour" in cab),
        ("границы «фактически» названы на двух языках",
         len(cab["actual_behaviour"]["limits"]["ru"]) >= 4 and len(cab["actual_behaviour"]["limits"]["en"]) >= 4),
        ("цикл эволюции полный (9 шагов)", len(cab["evolution"]["cycle"]) == 9),
        ("защита от массовой поломки перечисляет canonical Shared Gene по ID",
         cab["evolution"]["shared_change_guard"]["candidates"][0]["gene_id"]
         == "rule.receivables-policy"),
        ("Agent Cabinet — проекция общего журнала Evolution Console",
         "Evolution Console" in cab["evolution"]["ledger_ru"]),
        ("защита задаёт буквальный вопрос с числом агентов",
         "{N}" in cab["evolution"]["shared_change_guard"]["prompt_ru"]
         and "{N}" in cab["evolution"]["shared_change_guard"]["prompt_en"]
         and len(cab["evolution"]["shared_change_guard"]["choices_ru"]) == 3),
        ("markdown-вид собирается",
         "Agent Cabinet — кабинет агента: Дебиторка 28 филиалов" in as_markdown(cab)),
    ]
    for label, cond in checks:
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond

    legacy = json.loads(json.dumps(GOOD))
    legacy.pop("shared_genes")
    legacy_cab = build(legacy)
    legacy_ok = (
        legacy_cab["schema"] == CABINET_SCHEMA
        and len(legacy_cab["passport"]["genome"]) == 2
        and legacy_cab["passport"]["attention"]["shared_genes"] == []
        and legacy_cab["passport"]["attention"]["legacy_global_capabilities"]
        == ["Отправить письмо"]
    )
    print(("PASS: " if legacy_ok else "FAIL: ") +
          "Agent Passport без shared_genes сохраняет backward-compatible v1.1 output")
    ok = ok and legacy_ok

    unsafe = json.loads(json.dumps(GOOD))
    unsafe["agent"]["name"] = "<img src=x onerror=alert(1)>"
    unsafe_markdown = as_markdown(build(unsafe))
    markdown_safe = (
        "<img src=x onerror=alert(1)>" not in unsafe_markdown
        and "&lt;img src=x onerror=alert(1)&gt;" in unsafe_markdown
    )
    print(("PASS: " if markdown_safe else "FAIL: ") +
          "markdown Agent Cabinet экранирует untrusted Agent Passport text")
    ok = ok and markdown_safe

    # негативный: паспорт без границ не даёт собрать кабинет
    bad = json.loads(json.dumps(GOOD)); bad["capabilities"][0]["limits"] = []
    rejected = not check_report(bad)["ready"]
    try:
        build(bad)
    except ValueError:
        rejected = rejected and True
    else:
        rejected = False
    print(("PASS: " if rejected else "FAIL: ") +
          "паспорт без границ не проходит единый checker и Agent Cabinet не собирается")
    ok = ok and rejected
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    args = [a for a in argv if not a.startswith("-")]
    if len(args) != 1:
        print("Как пользоваться:")
        print("  python3 build_agent_cabinet.py путь/к/паспорту.yaml [--markdown]")
        print("  python3 build_agent_cabinet.py --selftest")
        return 2
    doc = load_passport(args[0])
    if not isinstance(doc, dict) or "agent" not in doc:
        print("ОШИБКА: внутри файла не паспорт агента"); return 2
    report = check_report(doc)
    errors = [x for x in report["issues"] if x["severity"] == "error"]
    warns = [x for x in report["issues"] if x["severity"] == "warning"]
    if not report["ready"]:
        print("Кабинет НЕ собран: паспорт не проходит стандарт. Сначала исправь:")
        for issue in errors:
            print("  ОШИБКА: " + issue["message_ru"])
        print("\nПодсказка: python3 tools/check_agent_passport.py " + args[0])
        return 1
    for issue in warns:
        print("ВНИМАНИЕ: " + issue["message_ru"], file=sys.stderr)
    cab = build(doc)
    print(as_markdown(cab) if "--markdown" in argv else json.dumps(cab, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
