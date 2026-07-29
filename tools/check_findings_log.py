#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт: нашёл системную ошибку — записал. Ноль и «мы не смотрели» это разные вещи.

ЗАЧЕМ. Строя агента, почти всегда находишь чужие дефекты. Молча пройти мимо — оставить
их следующему, и он потратит те же часы заново. За один день 29.07.2026 так нашлись:

  • канон называл агента с 45 инструментами «образцом урезанных прав, ни одного опасного»
    — а у него `delete_agent`, `delete_profile` и `token_generate`;
  • обязательный тест приватности жил в scratchpad и исчез вместе с сессией — прогнать
    его перед деплоем было нечем;
  • ДВА теста закрепляли нарушение канона вместо канона: «Ваши автоматизации» и наличие
    собственного переключателя языка;
  • `preflight_ui.sh` был красным на main и держал деплой всем, а не только автору правки.

Ни одна из этих находок не была задачей. Все они всплыли по дороге.

ПОЧЕМУ ЭТО ГЕЙТ, А НЕ ПРОСТО ПРАВИЛО. «Записывай находки» без проверки возвращается через
неделю — это наш многократно проверенный класс. Но проверить машинно можно не полноту
(её никто не измерит), а **факт наличия ответа**:

    файла нет          → никто не смотрел          → ОШИБКА
    findings: []       → посмотрели, не нашли      → ГОДНО
    список с находками → посмотрели, нашли         → ГОДНО, если поля заполнены

Пустой список обязателен и валиден. В этом весь смысл: ноль это утверждение, а не
отсутствие утверждения. Тот же принцип, по которому bundle стандартов честно отдаёт
пустой список паспортов вместо ошибки.

Формат `evidence/findings.yaml`:

    findings:
      - what: "канон называет агента образцом урезанных прав"
        where: "CLAUDE.md, живой agent/get"
        impact: "агент-эталон может удалить другого агента аккаунта"
        severity: blocker      # blocker | major | minor

Как пользоваться:
  python3 check_findings_log.py evidence/findings.yaml
  python3 check_findings_log.py --selftest

Коды выхода: 0 — годно, 1 — есть нарушения.
"""
import os
import sys

SEVERITIES = ("blocker", "major", "minor")
REQUIRED = ("what", "where", "impact", "severity")


def check(doc, exists=True):
    """Возвращает список проблем. doc = разобранный YAML или None."""
    problems = []
    if not exists:
        return ["файла находок нет — значит никто не смотрел. Пустой список тоже ответ: "
                "положи evidence/findings.yaml с `findings: []`"]
    if not isinstance(doc, dict) or "findings" not in doc:
        return ["в файле находок нет ключа `findings` — непонятно, смотрели или нет"]
    items = doc.get("findings")
    if items is None:
        items = []
    if not isinstance(items, list):
        return ["`findings` обязан быть списком (пустой список — валидный ответ)"]
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append("находка %d — не запись со полями" % i)
            continue
        for field in REQUIRED:
            if not str(it.get(field) or "").strip():
                problems.append("находка %d: пустое поле `%s` — находка без него "
                                "бесполезна следующему" % (i, field))
        sev = str(it.get("severity") or "").strip()
        if sev and sev not in SEVERITIES:
            problems.append("находка %d: severity «%s» — допустимо %s"
                            % (i, sev, " | ".join(SEVERITIES)))
    return problems


def selftest():
    print("Самопроверка гейта находок:")
    ok = True

    def case(label, doc, exists, expect_problem):
        nonlocal ok
        got = bool(check(doc, exists))
        good = got == expect_problem
        print(("PASS: " if good else "FAIL: ") + label)
        ok = ok and good

    full = {"findings": [{"what": "канон врёт про права", "where": "CLAUDE.md",
                          "impact": "агент может удалить агента", "severity": "blocker"}]}
    case("файла нет — поймано (никто не смотрел)", None, False, True)
    case("пустой список — ГОДЕН, это честный ноль", {"findings": []}, True, False)
    case("заполненная находка проходит", full, True, False)
    case("нет ключа findings — поймано", {"other": 1}, True, True)
    case("findings не список — поймано", {"findings": "нет"}, True, True)
    case("находка без impact — поймано",
         {"findings": [{"what": "a", "where": "b", "impact": "", "severity": "minor"}]}, True, True)
    case("чужая severity — поймано",
         {"findings": [{"what": "a", "where": "b", "impact": "c", "severity": "критично"}]}, True, True)
    case("findings: null равен пустому списку", {"findings": None}, True, False)

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = [a for a in argv if not a.startswith("-")]
    path = paths[0] if paths else "evidence/findings.yaml"
    exists = os.path.exists(path)
    doc = None
    if exists:
        try:
            import yaml
        except ImportError:
            print("ОШИБКА: нужен PyYAML, чтобы прочитать %s" % path)
            return 1
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    problems = check(doc, exists)
    for p in problems:
        print("ОШИБКА: " + p)
    if problems:
        return 1
    n = len((doc or {}).get("findings") or [])
    print("находки записаны: %d %s" % (n, "(честный ноль — смотрели, не нашли)" if not n else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
