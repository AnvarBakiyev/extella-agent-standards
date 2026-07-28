#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка ЕДИНОГО РЕЕСТРА способностей из паспортов (решение Анвара 28.07.2026).

Почему так, а не в KV. Реестр можно хранить только там, откуда его можно пересобрать.
Если потеря хранилища = потеря данных, это не реестр, а единственная копия. 28.07 выяснилось,
что 12 записей реестра автоматизаций существовали ТОЛЬКО в KV, а `global: true` не гарантирует
общего чтения: собственная копия ключа у агента побеждает общую молча
(разбор — `docs/INCIDENT_KV_SCOPE_SHADOWING.md` в core-portal).

Отсюда три уровня, и этот скрипт делает первый:

1. **что существует** — паспорта в git. ИСТОЧНИК ПРАВДЫ, ревьюится и откатывается;
2. **что установлено здесь** — файлы на устройстве плюс контракт `/api/state`;
3. **что агент может найти** — вот этот реестр. ПРОИЗВОДНАЯ, пересобирается одной командой.

Реестр НЕ прячет проблемы: паспорт, не прошедший гейт, попадает в реестр с `passport_ok: false`
и кодами ошибок. Задача реестра — сказать правду о том, что есть, а не показать красивую картину.

Как пользоваться:
  python3 build_capability_registry.py ~/Documents/Extella ~/Documents/Codex
  python3 build_capability_registry.py --roots-file roots.txt -o registry.json
  python3 build_capability_registry.py --selftest

Коды выхода: 0 — реестр собран, 1 — собран, но есть автоматизации с непройденным паспортом,
2 — собирать нечего.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_agent_passport import load_passport                      # единый разбор файла
from check_automation_passport import check_report as check_automation

SCHEMA = "extella.capability_registry.v1"
PASSPORT_NAMES = ("automation_passport.yaml", "automation_passport.yml")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
# Шаблоны стандартов — не продукт; попадут в реестр как пустышки и испортят счёт.
SKIP_PATH_PARTS = ("extella-agent-standards/templates", "extella-evolution-standards-v2/templates")


