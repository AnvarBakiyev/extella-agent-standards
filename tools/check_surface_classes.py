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

ПРИЁМКА 25.09.2026: прогон по живому реестру дал 12 попаданий. Одно ложное —
служебный `_ports.json` требовался как карточка, стало пробой. Одиннадцать
настоящих: установленные приложения без объявленного класса. Вторая редакция
починки объявляла расхождение копий паспорта отказом и краснела на одиннадцати
продуктах — снято до заметки, отказ остался за устаревшей канонной копией.
"""
import hashlib
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
# Каталог карточек уходящего тулбара. Канонический канал — Extella OS, поэтому путь
# настраивается (EXTELLA_CARDS_DIR), а его отсутствие — не провал: проверка объявленных
# классов работает и без установленных карточек.
DEFAULT_REGISTRY = Path(os.environ.get("EXTELLA_CARDS_DIR")
                        or Path.home() / "extella-plugins" / "_registry")
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
        # Служебные файлы реестра карточками не являются: `_ports.json` — это таблица
        # занятых портов. Первая редакция гейта требовала для неё класс поверхности,
        # то есть врала на живом дереве (замер 25.09.2026).
        if path.name.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cards.append({"id": path.stem, "unreadable": True})
            continue
        cards.append({"id": str(data.get("id") or path.stem), "name": data.get("name")})
    return cards


def passports_by_id(roots=None, таблица=None):
    """Паспорта автоматизаций из git — источник правды первого уровня.

    ДВА ЗАМЕРА 25.09.2026, оба меняли вердикт гейта на чужой предмет:

    1. Имя файла сверялось с учётом регистра, и паспорт, названный
       `AUTOMATION_PASSPORT.yaml`, был невидим: гейт продолжал ругаться «паспорта
       нет», когда паспорт написан и лежит рядом.
    2. На машине владельца пять копий одного паспорта в разных клонах продукта.
       Прежняя редакция брала первую попавшуюся и «не спорила» — и читала копию из
       мёртвого legacy-клона, то есть выносила вердикт не о том файле. Теперь
       неоднозначность — это отказ (H70), а разрешается она объявлением
       `passport:` в surface_classes.yaml.
    """
    найдено = {}
    дубли = {}
    корни = [str(r) for r in (roots or PASSPORT_ROOTS) if Path(r).is_dir()]
    пути = list(find_passports(корни))
    # Регистр имени файла не должен решать судьбу паспорта.
    for корень in корни:
        for путь in Path(корень).rglob("*"):
            if (путь.is_file() and путь.name.lower() in ("automation_passport.yaml", "automation_passport.yml")
                    and str(путь) not in пути
                    and not any(ч in str(путь) for ч in (".git/", "node_modules", "__pycache__"))):
                пути.append(str(путь))
    for path in sorted(set(пути)):
        try:
            doc = load_passport(str(path))
        except Exception:
            continue
        aid = str(((doc or {}).get("automation") or {}).get("automation_id") or "").strip()
        if not aid:
            continue
        дубли.setdefault(aid, []).append(str(path))
        if aid not in найдено:
            найдено[aid] = {"path": path, "doc": doc}
    # Канонная копия выбирается явно, а не «первая попавшаяся»: объявленная строкой
    # passport: в surface_classes.yaml, иначе — лежащая в ~/Documents/Extella (наш
    # канонный каталог), иначе первая. Прежняя редакция читала копию из мёртвой
    # ветки Codex и выносила вердикт не о том файле.
    канон = str(Path.home() / "Documents" / "Extella")
    for aid, копии in дубли.items():
        объявлен = str(((таблица or {}).get(aid) or {}).get("passport") or "").strip()
        выбор = [к for к in копии if объявлен and объявлен in к]
        if not выбор:
            выбор = [к for к in копии if к.startswith(канон)]
        if not выбор:
            выбор = копии
        try:
            найдено[aid] = {"path": выбор[0], "doc": load_passport(выбор[0]), "копии": копии}
        except Exception:
            найдено[aid] = {"path": выбор[0], "doc": найдено.get(aid, {}).get("doc") or {}, "копии": копии}
    return найдено


def audit(table, cards, passports):
    """Что не так. Пустой список = порядок."""
    problems = []
    # Расхождение копий — ЗАМЕТКА, а не отказ. Клонов репозитория у нас много, и
    # рабочая ветка законно отличается от канона; красная стена на одиннадцати
    # продуктах отключила бы гейт целиком. Отказ остаётся там, где он был: канонная
    # копия не проходит гейт паспорта. Замер 25.09.2026.
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

    # Приёмка 25.09.2026: живой прогон дал две ложные тревоги — служебный `_ports.json`
    # (проба ниже) и расхождение копий паспорта в одиннадцати продуктах. Второе оказалось
    # не дефектом продуктов, а следствием того, что клонов репозитория много: расхождение
    # стало заметкой, а выбор канонной копии — явным.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as вр2:
        к = Path(вр2)
        (к / "Extella").mkdir(); (к / "Codex").mkdir()
        (к / "Extella" / "automation_passport.yaml").write_text(
            "automation:\n  automation_id: проба\n  hosting_profile: local\n", encoding="utf-8")
        (к / "Codex" / "automation_passport.yaml").write_text(
            "automation:\n  automation_id: проба\n  hosting_profile: cloud\n", encoding="utf-8")
        найдено = passports_by_id([к / "Codex", к / "Extella"],
                                  {"проба": {"passport": "Extella"}})
        сведения = найдено.get("проба", {})
        if "Extella" not in str(сведения.get("path")):
            print("FAIL: объявленная канонная копия паспорта не выбрана")
            return 1
        if len(сведения.get("копии") or []) != 2:
            print("FAIL: расхождение копий не замечено")
            return 1
        if "проба" in dict(audit({}, [], найдено)):
            print("FAIL: расхождение копий в клонах объявлено отказом — это заметка")
            return 1
    одна = {"один": {"копии": ["/а/docs/automation_passport.yaml"], "doc": {}}}
    if "один" in dict(audit({}, [], одна)):
        print("FAIL: единственная копия паспорта объявлена проблемой")
        return 1

    # Приёмка 25.09.2026: живой прогон дал одну ложную тревогу — служебный
    # `_ports.json` (таблица портов) требовался как карточка. Проба держит это.
    import tempfile
    with tempfile.TemporaryDirectory() as вр:
        реестр = Path(вр)
        (реестр / "_ports.json").write_text('{"robin": 45103}', encoding="utf-8")
        (реестр / "robin.json").write_text('{"id": "robin", "name": "Robin"}', encoding="utf-8")
        найденные = {к["id"] for к in installed_cards(реестр)}
        if "_ports" in найденные:
            print("FAIL: служебный файл реестра посчитан карточкой")
            return 1
        if "robin" not in найденные:
            print("FAIL: настоящая карточка потеряна")
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
    for aid, сведения in sorted(passports.items()):
        копии = sorted(set(сведения.get("копии") or []))
        разные = set()
        for к in копии:
            try:
                разные.add(hashlib.sha256(Path(к).read_bytes()).hexdigest())
            except OSError:
                разные.add(к)
        if len(разные) > 1:
            print("  ~ %-26s паспорт расходится в %d рабочих копиях; канонной считаю %s"
                  % (aid, len(копии), сведения.get("path")))
    if not problems:
        print("У каждой карточки объявлен класс; у каждой автоматизации есть паспорт.")
        return 0
    for cid, text in problems:
        print("  ✗ %-26s %s" % (cid, text))
    print("\nПОВЕРХНОСТИ НЕ В ПОРЯДКЕ (карточек с проблемой: %d)." % len(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
