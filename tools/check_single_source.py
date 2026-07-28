#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт единственного источника: правило не должно жить в двух местах.

Повод — не теория. 28.07.2026 из паспортов сняли 30 полей, и через час выяснилось, что
`AGENT_ARCHITECTURE.md` §9 продолжает требовать десять снятых. Документ разошёлся с шаблоном
за час, молча, и никакой ошибки при этом не возникло. Это тот же класс, что расхождение
описаний эксперта с аккаунтом и пустой реестр при целых данных: **одна вещь, две копии,
никто не знает, какая права.**

Что проверяем:

1. **Снятые поля нигде не воскресают.** Ни один документ и ни один шаблон не должен снова
   требовать поле, которое мы удалили как мёртвое.
2. **Поля паспорта объявляются только в `templates/`.** Документ, который перечисляет их
   заново, обязательно разъедется с шаблоном — вопрос лишь во времени.

Осознанное упоминание в разборе («здесь было поле X, мы его сняли») помечается в той же строке:
`canon-ok: причина`.

Как пользоваться:
  python3 check_single_source.py            # весь репозиторий стандартов
  python3 check_single_source.py --json
  python3 check_single_source.py --selftest

Коды выхода: 0 — источник один, 1 — расхождение, 2 — проверить не удалось.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Удалены 28.07.2026 как мёртвые: их не читал ни продукт, ни один гейт.
REMOVED_FIELDS = ("alerts", "approval_binding", "completeness_contract", "data_fields",
                  "data_residency", "input_schema", "output_schema", "reconciliation")
# Поля, объявлять которые вправе только шаблон. Список намеренно короткий: это те, вокруг
# которых уже случалось расхождение.
TEMPLATE_ONLY_FIELDS = ("platform_agent_id", "hosting_profile", "help_surface",
                        "max_delegation_depth", "secret_ref", "personal_data")
CANON_OK_RE = re.compile(r"canon-ok:\s*\S+")
# Разбор истории имеет право называть снятое поле — там это факт, а не требование.
HISTORY_FILES = {"CHANGELOG.md"}


def _looks_like_declaration(line):
    """Объявление поля — это `имя:` в начале строки или в отступе, а не упоминание в тексте."""
    return bool(re.match(r"^\s*[-`]?\s*[a-z_]{3,}\s*:", line))


def check_repo(root=ROOT):
    issues = []
    docs = sorted(glob.glob(os.path.join(root, "*.md")) +
                  glob.glob(os.path.join(root, "checklists", "*.md")))
    templates = sorted(glob.glob(os.path.join(root, "templates", "*.yaml")))

    for path in docs + templates:
        name = os.path.basename(path)
        is_template = os.sep + "templates" + os.sep in path
        for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            if CANON_OK_RE.search(line) or name in HISTORY_FILES:
                continue
            for field in REMOVED_FIELDS:
                if re.search(r"\b%s\b" % field, line) and _looks_like_declaration(line):
                    issues.append({
                        "code": "REMOVED_FIELD_RESURRECTED", "severity": "error",
                        "path": "%s:%d" % (name, n), "field": field,
                        "message_ru": "поле «%s» снято 28.07 как мёртвое, а здесь объявлено "
                                      "снова — вернётся и требование его заполнять" % field,
                        "message_en": "field %r was removed on 28.07 as dead, but is declared "
                                      "here again — the obligation to fill it would return" % field,
                    })
            if is_template:
                continue
            for field in TEMPLATE_ONLY_FIELDS:
                if re.search(r"\b%s\b" % field, line) and _looks_like_declaration(line):
                    issues.append({
                        "code": "FIELD_DECLARED_OUTSIDE_TEMPLATE", "severity": "error",
                        "path": "%s:%d" % (name, n), "field": field,
                        "message_ru": "поле «%s» объявлено вне templates/. Одно правило в двух "
                                      "местах разъезжается молча — оставь объявление шаблону, "
                                      "здесь только ссылайся" % field,
                        "message_en": "field %r is declared outside templates/. One rule in two "
                                      "places diverges silently — leave the declaration to the "
                                      "template and only refer to it here" % field,
                    })
    return {"documents": len(docs), "templates": len(templates), "issues": issues,
            "ready": not issues}


def selftest():
    print("Самопроверка единственного источника:")
    ok = True
    cases = [
        ("объявление снятого поля — поймано", "    input_schema: {}", False, "REMOVED_FIELD_RESURRECTED"),
        ("упоминание в тексте не считается объявлением",
         "Раньше требовали input_schema, теперь нет.", False, None),
        ("объявление вне шаблона — поймано", "  hosting_profile: \"\"", False,
         "FIELD_DECLARED_OUTSIDE_TEMPLATE"),
        ("в шаблоне объявлять можно", "  hosting_profile: \"\"", True, None),
        ("осознанная пометка снимает вопрос",
         "  input_schema: {}   # canon-ok: пример из разбора", False, None),
    ]
    import tempfile
    for label, line, in_template, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            sub = "templates" if in_template else ""
            d = os.path.join(tmp, sub) if sub else tmp
            os.makedirs(d, exist_ok=True)
            fn = "t.yaml" if in_template else "DOC.md"
            open(os.path.join(d, fn), "w", encoding="utf-8").write(line + "\n")
            codes = {i["code"] for i in check_repo(tmp)["issues"]}
            got = (expected in codes) if expected else (not codes)
            print(("PASS: " if got else "FAIL: ") + label)
            ok = ok and got

    for i in check_repo(ROOT)["issues"]:
        if not i.get("message_ru") or not i.get("message_en"):
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
    report = check_repo()
    if "--json" in argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    for i in report["issues"]:
        print("ОШИБКА: %s — %s" % (i["path"], i["message_ru"]))
    print("ИТОГ: " + ("источник один (документов %d, шаблонов %d)"
                      % (report["documents"], report["templates"]) if report["ready"]
                      else "расхождений %d — исправь выше" % len(report["issues"])))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
