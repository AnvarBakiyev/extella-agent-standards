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


def _needs_from_manifest(passport_path):
    """Требования модуля к машине — из его MANIFEST.yaml, а не из второго словаря в паспорте.

    Манифест уже есть у каждого продукта (№29) и проверяется установщиком; сборщику нужны те
    же факты словами: «нужна программа tesseract», «желателен модуль sglang». Ищем рядом с
    паспортом и в корне плагина (паспорт лежит в docs/). Нет манифеста — нет требований,
    и это честная пустота, а не выдумка.
    """
    here = os.path.dirname(os.path.abspath(passport_path))
    candidates = [os.path.join(here, "MANIFEST.yaml"),
                  os.path.join(os.path.dirname(here), "MANIFEST.yaml")]
    manifest = next((c for c in candidates if os.path.isfile(c)), None)
    if not manifest:
        return [], None
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                        "templates"))
        from manifest_check import parse as parse_manifest   # канон, тот же разбор, что у установщика
        with open(manifest, encoding="utf-8") as f:
            records = parse_manifest(f.read())
    except Exception:
        return [], manifest
    needs = []
    for r in records:
        kind = str(r.get("kind") or "")
        subject = r.get("name") or r.get("path") or r.get("port") or r.get("min_version") or ""
        level = "желательно" if str(r.get("level") or "").strip() == "warn" else "обязательно"
        needs.append("%s: %s (%s)" % (kind, subject, level))
    return needs, manifest


