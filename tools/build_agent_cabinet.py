#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Базовая технология кабинета агента: КАБИНЕТ СОБИРАЕТСЯ ИЗ ПАСПОРТА, а не пишется руками.

Замысел (Анвар, 26.07.2026): у каждого агента должен быть свой кабинет — «Паспорт» (что это за
агент и как он работает сейчас) и «Эволюция» (изменение через черновик → тест → публикацию →
откат). Чтобы это не делали руками для каждого агента, кабинет ГЕНЕРИРУЕТСЯ из паспорта агента,
который уже обязателен по стандарту и уже проверяется `check_agent_passport.py`.

Путь агента получается такой:
    заполнил паспорт → проверялка пропустила → кабинет появился сам → агент виден в общем центре

Как пользоваться:
  python3 build_agent_cabinet.py мой_агент.yaml            → кабинет в JSON (для интерфейса)
  python3 build_agent_cabinet.py мой_агент.yaml --markdown → человекочитаемый вид
  python3 build_agent_cabinet.py --selftest                → самопроверка без файлов

Коды выхода: 0 — кабинет собран, 1 — паспорт не проходит стандарт (кабинет не собираем), 2 — файл не прочитан.

ЧЕСТНОСТЬ ВСТРОЕНА: раздел «Как работает фактически» перечисляет ТОЛЬКО те источники доказательств,
которые реально есть, и рядом — границы (чего мы не видим). Кабинет, обещающий полную картину без
неё, — это ровно та ложь, против которой задумано разделение «заявленное / фактическое».
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import check, load_passport, is_blank   # единый источник правил стандарта

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
    ("run_history", "История прогонов процессов (что запускалось, когда, с каким результатом)"),
    ("upc_steps", "Пошаговые журналы процесса: какие шаги выполнялись и что вернули"),
    ("ledger_receipts", "Квитанции управляемого журнала версий: черновик, тест, публикация, откат"),
    ("activity_center", "Журнал активности устройства"),
]

EVOLUTION_CYCLE = [
    ("describe", "Описать желаемое изменение обычным языком"),
    ("classify", "Определить, что меняется: знание, правило, способность или общий механизм"),
    ("scope", "Выбрать область: только этот агент / группа / все связанные агенты"),
    ("draft", "Создать новую версию как черновик (в production не исполняется)"),
    ("impact", "Показать затрагиваемые этапы, зависимости и ВСЕХ затронутых агентов"),
    ("compare", "Прогнать прежнюю и новую версии на одинаковых кейсах, сравнить решения/стоимость/ошибки"),
    ("publish", "Опубликовать изменение (только неизменившийся черновик с успешным тестом)"),
    ("observe", "Наблюдать результат на реальных запусках"),
    ("rollback", "Вернуть точную предыдущую версию"),
]


def _provenance(cap):
    """Откуда пришёл элемент состояния: собственный агента или общий (влияет на класс)."""
    return "global" if cap.get("global") is True else "agent"