def find_passports(roots):
    """Все паспорта автоматизаций под указанными корнями, без шаблонов и мусорных каталогов."""
    found = []
    for root in roots:
        root = os.path.expanduser(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if any(part in dirpath.replace(os.sep, "/") for part in SKIP_PATH_PARTS):
                continue
            for name in filenames:
                if name in PASSPORT_NAMES:
                    found.append(os.path.join(dirpath, name))
    return sorted(set(found))


def _entry(path, doc, report):
    a = doc.get("automation") if isinstance(doc.get("automation"), dict) else {}
    comp = doc.get("components") if isinstance(doc.get("components"), dict) else {}
    agents = [str(x.get("platform_agent_id") or "").strip()
              for x in (comp.get("platform_agents") or []) if isinstance(x, dict)]
    experts = [str(x.get("name") or "").strip() if isinstance(x, dict) else str(x)
               for x in (comp.get("experts") or [])]
    integrations = []
    for it in (comp.get("integrations") or []):
        if not isinstance(it, dict):
            continue
        integrations.append({"kind": it.get("kind"),
                             "scopes": it.get("scopes") or [],
                             "external_writes": bool(it.get("external_writes")),
                             "personal_data": it.get("personal_data")})
    return {
        "automation_id": a.get("automation_id") or None,
        "name": a.get("name") or {},
        "version": a.get("version") or None,
        "hosting_profile": a.get("hosting_profile") or None,
        "service": a.get("service") or {},
        "limits": a.get("limits") or [],
        "agent_ids": [x for x in agents if x],
        "experts": [x for x in experts if x],
        "integrations": integrations,
        "source_path": path,
        "passport_ok": bool(report["ready"]),
        "issues": [e["code"] for e in report["errors"]],
    }


def build(roots, now=None):
    """Собирает реестр. now передаётся снаружи, чтобы сборка была воспроизводима в тестах."""
    entries, warnings = [], []
    for path in find_passports(roots):
        doc = load_passport(path)
        if not isinstance(doc, dict):
            warnings.append({"code": "PASSPORT_UNREADABLE", "path": path,
                             "message_ru": "паспорт не прочитан — пропущен",
                             "message_en": "passport unreadable — skipped"})
            continue
        entries.append(_entry(path, doc, check_automation(doc)))

    # Один id — одна автоматизация. Дубль означает, что два репозитория считают себя одним
    # продуктом; это ровно тот класс, из-за которого реестры расходятся.
    by_id = {}
    for e in entries:
        if not e["automation_id"]:
            warnings.append({"code": "AUTOMATION_ID_MISSING", "path": e["source_path"],
                             "message_ru": "у паспорта нет automation_id — в реестр по имени не берём",
                             "message_en": "the passport has no automation_id — not indexed by name"})
            continue
        by_id.setdefault(e["automation_id"], []).append(e)
    for aid, group in by_id.items():
        if len(group) > 1:
            warnings.append({"code": "AUTOMATION_ID_DUPLICATE", "path": aid,
                             "message_ru": "id «%s» объявлен в %d паспортах: %s"
                                           % (aid, len(group), ", ".join(g["source_path"] for g in group)),
                             "message_en": "id %r is declared in %d passports: %s"
                                           % (aid, len(group), ", ".join(g["source_path"] for g in group))})

    # Способность, объявленная несколькими автоматизациями — кандидат в общие (пункт C8).
    # Это не ошибка, а сигнал: одно и то же написано несколько раз.
    owners = {}
    for e in entries:
        for name in e["experts"]:
            owners.setdefault(name, set()).add(e["automation_id"] or e["source_path"])
    shared = sorted([{"expert": n, "used_by": sorted(v)} for n, v in owners.items() if len(v) > 1],
                    key=lambda x: x["expert"])

    capabilities = sorted(
        [{"expert": n, "owner": sorted(v)[0], "shared": len(v) > 1} for n, v in owners.items()],
        key=lambda x: x["expert"])

    not_ready = [e["automation_id"] or e["source_path"] for e in entries if not e["passport_ok"]]

    return {
        "schema": SCHEMA,
        "source": "passports_in_git",
        "built_at": now or datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "automations": sorted(entries, key=lambda e: e["automation_id"] or e["source_path"]),
        "capabilities": capabilities,
        "shared_candidates": shared,
        "counts": {"automations": len(entries), "capabilities": len(capabilities),
                   "shared_candidates": len(shared), "passport_not_ready": len(not_ready)},
        "warnings": warnings,
    }


SELFTEST_GOOD = {
    "automation": {
        "automation_id": "demo_one", "name": {"ru": "Демо", "en": "Demo"}, "owner": "Анвар",
        "business_goal": "проверка сборки", "version": "1.0.0", "languages": ["ru", "en"],
        "hosting_profile": "local",
        "service": {"port": 1, "health": "/api/health", "state": "/api/state"},
        "limits": ["ничего не делает"], "help_surface": "панель",
    },
    "components": {
        "platform_agents": [{"platform_agent_id": "agent_demo123456", "role": "r",
                             "provider_expected": "alibaba"}],
        "experts": [{"name": "shared_send", "required": True}, {"name": "only_mine", "required": True}],
    },
    "budgets": {"max_duration_ms": 1, "max_llm_tokens": 1, "max_external_actions": 0},
    "operations": {"owner_on_call": "Анвар", "rollback": "версия -1", "success_metric": "ok"},
}


def selftest():
    import copy
    import tempfile
    print("Самопроверка сборки реестра способностей:")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        good = copy.deepcopy(SELFTEST_GOOD)
        second = copy.deepcopy(SELFTEST_GOOD)
        second["automation"]["automation_id"] = "demo_two"
        second["components"]["experts"] = [{"name": "shared_send"}]
        broken = copy.deepcopy(SELFTEST_GOOD)
        broken["automation"]["automation_id"] = "demo_broken"
        broken["automation"]["hosting_profile"] = ""      # обязательное поле пустое
        # своя способность, чтобы «общей» стала ровно одна и проверка была осмысленной
        broken["components"]["experts"] = [{"name": "broken_only"}]
        for i, doc in enumerate((good, second, broken)):
            d = os.path.join(tmp, "pack%d" % i, "docs")
            os.makedirs(d)
            with open(os.path.join(d, "automation_passport.yaml"), "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False)     # YAML-разборщик читает и JSON

        reg = build([tmp], now="2026-01-01T00:00:00Z")

        checks = [
            ("три паспорта найдены", reg["counts"]["automations"] == 3),
            ("общая способность найдена", [s["expert"] for s in reg["shared_candidates"]] == ["shared_send"]),
            ("общая помечена в способностях",
             any(c["expert"] == "shared_send" and c["shared"] for c in reg["capabilities"])),
            ("личная не помечена общей",
             any(c["expert"] == "only_mine" and not c["shared"] for c in reg["capabilities"])),
            ("непройденный паспорт ПОПАЛ в реестр",
             any(e["automation_id"] == "demo_broken" for e in reg["automations"])),
            ("и помечен честно",
             any(e["automation_id"] == "demo_broken" and not e["passport_ok"]
                 and "AUTOMATION_HOSTING_REQUIRED" in e["issues"] for e in reg["automations"])),
            ("счётчик непройденных верен", reg["counts"]["passport_not_ready"] == 1),
            ("сборка воспроизводима", build([tmp], now="2026-01-01T00:00:00Z") == reg),
        ]
        for label, passed in checks:
            print(("PASS: " if passed else "FAIL: ") + label)
            ok = ok and passed

        # Дубль id — два репозитория считают себя одним продуктом.
        d = os.path.join(tmp, "pack_dup", "docs")
        os.makedirs(d)
        with open(os.path.join(d, "automation_passport.yaml"), "w", encoding="utf-8") as f:
            json.dump(good, f, ensure_ascii=False)
        dup = build([tmp], now="2026-01-01T00:00:00Z")
        if any(w["code"] == "AUTOMATION_ID_DUPLICATE" for w in dup["warnings"]):
            print("PASS: дубль automation_id — поймано")
        else:
            ok = False
            print("FAIL: дубль automation_id — НЕ поймано")

        for w in dup["warnings"]:
            if not w.get("message_ru") or not w.get("message_en"):
                ok = False
                print("FAIL: предупреждение без одного из языков: %s" % w["code"])
                break
        else:
            print("PASS: каждое предупреждение на двух языках (§3.26)")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    p = argparse.ArgumentParser(add_help=True, description="Сборка реестра способностей из паспортов")
    p.add_argument("roots", nargs="*", help="каталоги, где искать паспорта")
    p.add_argument("--roots-file", help="файл со списком каталогов, по одному на строку")
    p.add_argument("-o", "--out", help="куда записать реестр (по умолчанию — на экран)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()

    roots = list(args.roots)
    if args.roots_file:
        with open(os.path.expanduser(args.roots_file), encoding="utf-8") as f:
            roots += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not roots:
        print("ОШИБКА: не указано ни одного каталога для поиска паспортов")
        return 2

    reg = build(roots)
    if not reg["automations"]:
        print("ОШИБКА: паспортов не найдено — собирать нечего. Проверь каталоги.")
        return 2

    text = json.dumps(reg, ensure_ascii=False, indent=2)
    if args.out:
        with open(os.path.expanduser(args.out), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        c = reg["counts"]
        print("Реестр собран: автоматизаций %d, способностей %d, общих кандидатов %d, "
              "паспорт не пройден у %d" % (c["automations"], c["capabilities"],
                                           c["shared_candidates"], c["passport_not_ready"]))
        for e in reg["automations"]:
            if not e["passport_ok"]:
                print("  НЕ ГОТОВ: %s — %s" % (e["automation_id"] or e["source_path"],
                                               ", ".join(e["issues"][:3])))
        for w in reg["warnings"]:
            print("  ВНИМАНИЕ: %s — %s" % (w["code"], w["message_ru"]))
        print("Файл: %s" % args.out)
    else:
        print(text)
    return 1 if reg["counts"]["passport_not_ready"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
