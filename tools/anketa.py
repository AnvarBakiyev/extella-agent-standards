#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Анкета компании: работы людей и контур компании, файлом по схеме.

ЗАЧЕМ. Глава APP_FROM_MODULES.md (§3) велит разложить задачу на потребности по одной фразе
и по каждой спросить поиск. Откуда берутся эти фразы, стандарт не говорил: их помнил человек
со встречи, и после встречи они терялись. Анкета кладёт их в файл. У каждой потребности есть
место под владельца процесса, частоту, вход, форму результата и то, что нельзя выносить
с машины.

Первая встреча заполняет малую часть мест. Пустое место не считается ошибкой: это вопрос на
следующую встречу. Проверка показывает пустые места списком и не просит модель их додумать.

Схема extella.anketa.v1. Ключи латиницей, значения на языке встречи, как в app.json
и паспортах. Анкета с данными живой компании хранится в репозитории этой компании,
а не в стандартах: стандарты публичны.

Запуск:
  python3 tools/anketa.py --пустая                      пустой бланк
  python3 tools/anketa.py --пример                      вымышленный заполненный образец
  python3 tools/anketa.py --проверить файл.json         ошибки и пустые места
  python3 tools/anketa.py --проверить файл.json --json  то же для машины
  python3 tools/anketa.py --потребности файл.json       фразы для wz_capability_find
  python3 tools/anketa.py --промпт                      задание модели заполнить анкету
  python3 tools/anketa.py --selftest

Коды выхода: 0 — анкета годится, пустые места допустимы; 1 — есть ошибки; 2 — неверный запуск.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import формы  # noqa: E402  словарь пяти форм живёт в одном месте

SCHEMA = "extella.anketa.v1"
HOSTING = ("saas", "on_prem", "unknown")

# Поле, описание по-русски, описание по-английски. Одна таблица кормит бланк, проверку
# и промпт, поэтому промпт не может разойтись со схемой.
CONTOUR_FIELDS = (
    ("hosting", "где будет стоять платформа: saas, on_prem или unknown",
     "where the platform will run: saas, on_prem or unknown"),
    ("data_must_stay", "какие данные не выходят за периметр компании",
     "which data must not leave the company perimeter"),
    ("existing_systems", "какие системы уже работают: 1С, Bitrix24, Teams, почта",
     "which systems already run: 1C, Bitrix24, Teams, mail"),
    ("logging", "куда уходят журналы действий, например в SIEM",
     "where action logs must go, for example a SIEM"),
    ("os", "операционные системы рабочих мест и серверов",
     "operating systems of workstations and servers"),
    ("decision_maker", "кто в компании решает о запуске",
     "who in the company decides on the launch"),
)
LIST_FIELDS = {"data_must_stay", "existing_systems", "os"}

WORK_FIELDS = (
    ("need", "что нужно, одной фразой", "what is needed, in one phrase"),
    ("department", "подразделение", "department"),
    ("owner", "владелец процесса: кто отвечает за результат",
     "process owner: who is accountable for the result"),
    ("frequency", "как часто делается работа", "how often the work is done"),
    ("volume", "объём за период: документы, заявки, записи",
     "volume per period: documents, requests, records"),
    ("input", "откуда приходят данные", "where the data comes from"),
    ("output_form", "форма результата: list, number, steps, links или document",
     "result form: list, number, steps, links or document"),
    ("must_not_leave", "что из этой работы нельзя выносить с машины",
     "what from this work must not leave the machine"),
    ("who_decides", "кто принимает решение по результату", "who decides on the result"),
    ("pain_today", "что сегодня ломается или отнимает время",
     "what breaks or takes time today"),
    ("source", "где это сказано: таймкод, цитата или страница",
     "where it was said: timecode, quote or page"),
)

# «Одна фраза» проверяется грубо: точка с запятой или больше 16 слов. Союз «и» не ловится
# намеренно: «счета и накладные» остаются одной потребностью, а ложная тревога в проверке
# дороже пропуска. Разбирать фразу точнее стоит, только если грубый признак начнёт пропускать
# составные задачи.
NEED_MAX_WORDS = 16


def _blank(v):
    if v is None:
        return True
    if isinstance(v, list):
        return all(_blank(x) for x in v)
    if isinstance(v, str):
        return not v.strip()
    return False


def _issue(bucket, code, path, ru, en):
    bucket.append({"code": code, "path": path, "message_ru": ru, "message_en": en})