def _entry(path, doc, report):
    a = doc.get("automation") if isinstance(doc.get("automation"), dict) else {}
    needs, manifest = _needs_from_manifest(path)
    comp = doc.get("components") if isinstance(doc.get("components"), dict) else {}
    agents = [str(x.get("platform_agent_id") or "").strip()
              for x in (comp.get("platform_agents") or []) if isinstance(x, dict)]
    # experts несут не только имя: `what` — что способность делает словами клиента. Именно по
    # этому тексту её находит агент, поэтому имя без `what` — способность, которую не найти.
    experts, experts_what = [], {}
    for x in (comp.get("experts") or []):
        nm = str(x.get("name") or "").strip() if isinstance(x, dict) else str(x)
        if not nm:
            continue
        experts.append(nm)
        if isinstance(x, dict) and str(x.get("what") or "").strip():
            experts_what[nm] = str(x["what"]).strip()
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
        "kind": str(a.get("kind") or "automation").strip().lower(),
        "name": a.get("name") or {},
        "business_goal": a.get("business_goal") or None,
        # «Проверено живьём» — только из паспорта: дата и где запускали. Нет поля — нет метки.
        "verified": a.get("verified") if isinstance(a.get("verified"), dict) else None,
        "needs": needs,
        "manifest_path": manifest,
        "version": a.get("version") or None,
        "hosting_profile": a.get("hosting_profile") or None,
        "service": a.get("service") or {},
        "limits": a.get("limits") or [],
        "agent_ids": [x for x in agents if x],
        "experts": experts,
        "experts_what": experts_what,
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

    # Подсказка, а не запрет (решение Анвара 28.07): семейство из четырёх и более похожих
    # способностей — повод взвесить обработчик класса вместо N-го эксперта. Жёсткого правила
    # нет намеренно: абстракция раньше времени вредна не меньше, чем копипаста.
    families = {}
    for c in capabilities:
        pref = str(c["expert"]).split("_")[0]
        if pref:
            families.setdefault(pref, []).append(c["expert"])
    class_hints = sorted(
        [{"family": p, "count": len(v), "members": sorted(v)[:8]}
         for p, v in families.items() if len(v) >= 4],
        key=lambda x: -x["count"])

    return {
        "schema": SCHEMA,
        "source": "passports_in_git",
        "built_at": now or datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "automations": sorted(entries, key=lambda e: e["automation_id"] or e["source_path"]),
        "capabilities": capabilities,
        "shared_candidates": shared,
        "class_handler_hints": class_hints,
        "counts": {"automations": len(entries), "capabilities": len(capabilities),
                   "shared_candidates": len(shared), "passport_not_ready": len(not_ready),
                   "class_handler_hints": len(class_hints)},
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


DECLARED_KEY = "capability:declared:v1"       # свободное имя без истории (урок 28.07: близнецы ключей)
DECLARED_AGENT = "agent_extella_default"       # тот же скоуп-канон, что у живого реестра
DECLARED_SHARD = 8000


def publish(reg, api_base="https://api.extella.ai", api_token=""):
    """Кладёт собранный реестр паспортов в KV платформы. Возвращает код выхода (0 — успех).

    Зачем: wz_capability_find читает паспорта из файла на устройстве исполнения, а исполняется
    он по умолчанию на VPS, где git-репозиториев нет. Живой случай 04.09.2026: паспорт OCR
    собран на Mac, платформа отвечала «паспорта нет». Файл в git остаётся источником, KV — его
    зеркало, пересобираемое одной командой; читатель берёт из KV только то, что свежее локального.
    """
    import base64
    import urllib.request
    if not api_token:
        try:
            with open(os.path.expanduser("~/extella_wizard/app/config.json"), encoding="utf-8") as f:
                api_token = json.load(f).get("auth_token", "")
        except Exception:
            api_token = ""
    if not api_token:
        print("ОШИБКА: --publish без токена: нет --api-token и нет ~/extella_wizard/app/config.json")
        return 1

    def api(path, payload):
        req = urllib.request.Request(
            api_base.rstrip("/") + path, data=json.dumps(payload).encode("utf-8"),
            headers={"X-Auth-Token": api_token, "Content-Type": "application/json",
                     "X-Profile-Id": "default", "X-Agent-Id": DECLARED_AGENT}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    b64 = base64.b64encode(json.dumps(reg, ensure_ascii=False).encode("utf-8")).decode("ascii")
    chunks = [b64[i:i + DECLARED_SHARD] for i in range(0, len(b64), DECLARED_SHARD)]
    try:
        for i, c in enumerate(chunks):
            api("/api/kv/set", {"key": "%s:%d" % (DECLARED_KEY, i), "value": c, "global": True,
                                "description": "реестр паспортов (declared), шард %d" % i})
        api("/api/kv/set", {"key": DECLARED_KEY, "global": True,
                            "value": json.dumps({"chunks": len(chunks), "enc": "b64",
                                                 "built_at": reg["built_at"],
                                                 "count": reg["counts"]["automations"]}),
                            "description": "реестр паспортов из git (declared), мета шардов"})
    except Exception as exc:
        print("ОШИБКА: реестр паспортов в KV не записан: %s" % str(exc)[:160])
        return 1
    print("Реестр паспортов опубликован в KV: %s, шардов %d, built_at %s"
          % (DECLARED_KEY, len(chunks), reg["built_at"]))
    return 0


def main(argv):
    p = argparse.ArgumentParser(add_help=True, description="Сборка реестра способностей из паспортов")
    p.add_argument("roots", nargs="*", help="каталоги, где искать паспорта")
    p.add_argument("--roots-file", help="файл со списком каталогов, по одному на строку")
    p.add_argument("-o", "--out", help="куда записать реестр (по умолчанию — на экран)")
    p.add_argument("--check", metavar="ФАЙЛ",
                   help="не писать, а СВЕРИТЬ готовый файл с паспортами: отличается — код 1. "
                        "Гейт против протухания: артефакт в дистрибутиве уезжает клиенту, "
                        "а паспорта живут в других репозиториях и меняются без него")
    p.add_argument("--publish", action="store_true",
                   help="после сборки положить реестр паспортов в KV платформы (глобально, "
                        "шардами), чтобы wz_capability_find видел его на любом устройстве, а не "
                        "только там, где лежит файл")
    p.add_argument("--api-base", default="https://api.extella.ai")
    p.add_argument("--api-token", default="",
                   help="токен платформы; по умолчанию берётся из ~/extella_wizard/app/config.json")
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

    if args.check:
        path = os.path.expanduser(args.check)
        if not os.path.exists(path):
            print("ОШИБКА: сверять нечего — файла нет: %s" % path)
            return 1
        try:
            with open(path, encoding="utf-8") as f:
                shipped = json.load(f)
        except Exception as exc:
            print("ОШИБКА: файл не прочитан: %s" % exc)
            return 1
        # built_at меняется всегда — сверяем содержание, а не момент сборки.
        a = {k: v for k, v in reg.items() if k != "built_at"}
        b = {k: v for k, v in shipped.items() if k != "built_at"}
        if a == b:
            print("Каталог способностей СВЕЖИЙ: совпадает с паспортами (автоматизаций %d)"
                  % reg["counts"]["automations"])
            return 0
        print("КАТАЛОГ ПРОТУХ: файл не совпадает с паспортами.")
        ship_ids = {e.get("automation_id") for e in (shipped.get("automations") or [])}
        live_ids = {e.get("automation_id") for e in reg["automations"]}
        for aid in sorted(live_ids - ship_ids):
            print("  нет в файле, есть в паспортах: %s" % aid)
        for aid in sorted(ship_ids - live_ids):
            print("  есть в файле, нет в паспортах: %s" % aid)
        if ship_ids == live_ids:
            print("  состав тот же — изменилось содержимое паспортов")
        print("Пересобери: python3 %s --roots-file <roots> -o %s"
              % (os.path.basename(__file__), args.check))
        return 1

    text = json.dumps(reg, ensure_ascii=False, indent=2)
    if args.publish:
        # Зеркало в KV — тем же приёмом, что и живой реестр (b64-шарды по 8000: kv/set строит
        # эмбеддинг значения и большое не берёт). Источник остаётся в git; KV — производная,
        # которую читатель на любом устройстве может забрать, если локального файла нет.
        code = publish(reg, api_base=args.api_base, api_token=args.api_token)
        if code:
            return code
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
