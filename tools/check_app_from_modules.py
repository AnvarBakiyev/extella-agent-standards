#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт готовности приложения, собранного из модулей.

ЗАЧЕМ. Приложение из модулей состоит из чужих узлов и одного окна, и каждая его часть
уже ломалась поодиночке: модуль без паспорта (границы неизвестны), эксперт не виден
агенту (кнопка отвечает «не найден»), права не сходятся (403 при целой странице), окно
без «чего не обещаем», манифест, отставший от модулей. Этот гейт не проверяет заново то,
что умеют существующие проверялки — он их зовёт и добавляет ровно то, что есть только у
приложения из модулей: реестр, план, отчёт провижининга.

Стадия решает строгость (stages.yaml): на стройке модуль без паспорта и непроверенный
провижининг — предупреждение с именем, на проде — отказ.

    python3 tools/check_app_from_modules.py apps/priemka_schetov
    python3 tools/check_app_from_modules.py apps/priemka_schetov --stage build
    python3 tools/check_app_from_modules.py --selftest

Коды выхода: 0 — готово, 1 — есть отказы, 2 — каталог или реестр не прочитаны.
"""
import contextlib
import io
import json
import os
import pathlib
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
import окно_из_форм as окно  # noqa: E402
import check_app_scopes  # noqa: E402
import check_automation_passport  # noqa: E402
import check_brand_copy  # noqa: E402
import check_waiting_state  # noqa: E402
from check_agent_passport import load_passport  # noqa: E402
from формы import Отказ  # noqa: E402

КАНОН_МАНИФЕСТ = СЮДА.parent / "templates" / "manifest_check.py"
РЕЕСТР = pathlib.Path.home() / "extella_wizard" / "registry" / "capabilities_declared.json"


def _issue(беды, code, ru, en):
    беды.append({"code": code, "severity": "error", "message_ru": ru, "message_en": en})


def _warn(беды, code, ru, en):
    беды.append({"code": code, "severity": "warning", "message_ru": ru, "message_en": en})


def проверить(папка: pathlib.Path, реестр: dict, стадия: str = "prod") -> list:
    беды = []
    строго = стадия != "build"
    план_путь = папка / "app.json"
    if not план_путь.exists():
        _issue(беды, "APP_PLAN_MISSING", "нет app.json — приложение из модулей начинается с плана",
               "app.json is missing — an application from modules starts with the plan")
        return беды
    try:
        план = окно.проверить_план(json.loads(план_путь.read_text(encoding="utf-8")))
    except (Отказ, ValueError) as о:
        _issue(беды, "APP_PLAN_INVALID", f"план не принят: {о}", f"the plan is rejected: {о}")
        return беды

    # 1. Модули: каждый в реестре и с пройденным паспортом.
    по_id = {}
    for а in (реестр.get("automations") or []):
        if а.get("automation_id"):
            по_id[а["automation_id"]] = а
        for имя in (а.get("experts") or []):
            по_id.setdefault(имя, а)
    for м in план["modules"]:
        з = по_id.get(м)
        if not з:
            (_issue if строго else _warn)(беды, "APP_MODULE_NO_PASSPORT",
                                          f"модуль «{м}» не найден в реестре паспортов — границы и требования неизвестны",
                                          f"module {м!r} is not in the passport registry — limits and requirements are unknown")
        elif not з.get("passport_ok"):
            (_issue if строго else _warn)(беды, "APP_MODULE_PASSPORT_NOT_READY",
                                          f"паспорт модуля «{м}» не проходит гейт: {', '.join(з.get('issues') or [])}",
                                          f"passport of module {м!r} fails the gate: {', '.join(з.get('issues') or [])}")
    # Эксперт кнопки обязан принадлежать одному из модулей приложения или самому приложению.
    известные = set()
    for м in план["modules"]:
        известные.update((по_id.get(м) or {}).get("experts") or [м])
    известные.update(п.stem for п in (папка / "experts").glob("*.py")) if (папка / "experts").is_dir() else None
    for э in план["screens"]:
        if not э.get("action"):
            continue
        зовёт = [ш.get("expert") for ш in (э["action"].get("steps") or [])] or [э["action"].get("expert")]
        for имя in зовёт:
            if имя not in известные:
                _issue(беды, "APP_ACTION_EXPERT_FOREIGN",
                       f"экран «{э['id']}» зовёт эксперт «{имя}», который не принадлежит ни одному модулю приложения",
                       f"screen {э['id']!r} calls expert {имя!r} that belongs to none of the app modules")

    # 2. Файлы сборки.
    for имя, ru, en in (("index.html", "нет окна — собери: build_app_from_modules.py", "no window — run build_app_from_modules.py"),
                        ("listing.json", "нет листинга с правами", "listing.json with rights is missing"),
                        ("MANIFEST.yaml", "нет манифеста зависимостей", "MANIFEST.yaml is missing"),
                        ("docs/automation_passport.yaml", "нет паспорта приложения", "the app passport is missing")):
        if not (папка / имя).exists():
            _issue(беды, "APP_FILE_MISSING", f"{имя}: {ru}", f"{имя}: {en}")
    if беды and any(б["code"] == "APP_FILE_MISSING" for б in беды):
        return беды
    копия = папка / "manifest_check.py"
    if not копия.exists() or копия.read_bytes() != КАНОН_МАНИФЕСТ.read_bytes():
        _issue(беды, "APP_MANIFEST_CHECK_DRIFT", "manifest_check.py отсутствует или отличается от канона templates/",
               "manifest_check.py is missing or differs from the canon in templates/")

    # 3. Окно: помощь с границами, живой вызов без токенов ядра, ожидание, бренд.
    окно_текст = (папка / "index.html").read_text(encoding="utf-8")
    for кусок, code, ru, en in (
            ("xtl_help", "APP_HELP_MISSING", "в окне нет «? Как это работает» (§3.20)", "the window has no «? How it works» (§3.20)"),
            ("app-agent/run", "APP_NO_LIVE_CALL", "окно не зовёт эксперта через app-agent/run", "the window does not call an expert via app-agent/run"),
            ("{{app_token}}", "APP_NO_APP_TOKEN", "в окне нет подстановки {{app_token}}", "the window has no {{app_token}} placeholder")):
        if кусок not in окно_текст:
            _issue(беды, code, ru, en)
    for запретное in ("api.extella.ai", "X-Auth-Token"):
        if запретное in окно_текст:
            _issue(беды, "APP_CORE_TOKEN_IN_PAGE", f"в окне есть «{запретное}» — токен ядра на странице запрещён",
                   f"the window contains {запретное!r} — the core token is forbidden on a page")
    for строка, что in check_waiting_state.проверить_текст(окно_текст):
        _issue(беды, "APP_WAITING_INVISIBLE", f"index.html:{строка}: {что}", f"index.html:{строка}: waiting is not visible")
    ошибки_бренда, _ = check_brand_copy.check_text("index.html", окно_текст, strict=True)
    for о in ошибки_бренда[:5]:
        _issue(беды, "APP_BRAND", str(о), str(о))

    # 4. Права: существующий гейт, его вывод — в отчёт.
    буфер = io.StringIO()
    with contextlib.redirect_stdout(буфер):
        код = check_app_scopes.проверить(папка)
    if код != 0:
        _issue(беды, "APP_SCOPES_MISMATCH", буфер.getvalue().strip().replace("\n", " | "),
               "declared rights do not match what the page calls: " + буфер.getvalue().strip().replace("\n", " | "))

    # 5. Паспорт приложения — существующий гейт автоматизации.
    отчёт = check_automation_passport.check_report(load_passport(str(папка / "docs" / "automation_passport.yaml")))
    for e in отчёт["errors"]:
        _issue(беды, "APP_PASSPORT_" + e["code"], e["message_ru"], e["message_en"])

    # 6. Провижининг: отчёт есть, все эксперты видны агенту, инструкции не тронуты.
    пров = папка / "provisioning.json"
    if not пров.exists():
        (_issue if строго else _warn)(беды, "APP_NOT_PROVISIONED",
                                      "нет provisioning.json — эксперты модулей не проверены на видимость агенту: python3 tools/provision_modules.py",
                                      "provisioning.json is missing — module experts were not verified for the agent: run provision_modules.py")
    else:
        try:
            п = json.loads(пров.read_text(encoding="utf-8"))
        except ValueError:
            п = {}
        if п.get("agent_id") != план["agent_id"]:
            _issue(беды, "APP_PROVISIONING_AGENT_MISMATCH", "provisioning.json сделан для другого агента, чем в app.json",
                   "provisioning.json was made for a different agent than app.json names")
        if not п.get("all_verified"):
            (_issue if строго else _warn)(беды, "APP_PROVISIONING_INCOMPLETE",
                                          "не все эксперты видны агенту приложения — см. provisioning.json",
                                          "not all experts are visible to the app agent — see provisioning.json")
        if п.get("instructions_touched") is not False:
            _issue(беды, "APP_AGENT_INSTRUCTIONS_TOUCHED", "провижининг тронул instructions агента — ядро могло быть стёрто",
                   "provisioning touched the agent instructions — the core may have been erased")
    return беды


def _печать(беды: list) -> int:
    ошибки = [б for б in беды if б["severity"] == "error"]
    for б in беды:
        print(("  ✗ " if б["severity"] == "error" else "  ~ ") + б["code"] + ": " + б["message_ru"])
    if ошибки:
        print(f"ИТОГ: НЕ ГОТОВО — отказов {len(ошибки)}, предупреждений {len(беды) - len(ошибки)}")
        return 1
    print(f"ИТОГ: ГОТОВО — предупреждений {len(беды)}")
    return 0


def selftest() -> int:
    import tempfile
    import build_app_from_modules as сборка
    ошибки = []
    with tempfile.TemporaryDirectory() as tmp:
        корень = pathlib.Path(tmp)
        реестр = {"automations": [{"automation_id": "toolkit_ocr_read", "experts": ["toolkit_ocr_read"],
                                   "experts_what": {"toolkit_ocr_read": "достаёт текст"},
                                   "limits": ["RU: не шлёт наружу. EN: sends nothing out."],
                                   "manifest_path": None, "passport_ok": True, "issues": []}]}
        папка = корень / "probe_ocr"
        папка.mkdir()
        (папка / "app.json").write_text(json.dumps(окно.пример_плана(), ensure_ascii=False))
        сборка.собрать(папка, реестр)
        (папка / "provisioning.json").write_text(json.dumps(
            {"agent_id": "agent_XXXXXXXX", "all_verified": True, "instructions_touched": False, "experts": []}))
        беды = проверить(папка, реестр, "prod")
        if not [б for б in беды if б["severity"] == "error"]:
            print("  ✓ собранное приложение с провижинингом проходит на проде")
        else:
            ошибки.append("исправное приложение не прошло: " + ", ".join(б["code"] for б in беды))

        # Все сообщения на двух языках (§3.26).
        (папка / "provisioning.json").unlink()
        план = json.loads((папка / "app.json").read_text())
        план["modules"] = ["unknown_module"]
        (папка / "app.json").write_text(json.dumps(план, ensure_ascii=False))
        сборка.собрать(папка, реестр, без_паспорта_ок=True)
        коды_build = {б["code"]: б["severity"] for б in проверить(папка, реестр, "build")}
        коды_prod = {б["code"]: б["severity"] for б in проверить(папка, реестр, "prod")}
        if коды_build.get("APP_MODULE_NO_PASSPORT") == "warning" and коды_prod.get("APP_MODULE_NO_PASSPORT") == "error" \
                and коды_build.get("APP_NOT_PROVISIONED") == "warning" and коды_prod.get("APP_NOT_PROVISIONED") == "error":
            print("  ✓ модуль без паспорта и отсутствие провижининга: на стройке предупреждение, на проде отказ")
        else:
            ошибки.append(f"строгость по стадии не работает: build={коды_build}, prod={коды_prod}")

        текст = (папка / "index.html").read_text()
        (папка / "index.html").write_text(текст.replace("xtl_help", "no_help").replace("finally", "always"))
        коды = {б["code"] for б in проверить(папка, реестр, "prod")}
        if {"APP_HELP_MISSING", "APP_WAITING_INVISIBLE"} <= коды:
            print("  ✓ окно без помощи и без видимого ожидания — поймано")
        else:
            ошибки.append(f"порча окна не поймана: {коды}")
        (папка / "index.html").write_text(текст)

        листинг = json.loads((папка / "listing.json").read_text())
        листинг["права"] = ["expert.run"]
        (папка / "listing.json").write_text(json.dumps(листинг, ensure_ascii=False))
        if "APP_SCOPES_MISMATCH" in {б["code"] for б in проверить(папка, реестр, "prod")}:
            print("  ✓ права, не сошедшиеся с кодом окна, — поймано через check_app_scopes")
        else:
            ошибки.append("расхождение прав не поймано")

        (папка / "manifest_check.py").write_text("# подменён\n")
        if "APP_MANIFEST_CHECK_DRIFT" in {б["code"] for б in проверить(папка, реестр, "prod")}:
            print("  ✓ подменённая копия manifest_check.py — поймано")
        else:
            ошибки.append("дрейф копии manifest_check не пойман")

        все = проверить(папка, реестр, "prod")
        if all(б.get("message_ru") and б.get("message_en") for б in все):
            print("  ✓ каждое сообщение на двух языках (§3.26)")
        else:
            ошибки.append("есть сообщение без одного из языков")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main(аргументы) -> int:
    if "--selftest" in аргументы:
        return selftest()
    стадия = "prod"
    if "--stage" in аргументы:
        стадия = аргументы[аргументы.index("--stage") + 1]
    пути = [а for а in аргументы if not а.startswith("--") and а != стадия]
    if not пути:
        print(__doc__)
        return 2
    папка = pathlib.Path(пути[0]).expanduser()
    реестр_путь = pathlib.Path(os.environ.get("EXTELLA_DECLARED_REGISTRY") or РЕЕСТР)
    if not папка.is_dir():
        print(f"ОТКАЗ: нет каталога {папка}")
        return 2
    if not реестр_путь.exists():
        print(f"ОТКАЗ: нет реестра паспортов {реестр_путь}")
        return 2
    print(f"Приложение из модулей: {папка} · стадия {стадия}")
    return _печать(проверить(папка, json.loads(реестр_путь.read_text(encoding="utf-8")), стадия))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