def blank_form():
    """Пустой бланк: все поля на месте, чтобы их пустота была видна глазами."""
    return {
        "schema": SCHEMA,
        "company": {"name": "", "industry": "", "size": ""},
        "filled_from": {"kind": "", "ref": "", "date": ""},
        "contour": {f: ([] if f in LIST_FIELDS else "") for f, _, _ in CONTOUR_FIELDS},
        "works": [dict({"id": "w1"}, **{f: "" for f, _, _ in WORK_FIELDS})],
    }


def example():
    """Вымышленная компания. Данные живых компаний сюда не попадают: репозиторий публичный."""
    doc = blank_form()
    doc["company"] = {"name": "ТОО «Образец»", "industry": "оптовая продажа стройматериалов",
                      "size": "120 сотрудников"}
    doc["filled_from"] = {"kind": "call", "ref": "вымышленная встреча для образца",
                          "date": "2026-09-14"}
    doc["contour"].update({
        "hosting": "on_prem",
        "data_must_stay": ["реквизиты контрагентов", "закупочные цены"],
        "existing_systems": ["1С:Бухгалтерия", "Bitrix24"],
        "os": ["Windows"],
    })
    w = {f: "" for f, _, _ in WORK_FIELDS}
    doc["works"] = [
        dict(w, id="w1", need="распознавать входящие счета из сканов", department="бухгалтерия",
             owner="главный бухгалтер", frequency="ежедневно", volume="около 40 счетов в день",
             input="почта и сканер", output_form="list",
             must_not_leave="реквизиты контрагентов", who_decides="бухгалтер",
             pain_today="реквизиты перепечатываются руками", source="12:40"),
        dict(w, id="w2", need="сверять договоры поставки с шаблоном компании",
             department="юридический отдел", output_form="document",
             pain_today="правки контрагента ищутся глазами", source="31:05"),
        dict(w, id="w3", need="считать остатки на складах к утру", department="склад",
             output_form="number", source="44:10"),
    ]
    return doc


def check(doc):
    """Ошибки мешают работать с анкетой. Пустые места не мешают: это вопросы на встречу."""
    errors, warnings, empty = [], [], []
    if not isinstance(doc, dict):
        _issue(errors, "ANKETA_NOT_OBJECT", "", "анкета должна быть объектом JSON",
               "the questionnaire must be a JSON object")
        return {"ready": False, "errors": errors, "warnings": warnings, "empty": empty}

    if doc.get("schema") != SCHEMA:
        _issue(errors, "ANKETA_SCHEMA", "schema",
               "схема должна быть %s: другая версия читается иначе" % SCHEMA,
               "schema must be %s: another version reads differently" % SCHEMA)
    company = doc.get("company") if isinstance(doc.get("company"), dict) else {}
    if _blank(company.get("name")):
        _issue(errors, "ANKETA_COMPANY_NAME_REQUIRED", "company.name",
               "не названа компания: анкету не с чем связать",
               "the company is not named: the questionnaire links to nothing")

    contour = doc.get("contour") if isinstance(doc.get("contour"), dict) else {}
    for f, ru, en in CONTOUR_FIELDS:
        v = contour.get(f)
        if _blank(v):
            empty.append({"path": "contour." + f, "question_ru": ru, "question_en": en})
        elif f in LIST_FIELDS and not isinstance(v, list):
            _issue(errors, "ANKETA_CONTOUR_LIST", "contour." + f,
                   "поле должно быть списком строк", "the field must be a list of strings")
    hosting = str(contour.get("hosting") or "").strip().lower()
    if hosting and hosting not in HOSTING:
        _issue(errors, "ANKETA_HOSTING_INVALID", "contour.hosting",
               "размещение «%s» неизвестно, допустимо: %s" % (hosting, ", ".join(HOSTING)),
               "hosting %r is unknown, allowed: %s" % (hosting, ", ".join(HOSTING)))

    works = doc.get("works")
    if not isinstance(works, list) or not works:
        _issue(errors, "ANKETA_WORKS_REQUIRED", "works",
               "нет ни одной работы: искать модули не по чему",
               "no work is listed: there is nothing to search modules for")
        works = []
    seen = set()
    for i, w in enumerate(works):
        if not isinstance(w, dict):
            _issue(errors, "ANKETA_WORK_NOT_OBJECT", "works[%d]" % i,
                   "работа должна быть объектом", "a work must be an object")
            continue
        wid = str(w.get("id") or "").strip()
        where = "works[%s]" % (wid or i)
        if not wid:
            _issue(errors, "ANKETA_WORK_ID_REQUIRED", where,
                   "у работы нет id: на неё нельзя сослаться", "the work has no id: it cannot be referenced")
        elif wid in seen:
            _issue(errors, "ANKETA_WORK_ID_DUPLICATE", where,
                   "id «%s» повторяется" % wid, "id %r is repeated" % wid)
        seen.add(wid)

        need = str(w.get("need") or "").strip()
        if not need:
            _issue(errors, "ANKETA_NEED_REQUIRED", where + ".need",
                   "у работы нет потребности: без этого поля поиск не начать",
                   "the work has no need: the search cannot start without this field")
        elif ";" in need or len(need.split()) > NEED_MAX_WORDS:
            _issue(warnings, "ANKETA_NEED_SPLIT", where + ".need",
                   "похоже на несколько потребностей в одной фразе: по составной задаче поиск "
                   "модуль не находит (замер 04.09.2026), раздели её на отдельные работы",
                   "looks like several needs in one phrase: the search finds no module for a "
                   "compound task (measured 04.09.2026), split it into separate works")

        form = str(w.get("output_form") or "").strip().lower()
        if form and формы.ФОРМЫ_ПО_РУССКИ.get(form, form) not in формы.ФОРМЫ:
            _issue(errors, "ANKETA_FORM_INVALID", where + ".output_form",
                   "форма «%s» не из пяти: %s" % (form, ", ".join(формы.ФОРМЫ)),
                   "form %r is not one of the five: %s" % (form, ", ".join(формы.ФОРМЫ)))

        for f, ru, en in WORK_FIELDS:
            if f != "need" and _blank(w.get(f)):
                empty.append({"path": where + "." + f, "question_ru": ru, "question_en": en,
                              "need": need})
    return {"ready": not errors, "errors": errors, "warnings": warnings, "empty": empty}


