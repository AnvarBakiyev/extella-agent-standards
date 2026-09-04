#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка приложения из модулей: план → каталог продукта, готовый к провижинингу и гейту.

ЗАЧЕМ. Создатель описывает приложение планом (`app.json`): какие модули, какие экраны в
пяти формах, что окно обещает и чего не обещает. Всё остальное у продукта одинаковое и
потому не должно писаться руками: окно, листинг с правами, манифест зависимостей как
объединение манифестов модулей, паспорт автоматизации, эксперт состояния, иконка,
README. Каждая из этих вещей уже ломалась, когда её собирали вручную (порт, права, копия
манифеста), поэтому здесь они выводятся из плана и реестра, а не переписываются.

Что этот инструмент НЕ делает: не ходит на платформу (это `provision_modules.py`) и не
проверяет готовность (это `check_app_from_modules.py`). Сборка детерминирована: один план и
один реестр дают один и тот же каталог.

    python3 tools/build_app_from_modules.py apps/priemka_schetov            # рядом лежит app.json
    python3 tools/build_app_from_modules.py apps/priemka_schetov --реестр путь/к/capabilities_declared.json
    python3 tools/build_app_from_modules.py --selftest

Коды выхода: 0 — собрано, 1 — отказ с названной причиной, 2 — план или реестр не прочитаны.
"""
import datetime
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import zlib

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
sys.path.insert(0, str(СЮДА.parent / "templates"))
import окно_из_форм as окно  # noqa: E402
from формы import Отказ  # noqa: E402
from manifest_check import parse as разобрать_манифест  # noqa: E402

КАНОН_МАНИФЕСТ = СЮДА.parent / "templates" / "manifest_check.py"
БРОНЗА = СЮДА / "bronze_icon.py"
РЕЕСТР = pathlib.Path.home() / "extella_wizard" / "registry" / "capabilities_declared.json"
ПРАВА = ["expert.run", "device.run"]      # окно зовёт эксперта и закрепляет вызов за устройством
ТЕГИ = ["приложение", "модули"]

СОСТОЯНИЕ = '''# description: __ОПИСАНИЕ__
def __ИМЯ__(method: str = "state") -> dict:
    """Состояние приложения «__НАЗВАНИЕ__» по схеме extella.automation_state.v1.

    Приложение собрано из модулей и своего процесса не имеет, поэтому здесь нет ни
    запусков, ни расписаний: неизвестное отдаётся как null, а не как правдоподобное число.
    Единственное, что известно на устройстве: какие модули объявлены и виден ли листенер.
    """
    import datetime, hashlib, os, socket
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    account_ref = None
    try:
        with open(os.path.expanduser("~/.extella/api_token.txt"), encoding="utf-8") as f:
            account_ref = hashlib.sha256(f.read().strip().encode("utf-8")).hexdigest()[:16]
    except Exception:
        account_ref = None
    return {
        "schema": "extella.automation_state.v1",
        "enabled": True,
        "active_version": "__ВЕРСИЯ__",
        "last_run": None,
        "last_result": None,
        "last_error": None,
        "schedules": [],
        "checked_at": now,
        "modules": __МОДУЛИ__,
        "listener_present": os.path.exists(os.path.expanduser("~/.extella/device.txt")),
        "bound_to": {
            "hosting_profile": "local",
            "host": socket.gethostname(),
            "platform_profile_id": "default",
            "account_ref": account_ref,
            "agent_ids": ["__АГЕНТ__"],
            "since": "__СОБРАНО__",
        },
    }
'''


def _png(размер: int = 256) -> bytes:
    """Запасная квадратная иконка, если канонический генератор недоступен: одна плитка
    цвета акцента, без рисунка. Честнее пустого файла, но канон — bronze_icon.py."""
    строка = b"\x00" + bytes([0xC5, 0x7E, 0x33]) * размер
    сырое = строка * размер

    def кусок(тип, данные):
        return struct.pack(">I", len(данные)) + тип + данные + struct.pack(">I", zlib.crc32(тип + данные) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + кусок(b"IHDR", struct.pack(">IIBBBBB", размер, размер, 8, 2, 0, 0, 0))
            + кусок(b"IDAT", zlib.compress(сырое, 9)) + кусок(b"IEND", b""))


def иконка(куда: pathlib.Path) -> str:
    if куда.exists():
        return "уже есть"
    if БРОНЗА.exists():
        try:
            р = subprocess.run([sys.executable, str(БРОНЗА), "file-text", str(куда)],
                               capture_output=True, text=True, timeout=120)
            if р.returncode == 0 and куда.exists():
                return "bronze_icon.py"
        except Exception:
            pass
    куда.write_bytes(_png())
    return "запасная плитка (bronze_icon.py не сработал)"


def записи_реестра(модули: list, реестр: dict) -> tuple:
    """Записи реестра по идентификаторам модулей + список тех, кого в реестре нет."""
    по_id = {}
    for а in (реестр.get("automations") or []):
        if а.get("automation_id"):
            по_id[а["automation_id"]] = а
        for имя in (а.get("experts") or []):
            по_id.setdefault(имя, а)
    найдено, нет = [], []
    for м in модули:
        if м in по_id:
            if по_id[м] not in найдено:
                найдено.append(по_id[м])
        else:
            нет.append(м)
    return найдено, нет


def манифест(записи: list) -> str:
    """Объединение манифестов модулей: одна проверка на каждую зависимость, без дублей."""
    строки = ["# Манифест зависимостей приложения из модулей. Собран из манифестов модулей",
              "# инструментом build_app_from_modules.py — руками не править: правь манифест модуля.",
              "checks:",
              "  - kind: python", '    min_version: "3.10"',
              '    fix_ru: "поставь Python 3.10+ — на нём исполняются эксперты модулей"']
    виденные = {("python", "3.10")}
    for з in записи:
        путь = з.get("manifest_path")
        if not путь or not os.path.isfile(путь):
            continue
        for р in разобрать_манифест(pathlib.Path(путь).read_text(encoding="utf-8")):
            ключ = (р.get("kind"), р.get("name") or р.get("path") or р.get("port") or р.get("min_version"))
            if ключ in виденные:
                continue
            виденные.add(ключ)
            строки.append(f"  - kind: {р['kind']}")
            for к in ("name", "path", "port", "min_version", "level", "fix_ru"):
                if р.get(к) not in (None, ""):
                    строки.append(f'    {к}: "{str(р[к]).replace(chr(34), chr(39))}"')
    return "\n".join(строки) + "\n"


def _yaml_строка(т: str) -> str:
    return '"' + str(т).replace("\\", "\\\\").replace('"', '\\"') + '"'


def паспорт(план: dict, записи: list, версия: str, слаг: str) -> str:
    границы = []
    for з in записи:
        for л in (з.get("limits") or []):
            if л not in границы:
                границы.append(л)
    for язык, текст in (("ru", план["description"]["ru"]), ("en", план["description"]["en"])):
        pass
    границы.append("RU: Окно работает только там, где есть живой листенер Extella; без него кнопки честно "
                   "говорят, что устройство не определено. EN: The window works only where a live Extella "
                   "listener exists; without it the buttons say that the device is unknown.")
    эксперты = []
    for з in записи:
        for имя in (з.get("experts") or []):
            что = (з.get("experts_what") or {}).get(имя) or ""
            эксперты.append((имя, что, True))
    эксперты.append((f"{слаг}_state", "Состояние приложения по схеме extella.automation_state.v1", False))
    строки = [
        "---", f"# Паспорт приложения «{план['name']['ru']}», собранного из модулей.",
        "# Собран build_app_from_modules.py из app.json и реестра паспортов модулей.",
        "automation:", '  kind: "automation"', f'  automation_id: "app_{слаг}"',
        "  name:", f"    ru: {_yaml_строка(план['name']['ru'])}", f"    en: {_yaml_строка(план['name']['en'])}",
        f"  owner: {_yaml_строка(план.get('owner') or 'создатель приложения')}",
        f"  business_goal: {_yaml_строка(план['description']['ru'])}",
        f'  version: "{версия}"', '  languages: ["ru", "en"]', '  hosting_profile: "local"',
        "  state_reader:", f'    expert: "{слаг}_state"', '    params: {method: "state"}', '    method: "state"',
        '    schema: "extella.automation_state.v1"', '    agent_scope: "AGENT_FROM_COMPONENT"',
        '    agent_scope_ref: "app_agent"', "    expert_global: false",
        '    execution_device: "DEVICE_FROM_HOST"', '    data_device: "DEVICE_FROM_HOST"', '    evidence: "exact_target"',
        "  limits:"] + [f"    - {_yaml_строка(л)}" for л in границы] + [
        '  help_surface: "окно приложения, кнопка «? Как это работает» в шапке; открывается при первом визите"',
        "components:", "  platform_agents:", '    - component_id: "app_agent"',
        f'      platform_agent_id: "{план["agent_id"]}"',
        '      role: "агент приложения: запускает эксперты модулей на устройстве покупателя"',
        '      provider_expected: "alibaba"',
        "  experts:"] + [
        f'    - name: "{имя}"\n      required: true\n      global: {"true" if гл else "false"}\n      what: {_yaml_строка(что)}'
        for имя, что, гл in эксперты] + [
        "  schedules: []", "  integrations: []", "  knowledge: []", "  rules: []",
        "operations:",
        '  rollback: "Снять листинг с витрины и удалить эксперты приложения из скоупа его агента; эксперты модулей общие и остаются. Файлы покупателя не трогаются."',
    ]
    return "\n".join(строки) + "\n"


def собрать(папка: pathlib.Path, реестр: dict, без_паспорта_ок: bool = False) -> dict:
    план = json.loads((папка / "app.json").read_text(encoding="utf-8"))
    план = окно.проверить_план(план)
    if not str(план["agent_id"]).startswith("agent_"):
        raise Отказ("agent_id: для сборки нужен точный id агента приложения (agent_…); "
                    "агент создаётся по API до сборки — окну модель не нужна, только запуск экспертов")
    записи, нет = записи_реестра(план["modules"], реестр)
    if нет and not без_паспорта_ок:
        raise Отказ(f"модулей нет в реестре паспортов: {', '.join(нет)}. Выдай им паспорт и пересобери "
                    f"реестр, или собери с --без-паспорта — гейт на стадии прод это не пропустит")
    не_готовы = [з["automation_id"] for з in записи if not з.get("passport_ok")]
    версия = str(план.get("version") or "0.1.0")
    слаг = план["slug"]
    сегодня = datetime.date.today().isoformat()

    (папка / "docs").mkdir(exist_ok=True)
    (папка / "experts").mkdir(exist_ok=True)
    (папка / "index.html").write_text(окно.страница(план), encoding="utf-8")
    (папка / "MANIFEST.yaml").write_text(манифест(записи), encoding="utf-8")
    shutil.copy(КАНОН_МАНИФЕСТ, папка / "manifest_check.py")
    (папка / "docs" / "automation_passport.yaml").write_text(паспорт(план, записи, версия, слаг), encoding="utf-8")
    имя_состояния = f"{слаг}_state"
    (папка / "experts" / f"{имя_состояния}.py").write_text(
        СОСТОЯНИЕ.replace("__ОПИСАНИЕ__", f"Состояние приложения «{план['name']['ru']}» (extella.automation_state.v1)")
        .replace("__ИМЯ__", имя_состояния).replace("__НАЗВАНИЕ__", план["name"]["ru"])
        .replace("__ВЕРСИЯ__", версия).replace("__МОДУЛИ__", json.dumps(план["modules"], ensure_ascii=False))
        .replace("__АГЕНТ__", план["agent_id"]).replace("__СОБРАНО__", сегодня + "T00:00:00Z"),
        encoding="utf-8")
    границы = []
    for з in записи:
        границы += [л for л in (з.get("limits") or []) if л not in границы]
    листинг = {
        "name": план["name"]["ru"], "name_en": план["name"]["en"],
        "описание": план["description"]["ru"], "description_en": план["description"]["en"],
        "теги": ТЕГИ + [т for т in (план.get("tags") or []) if т not in ТЕГИ][:4],
        "иконка": "icon.png", "версия": версия, "цена": план.get("price", 0),
        "права": ПРАВА, "состояние": "собрано", "границы": границы,
        "модули": план["modules"], "агент": план["agent_id"],
        "источник": {"kind": "app_from_modules", "план": "app.json", "собрано": сегодня},
    }
    старый = папка / "listing.json"
    if старый.exists():
        try:
            прежний = json.loads(старый.read_text(encoding="utf-8"))
            for к in ("listing_id", "version_id"):
                if прежний.get(к):
                    листинг[к] = прежний[к]
        except Exception:
            pass
    старый.write_text(json.dumps(листинг, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    как_иконка = иконка(папка / "icon.png")
    (папка / "README.md").write_text(
        f"# {план['name']['ru']}\n\nЧто делает: {план['description']['ru']}\n\n"
        f"Как запустить: открыть плитку в магазине ОС Extella; окно зовёт эксперты модулей на этом компьютере.\n\n"
        f"Из чего собрано: модули {', '.join(план['modules'])}; план — app.json; сборка — "
        f"`python3 tools/build_app_from_modules.py`.\n\nЧего пока нет: "
        f"{план.get('missing_ru') or 'см. блок «чего не обещаем» в окне'}.\n", encoding="utf-8")
    return {"папка": str(папка), "модули": [з["automation_id"] for з in записи], "без_паспорта": нет,
            "паспорт_не_готов": не_готовы, "иконка": как_иконка, "экранов": len(план["screens"])}


def selftest() -> int:
    import tempfile
    ошибки = []
    with tempfile.TemporaryDirectory() as tmp:
        корень = pathlib.Path(tmp)
        модуль = корень / "modules" / "toolkit_probe"
        (модуль / "docs").mkdir(parents=True)
        (модуль / "MANIFEST.yaml").write_text(
            'checks:\n  - kind: python\n    min_version: "3.10"\n    fix_ru: "python"\n'
            '  - kind: command\n    name: "tesseract"\n    level: warn\n    fix_ru: "brew install tesseract"\n')
        реестр = {"automations": [{"automation_id": "toolkit_ocr_read", "experts": ["toolkit_ocr_read"],
                                   "experts_what": {"toolkit_ocr_read": "достаёт текст"},
                                   "limits": ["RU: не шлёт наружу. EN: sends nothing out."],
                                   "manifest_path": str(модуль / "MANIFEST.yaml"), "passport_ok": True}]}
        папка = корень / "apps" / "probe_ocr"
        папка.mkdir(parents=True)
        план = окно.пример_плана()
        (папка / "app.json").write_text(json.dumps(план, ensure_ascii=False))
        try:
            итог = собрать(папка, реестр)
        except Отказ as о:
            print(f"  ✗ сборка примера: {о}")
            return 1
        print(f"  ✓ пример собран: экранов {итог['экранов']}, иконка — {итог['иконка']}")
        for имя in ("index.html", "listing.json", "MANIFEST.yaml", "manifest_check.py",
                    "docs/automation_passport.yaml", "experts/probe_ocr_state.py", "icon.png", "README.md"):
            if not (папка / имя).exists():
                ошибки.append(f"нет файла {имя}")
        if (папка / "manifest_check.py").read_bytes() != КАНОН_МАНИФЕСТ.read_bytes():
            ошибки.append("manifest_check.py отличается от канона")
        текст_манифеста = (папка / "MANIFEST.yaml").read_text()
        if текст_манифеста.count("tesseract") != 2 or текст_манифеста.count("kind: python") != 1:
            ошибки.append("манифест не объединил зависимости модуля без дублей")
        else:
            print("  ✓ манифест приложения — объединение манифестов модулей, python один раз")

        import check_automation_passport
        from check_agent_passport import load_passport
        отчёт = check_automation_passport.check_report(load_passport(str(папка / "docs" / "automation_passport.yaml")))
        if отчёт["ready"]:
            print("  ✓ паспорт приложения проходит гейт автоматизации")
        else:
            ошибки.append("паспорт не проходит: " + ", ".join(e["code"] for e in отчёт["errors"]))

        import check_app_scopes
        import io, contextlib
        буфер = io.StringIO()
        with contextlib.redirect_stdout(буфер):
            код = check_app_scopes.проверить(папка)
        if код == 0:
            print("  ✓ права листинга сходятся с тем, что зовёт окно")
        else:
            ошибки.append("права не сходятся: " + буфер.getvalue().strip().replace("\n", " | "))

        ns = {}
        exec((папка / "experts" / "probe_ocr_state.py").read_text(), ns)
        с = ns["probe_ocr_state"]()
        нужно = {"enabled", "active_version", "last_run", "last_result", "last_error", "schedules", "checked_at", "bound_to"}
        if нужно <= set(с) and {"hosting_profile", "host", "platform_profile_id", "account_ref", "agent_ids", "since"} <= set(с["bound_to"]):
            print("  ✓ эксперт состояния отдаёт все поля схемы, неизвестное — null")
        else:
            ошибки.append("эксперт состояния отдаёт не все поля схемы")

        # Модуль вне реестра — отказ без флага, сборка с флагом.
        план2 = окно.пример_плана()
        план2["modules"] = ["unknown_module"]
        папка2 = корень / "apps" / "probe2"
        папка2.mkdir()
        (папка2 / "app.json").write_text(json.dumps(план2, ensure_ascii=False))
        try:
            собрать(папка2, реестр)
            ошибки.append("модуль вне реестра НЕ отвергнут")
        except Отказ:
            print("  ✓ модуль вне реестра — отказ, пока нет флага --без-паспорта")
        if собрать(папка2, реестр, без_паспорта_ок=True)["без_паспорта"] == ["unknown_module"]:
            print("  ✓ с флагом собирается и честно называет модуль без паспорта")
        else:
            ошибки.append("флаг --без-паспорта не назвал модуль")

        # Детерминизм: два прогона — один и тот же каталог (кроме иконки, она не пересобирается).
        было = {п.name: п.read_bytes() for п in папка.iterdir() if п.is_file() and p_ok(п)}
        собрать(папка, реестр)
        стало = {п.name: п.read_bytes() for п in папка.iterdir() if п.is_file() and p_ok(п)}
        if было == стало:
            print("  ✓ сборка воспроизводима: повтор даёт те же файлы")
        else:
            ошибки.append("повторная сборка меняет файлы: " + ", ".join(k for k in было if было[k] != стало.get(k)))

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def p_ok(п: pathlib.Path) -> bool:
    return п.suffix in (".html", ".json", ".yaml", ".md", ".py")


def main(аргументы) -> int:
    if "--selftest" in аргументы:
        return selftest()
    без = "--без-паспорта" in аргументы
    реестр_путь = pathlib.Path(os.environ.get("EXTELLA_DECLARED_REGISTRY") or РЕЕСТР)
    if "--реестр" in аргументы:
        реестр_путь = pathlib.Path(аргументы[аргументы.index("--реестр") + 1]).expanduser()
    пути = [а for а in аргументы if not а.startswith("--") and str(а) != str(реестр_путь)]
    if not пути:
        print(__doc__)
        return 2
    папка = pathlib.Path(пути[0]).expanduser()
    if not (папка / "app.json").exists():
        print(f"ОТКАЗ: нет {папка / 'app.json'} — образец: python3 tools/окно_из_форм.py --пример")
        return 2
    if not реестр_путь.exists():
        print(f"ОТКАЗ: нет реестра паспортов {реестр_путь}")
        return 2
    try:
        итог = собрать(папка, json.loads(реестр_путь.read_text(encoding="utf-8")), без)
    except Отказ as о:
        print(f"ОТКАЗ: {о}")
        return 1
    print(f"  ✓ собрано в {итог['папка']}: экранов {итог['экранов']}, модулей {len(итог['модули'])}, иконка — {итог['иконка']}")
    if итог["без_паспорта"]:
        print(f"  ~ без паспорта: {', '.join(итог['без_паспорта'])}")
    if итог["паспорт_не_готов"]:
        print(f"  ~ паспорт не проходит гейт у: {', '.join(итог['паспорт_не_готов'])}")
    print("  дальше: python3 tools/provision_modules.py " + str(папка) +
          " · python3 tools/check_app_from_modules.py " + str(папка))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
