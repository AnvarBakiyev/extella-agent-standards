#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Класс каждой установленной карточки объявлен, и объявлен один раз.

ЗАЧЕМ. Evolution Console показывает парк автоматизаций клиента. Пока класс карточки
нигде не объявлен, в этот парк попадают наши собственные инструменты (Конструктор,
Подключения, Workspace) и сторонние программы пользователя — и Console либо требует
у них Automation Passport, которого у них не может быть, либо прячет их молча.

Гейт следит за тремя вещами:
  1. каждая карточка на устройстве имеет объявленный класс (`surface_classes.yaml`);
  2. у карточки класса `automation` есть Automation Passport в git, и он проходит гейт;
  3. `automation_id` в таблице совпадает с тем, что объявлено в самом паспорте —
     иначе Console свяжет установку и паспорт по имени, а связь по имени это наш
     класс «мёртвых ссылок».

Запуск:
  python3 tools/check_surface_classes.py [--registry ~/extella-plugins/_registry]
  python3 tools/check_surface_classes.py --selftest

Коды выхода: 0 — порядок, 1 — есть карточки без класса или без паспорта.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import load_passport
from check_automation_passport import check_report as check_automation
# Поиск паспортов — тот же, что у сборщика реестра. Свой обход однажды уже промахнулся
# мимо вложенных репозиториев (Юрист и Травел лежат не на первом уровне).
from build_capability_registry import find_passports

HERE = Path(__file__).resolve().parents[1]
TABLE = HERE / "surface_classes.yaml"
DEFAULT_REGISTRY = Path.home() / "extella-plugins" / "_registry"
PASSPORT_ROOTS = [Path.home() / "Documents"]
CLASSES = {"automation", "system", "installed_app", "probe"}


def load_table(path=TABLE):
    """Читает таблицу классов. Разбор простой: файл наш, форма фиксированная."""
    doc = load_passport(str(path))
    surfaces = (doc or {}).get("surfaces") or {}
    out = {}
    for card_id, item in surfaces.items():
        if isinstance(item, dict):
            out[str(card_id)] = {
                "class": str(item.get("class") or "").strip(),
                "automation_id": str(item.get("automation_id") or "").strip(),
                "why": str(item.get("why") or "").strip(),
            }
    return out


def installed_cards(registry=DEFAULT_REGISTRY):
    """Карточки, реально лежащие на этом устройстве (уровень 2 реестров)."""
    cards = []
    if not Path(registry).is_dir():
        return cards
    for path in sorted(Path(registry).glob("*.json")):
        if ".bak" in path.name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cards.append({"id": path.stem, "unreadable": True})
            continue
        cards.append({"id": str(data.get("id") or path.stem), "name": data.get("name")})
    return cards


def passports_by_id(roots=None):
    """Паспорта автоматизаций из git — источник правды первого уровня."""
    found = {}
    for path in find_passports([str(r) for r in (roots or PASSPORT_ROOTS) if Path(r).is_dir()]):
        try:
            doc = load_passport(str(path))
        except Exception:
            continue
        aid = str(((doc or {}).get("automation") or {}).get("automation_id") or "").strip()
        if not aid:
            continue
        # Рабочие копии (worktrees) объявляют тот же id — берём первый и не спорим:
        # дубли id отдельно ловит сборщик реестра.
        if aid not in found or "worktrees" in str(found[aid]["path"]):
            found[aid] = {"path": path, "doc": doc}
    return found


def audit(table, cards, passports):
    """Что не так. Пустой список = порядок."""
    problems = []
    for card in cards:
        cid = card["id"]
        entry = table.get(cid)
        if not entry:
            problems.append((cid, "класс не объявлен — впиши карточку в surface_classes.yaml "
                                  "(automation | system | installed_app | probe)"))
            continue
        klass = entry["class"]
        if klass not in CLASSES:
            problems.append((cid, "класс «%s» неизвестен — допустимо: %s"
                             % (klass, ", ".join(sorted(CLASSES)))))
            continue
        if klass != "automation":
            continue
        aid = entry["automation_id"] or cid
        found = passports.get(aid)
        if not found:
            problems.append((cid, "класс automation, но Automation Passport с id «%s» "
                                  "не найден в git" % aid))
            continue
        report = check_automation(json.loads(json.dumps(found["doc"])))
        if not report["ready"]:
            codes = ", ".join(sorted({e["code"] for e in report["errors"]})[:4])
            problems.append((cid, "паспорт «%s» не проходит гейт: %s" % (aid, codes)))
            continue
        declared_card = str((found["doc"].get("automation") or {}).get("registry_card_id") or aid)
        if declared_card != cid:
            problems.append((cid, "паспорт «%s» указывает карточку «%s» — связь по имени "
                                  "даёт мёртвую ссылку" % (aid, declared_card)))
    return problems


def selftest():
    """Гейт обязан краснеть: карточка без класса и automation без паспорта."""
    table = {"known_system": {"class": "system", "automation_id": "", "why": "проба"},
             "known_auto": {"class": "automation", "automation_id": "nonexistent_auto", "why": "проба"}}
    cards = [{"id": "known_system"}, {"id": "known_auto"}, {"id": "unknown_card"}]
    problems = dict(audit(table, cards, {}))
    if "unknown_card" not in problems:
        print("FAIL: карточка без объявленного класса не поймана")
        return 1
    if "known_auto" not in problems:
        print("FAIL: automation без паспорта не поймана")
        return 1
    if "known_system" in problems:
        print("FAIL: платформенная поверхность зря потребовала паспорт")
        return 1
    print("селфтест: карточка без класса и automation без паспорта ловятся")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    registry = DEFAULT_REGISTRY
    if "--registry" in argv:
        registry = Path(argv[argv.index("--registry") + 1]).expanduser()

    table = load_table()
    cards = installed_cards(registry)
    passports = passports_by_id()

    if not cards:
        print("  ~ карточек на этой машине нет — сверять нечего")
        return 0

    counts = {}
    for card in cards:
        klass = (table.get(card["id"]) or {}).get("class") or "НЕ ОБЪЯВЛЕН"
        counts[klass] = counts.get(klass, 0) + 1

    print("Классы установленных поверхностей (карточек: %d)\n" % len(cards))
    for klass in sorted(counts):
        print("  %-14s %d" % (klass, counts[klass]))
    print("")

    problems = audit(table, cards, passports)
    if not problems:
        print("У каждой карточки объявлен класс; у каждой автоматизации есть паспорт.")
        return 0
    for cid, text in problems:
        print("  ✗ %-26s %s" % (cid, text))
    print("\nПОВЕРХНОСТИ НЕ В ПОРЯДКЕ (карточек с проблемой: %d)." % len(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