def needs(doc):
    """Фразы для поиска. Каждая идёт отдельным вызовом wz_capability_find, а не одним брифом."""
    out = []
    works = doc.get("works") if isinstance(doc, dict) else None
    for w in works if isinstance(works, list) else []:
        if isinstance(w, dict) and str(w.get("need") or "").strip():
            out.append({"id": str(w.get("id") or ""), "need": str(w["need"]).strip()})
    return out


def prompt():
    """Задание модели. Поля берутся из тех же таблиц, что и проверка."""
    lines = [
        "Заполни анкету компании по расшифровке встречи. Верни только JSON по бланку ниже, "
        "без пояснений.",
        "",
        "Правила:",
        "1. Не выдумывай. Чего нет в тексте, остаётся пустой строкой или пустым списком. "
        "Пустое место не ошибка: из пустых мест собирается список вопросов на следующую встречу.",
        "2. Одна работа содержит одну потребность одной фразой. Вопрос на встрече вида "
        "«был ли у вас опыт X» означает потребность X.",
        "3. В поле source у каждой работы стоит таймкод или короткая цитата, откуда она взята.",
        "4. Владелец процесса ставится, только если в тексте прямо сказано, что человек отвечает "
        "за этот процесс. Человек задал вопрос на встрече, и это ещё не делает его владельцем.",
        "5. output_form содержит одну из пяти форм по смыслу результата: list, number, steps, "
        "links, document. Если форма не ясна, поле остаётся пустым.",
        "6. contour.hosting принимает значения saas, on_prem или unknown.",
        "7. Требования к безопасности и к данным записываются в contour, а не в работы.",
        "",
        "Поля контура:",
    ]
    lines += ["  %s: %s" % (f, ru) for f, ru, _ in CONTOUR_FIELDS]
    lines += ["", "Поля каждой работы:"]
    lines += ["  %s: %s" % (f, ru) for f, ru, _ in WORK_FIELDS]
    lines += ["", "Бланк:", json.dumps(blank_form(), ensure_ascii=False, indent=2)]
    return "\n".join(lines)