def build(doc):
    """Собирает структуру кабинета из паспорта. Ничего не выдумывает: только то, что заявлено."""
    agent = doc.get("agent") or {}
    caps = [c for c in (doc.get("capabilities") or []) if isinstance(c, dict)]
    ops = doc.get("operations") or {}

    shared = [c for c in caps if _provenance(c) == "global"]
    writes = [c for c in caps if c.get("side_effects") in ("external", "physical")]
    needs_human = [c for c in caps if c.get("confirmation") == "always"]

    passport = {
        "identity": {
            "name": agent.get("name"), "owner": agent.get("owner"),
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
        # Эффективное состояние: не сырой список, а способности с происхождением и влиянием
        "effective_state": [{
            "capability": c.get("name"), "version": c.get("version"),
            "autonomy": c.get("autonomy"), "provenance": _provenance(c),
            "side_effects": c.get("side_effects"), "confirmation": c.get("confirmation"),
            "expert": c.get("expert") or None, "shared_handler": c.get("cspl") or None,
            "rules": c.get("rules") or [], "concepts": c.get("concepts") or [],
            "permissions": c.get("permissions") or [], "targets": c.get("targets") or [],
            "rollback": c.get("rollback") or None, "evidence": c.get("evidence_schema") or None,
            "limits": [x for x in (c.get("limits") or []) if not is_blank(x)],
            "help_surface": c.get("help_surface") or None,
        } for c in caps],
        "budgets": doc.get("budgets") or {},
        "operations": {"success_metric": ops.get("success_metric"),
                       "owner_on_call": ops.get("owner_on_call"),
                       "evidence_retention": ops.get("evidence_retention") or None},
        "attention": {
            "shared_objects": [c.get("name") for c in shared],
            "external_or_physical": [c.get("name") for c in writes],
            "human_required": [c.get("name") for c in needs_human],
        },
    }

    declared = {"steps": [{"capability": c.get("name"), "autonomy": c.get("autonomy"),
                           "side_effects": c.get("side_effects")} for c in caps]}

    actual = {
        "evidence_sources": [{"id": k, "what": v} for k, v in EVIDENCE_SOURCES],
        "shown": "маршруты последних управляемых запусков: какие правила сработали, "
                 "какие способности вызывались, где агент отклонился от заявленного пути",
        "limits": PLATFORM_LIMITS,
    }

    evolution = {
        "cycle": [{"step": k, "what": v} for k, v in EVOLUTION_CYCLE],
        "shared_change_guard": {
            "trigger": "изменение объекта с provenance=global",
            "must_show": "список ВСЕХ затронутых агентов и выбор: локальная копия или изменение всего класса",
            "candidates": [c.get("name") for c in shared],
            # Буквальный вопрос пользователю: без него защита остаётся благим пожеланием.
            # N подставляется на живых данных (сколько агентов реально используют механизм).
            "prompt_ru": "Этот механизм используют ещё {N} агентов. Создать локальную версию только "
                         "для этого агента или изменить весь класс?",
            "prompt_en": "This mechanism is used by {N} more agents. Create a local version for this "
                         "agent only, or change the whole class?",
            "choices_ru": ["Создать локальную версию", "Изменить весь класс", "Отмена"],
            "choices_en": ["Create a local version", "Change the whole class", "Cancel"],
        },
        "ledger": "тот же управляемый журнал версий, что в общем центре управления агентами "
                  "(кабинет — его проекция по одному агенту, а не второй механизм версий)",
    }

    return {"schema": "extella.agent_cabinet.v1", "passport": passport,
            "declared_behaviour": declared, "actual_behaviour": actual, "evolution": evolution}


def as_markdown(cab):
    p = cab["passport"]; i = p["identity"]
    out = ["# Кабинет агента: %s" % (i.get("name") or "—"), ""]
    out += ["**Владелец:** %s · **Цель:** %s" % (i.get("owner") or "—", i.get("business_goal") or "—"),
            "**Активная версия:** %s · **Модель:** %s · **Языки:** %s" %
            (i.get("active_version") or "—", i.get("model_profile") or "—", ", ".join(i.get("languages") or []) or "—"), ""]
    out += ["## Эффективное состояние", "", "| Способность | Версия | Самостоятельность | Откуда | Эффекты | Подтверждение | Границ |",
            "|---|---|---|---|---|---|---|"]
    for s in p["effective_state"]:
        out.append("| %s | %s | %s | %s | %s | %s | %d |" % (
            s["capability"], s["version"], s["autonomy"],
            "общий (влияет на класс)" if s["provenance"] == "global" else "только этот агент",
            s["side_effects"], s["confirmation"], len(s["limits"])))
    att = p["attention"]
    out += ["", "## Требует внимания", ""]
    out += ["- Общие объекты (изменение затронет другие агенты): %s" % (", ".join(att["shared_objects"]) or "нет")]
    out += ["- Действия наружу или с техникой: %s" % (", ".join(att["external_or_physical"]) or "нет")]
    out += ["- Обязателен человек: %s" % (", ".join(att["human_required"]) or "нет")]
    out += ["", "## Как работает фактически — источники", ""]
    out += ["- " + s["what"] for s in cab["actual_behaviour"]["evidence_sources"]]
    out += ["", "### Чего кабинет НЕ показывает (честные границы)", ""]
    out += ["- " + x for x in cab["actual_behaviour"]["limits"]["ru"]]
    out += ["", "## Эволюция — цикл изменения", ""]
    out += ["%d. %s" % (n, s["what"]) for n, s in enumerate(cab["evolution"]["cycle"], 1)]
    return "\n".join(out) + "\n"


GOOD = {
    "agent": {"name": "Дебиторка 28 филиалов", "owner": "Анвар", "business_goal": "Еженедельная сводка просрочки",
              "model_profile": "qwen-3.7", "version": "1.2.0", "languages": ["ru", "en"],
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
    "budgets": {"max_duration_ms": 60000, "max_llm_tokens": 20000, "max_delegation_depth": 1, "max_external_actions": 1},
    "operations": {"success_metric": "сводка до 09:00 пн", "owner_on_call": "Анвар", "evidence_retention": "90d"},
}


def selftest():
    print("Самопроверка генератора кабинета:")
    ok = True
    errors, _ = check(GOOD)
    if errors:
        ok = False; print("FAIL: эталонный паспорт не проходит стандарт:"); [print("      - " + e) for e in errors]
    else:
        print("PASS: эталонный паспорт проходит стандарт")
    cab = build(GOOD)
    checks = [
        ("кабинет собран по схеме v1", cab.get("schema") == "extella.agent_cabinet.v1"),
        ("паспорт содержит активную версию", cab["passport"]["identity"]["active_version"] == "1.2.0"),
        ("эффективное состояние: 2 способности", len(cab["passport"]["effective_state"]) == 2),
        ("провенанс различает общий объект", [s["provenance"] for s in cab["passport"]["effective_state"]] == ["agent", "global"]),
        ("общий объект попал в «требует внимания»", cab["passport"]["attention"]["shared_objects"] == ["Отправить письмо"]),
        ("действие наружу отмечено", cab["passport"]["attention"]["external_or_physical"] == ["Отправить письмо"]),
        ("обязателен человек отмечен", cab["passport"]["attention"]["human_required"] == ["Отправить письмо"]),
        ("заявленное поведение отделено от фактического",
         "declared_behaviour" in cab and "actual_behaviour" in cab),
        ("границы «фактически» названы на двух языках",
         len(cab["actual_behaviour"]["limits"]["ru"]) >= 4 and len(cab["actual_behaviour"]["limits"]["en"]) >= 4),
        ("цикл эволюции полный (9 шагов)", len(cab["evolution"]["cycle"]) == 9),
        ("защита от массовой поломки перечисляет общие объекты",
         cab["evolution"]["shared_change_guard"]["candidates"] == ["Отправить письмо"]),
        ("кабинет — проекция общего журнала версий", "проекция" in cab["evolution"]["ledger"]),
        ("защита задаёт буквальный вопрос с числом агентов",
         "{N}" in cab["evolution"]["shared_change_guard"]["prompt_ru"]
         and "{N}" in cab["evolution"]["shared_change_guard"]["prompt_en"]
         and len(cab["evolution"]["shared_change_guard"]["choices_ru"]) == 3),
        ("markdown-вид собирается", "Кабинет агента: Дебиторка 28 филиалов" in as_markdown(cab)),
    ]
    for label, cond in checks:
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond
    # негативный: паспорт без границ не даёт собрать кабинет
    bad = json.loads(json.dumps(GOOD)); bad["capabilities"][0]["limits"] = []
    if check(bad)[0]:
        print("PASS: паспорт без границ не проходит стандарт — кабинет не собирается")
    else:
        ok = False; print("FAIL: паспорт без границ прошёл — так нельзя")
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
    errors, warns = check(doc)
    if errors:
        print("Кабинет НЕ собран: паспорт не проходит стандарт. Сначала исправь:")
        for e in errors:
            print("  ОШИБКА: " + e)
        print("\nПодсказка: python3 tools/check_agent_passport.py " + args[0])
        return 1
    for w in warns:
        print("ВНИМАНИЕ: " + w, file=sys.stderr)
    cab = build(doc)
    print(as_markdown(cab) if "--markdown" in argv else json.dumps(cab, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