def print_report(doc, rep):
    company = doc.get("company") if isinstance(doc, dict) and isinstance(doc.get("company"), dict) else {}
    src = doc.get("filled_from") if isinstance(doc, dict) and isinstance(doc.get("filled_from"), dict) else {}
    print("Анкета: %s" % (company.get("name") or "компания не названа"))
    if src.get("kind") or src.get("ref"):
        print("Заполнена по: %s" % " · ".join(x for x in (src.get("kind"), src.get("ref"), src.get("date")) if x))
    print("Потребностей для поиска: %d" % len(needs(doc)))
    for title, key, mark in (("Ошибки", "errors", "✗"), ("Предупреждения", "warnings", "!")):
        if rep[key]:
            print("\n%s:" % title)
            for e in rep[key]:
                print("  %s %s  %s: %s" % (mark, e["code"], e["path"], e["message_ru"]))
    if rep["empty"]:
        print("\nПустые места, это вопросы на следующую встречу:")
        group = None
        for e in rep["empty"]:
            head = ("контур" if e["path"].startswith("contour.")
                    else "работа «%s»" % (e.get("need") or e["path"].split(".")[0]))
            if head != group:
                print("  %s" % head)
                group = head
            print("    · %s: %s" % (e["path"].rsplit(".", 1)[-1], e["question_ru"]))
    print("\nИтог: %s" % ("анкета годится" if rep["ready"] else "анкета не годится, исправь ошибки"))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def selftest():
    import tempfile
    print("Самопроверка анкеты:")
    failed = []

    def expect(label, cond):
        print(("  ✓ " if cond else "  ✗ ") + label)
        if not cond:
            failed.append(label)

    def codes(rep, key="errors"):
        return {e["code"] for e in rep[key]}

    r = check(blank_form())
    expect("пустой бланк не годится: нет компании и потребности",
           not r["ready"] and {"ANKETA_COMPANY_NAME_REQUIRED", "ANKETA_NEED_REQUIRED"} <= codes(r))

    r = check(example())
    expect("образец годится и показывает пустые места", r["ready"] and len(r["empty"]) > 0)
    expect("из образца три потребности для поиска", len(needs(example())) == 3)

    d = example()
    d["works"][0]["output_form"] = "таблица"
    expect("форма вне пяти поймана", "ANKETA_FORM_INVALID" in codes(check(d)))

    d = example()
    d["works"][0]["output_form"] = "список"
    expect("русское имя формы принимается", check(d)["ready"])

    d = example()
    d["works"][1]["id"] = "w1"
    expect("повтор id пойман", "ANKETA_WORK_ID_DUPLICATE" in codes(check(d)))

    d = example()
    d["schema"] = "extella.anketa.v0"
    expect("чужая версия схемы поймана", "ANKETA_SCHEMA" in codes(check(d)))

    d = example()
    d["contour"]["hosting"] = "облако"
    expect("размещение вне списка поймано", "ANKETA_HOSTING_INVALID" in codes(check(d)))

    split = example()
    split["works"][0]["need"] = "распознавать счета; вести контрагентов; выставлять документы"
    rs = check(split)
    expect("несколько потребностей в фразе дают предупреждение, анкета годится",
           rs["ready"] and "ANKETA_NEED_SPLIT" in codes(rs, "warnings"))

    one = example()
    one["works"][0]["need"] = "распознавать счета и накладные"
    expect("союз «и» внутри одной потребности тревоги не даёт",
           "ANKETA_NEED_SPLIT" not in codes(check(one), "warnings"))

    msgs = check(blank_form())["errors"] + rs["warnings"]
    qs = check(example())["empty"]
    expect("каждое сообщение и каждый вопрос на двух языках (§3.26)",
           all(e.get("message_ru") and e.get("message_en") for e in msgs)
           and all(e.get("question_ru") and e.get("question_en") for e in qs))

    pr = prompt()
    expect("промпт называет каждое поле схемы",
           all(f in pr for f, _, _ in CONTOUR_FIELDS + WORK_FIELDS))

    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "анкета.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(example(), f, ensure_ascii=False)
        expect("файл с кириллицей читается при любой кодировке машины", check(_load(p))["ready"])

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if not failed else "есть провалы"))
    return 0 if not failed else 1


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # консоль Windows с cp1251 иначе падает на «✓»
    except Exception:
        pass
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    cmd = argv[0]
    if cmd == "--selftest":
        return selftest()
    if cmd == "--пустая":
        print(json.dumps(blank_form(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "--пример":
        print(json.dumps(example(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "--промпт":
        print(prompt())
        return 0
    if cmd in ("--проверить", "--потребности"):
        if len(argv) < 2:
            print("нужен путь к анкете: anketa.py %s файл.json" % cmd)
            return 2
        try:
            doc = _load(argv[1])
        except FileNotFoundError:
            print("файла нет: %s" % argv[1])
            return 2
        except json.JSONDecodeError as ex:
            print("файл не читается как JSON: %s" % ex)
            return 1
        if cmd == "--потребности":
            print(json.dumps(needs(doc), ensure_ascii=False, indent=2))
            return 0
        rep = check(doc)
        if "--json" in argv[2:]:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print_report(doc, rep)
        return 0 if rep["ready"] else 1
    print("неизвестная команда: %s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
