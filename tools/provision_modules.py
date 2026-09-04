#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Провижининг модулей: эксперты модулей становятся видны агенту приложения.

ЗАЧЕМ. Приложение из модулей работает через своего агента: окно зовёт `app-agent/run`, а
тот запускает эксперт по имени в скоупе агента. Если эксперт агенту не виден, окно откроется
целым, а каждая кнопка ответит «эксперт не найден». До 04.09.2026 единственный код, который
клал экспертов в скоуп агента, жил в `agent_forge` и заодно перезаписывал `instructions`
агента целиком — у любой копии Qwen там лежит ядро платформы на сто девять тысяч знаков.

Правила этого инструмента, каждое куплено поломкой:
  * `instructions` агента не пишутся никогда;
  * эксперт модуля обычно глобальный и уже виден — тогда копия не делается: одно имя в двух
    скоупах даёт недетерминированный запуск (канон платформы, правило 3);
  * копия делается только для невидимого, под заголовком агента приложения, и тут же
    перечитывается: «успешно» от платформы фактом не является (правило 5);
  * собственные эксперты приложения (`experts/*.py` в каталоге) пишутся в скоуп агента.

Отчёт ложится в `provisioning.json` рядом с планом — его читает гейт приложения.

    python3 tools/provision_modules.py apps/priemka_schetov
    python3 tools/provision_modules.py apps/priemka_schetov --проверить     # только чтение
    python3 tools/provision_modules.py --selftest

Коды выхода: 0 — все эксперты видны агенту, 1 — что-то не видно или не записалось,
2 — план или реестр не прочитаны.
"""
import datetime
import json
import os
import pathlib
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
import platform_client as пк  # noqa: E402

КАНОН_АГЕНТ = "agent_extella_default"          # откуда читается каноническая копия эксперта
РЕЕСТР = pathlib.Path.home() / "extella_wizard" / "registry" / "capabilities_declared.json"


def описание(текст: str) -> str:
    for строка in текст.splitlines()[:6]:
        if строка.startswith("# description:"):
            return строка.split(":", 1)[1].strip()
    return ""


class Платформа:
    """Транспорт. В самопроверке подменяется поддельным — сеть гейту не нужна."""

    def __init__(self, запрос=None):
        self._запрос = запрос or пк.запрос
        self._токен = None

    def _заголовки(self, agent_id: str) -> dict:
        if self._токен is None:
            self._токен = пк.токен()
        return {"X-Auth-Token": self._токен, "X-Profile-Id": "default", "X-Agent-Id": agent_id}

    def получить(self, имя: str, agent_id: str, глобально: bool) -> str:
        """Код эксперта, как его видит агент, или пустая строка."""
        код, сырое = self._запрос(пк.ЯДРО, "/api/expert/get", тело={"name": имя, "global": глобально},
                                  заголовки=self._заголовки(agent_id), таймаут=60)
        if код != 200 or not str(сырое).strip().startswith("{"):
            return ""
        return str(json.loads(сырое).get("expert_code") or "")

    def сохранить(self, имя: str, оп: str, код_эксперта: str, agent_id: str) -> tuple:
        код, сырое = self._запрос(пк.ЯДРО, "/api/expert/save",
                                  тело={"name": имя, "description": оп, "code": код_эксперта,
                                        "cspl": "fython", "global": False},
                                  заголовки=self._заголовки(agent_id), таймаут=90)
        return код, str(сырое)[:200]


def эксперты_модулей(модули: list, реестр: dict) -> tuple:
    """Имена экспертов по идентификаторам модулей из реестра паспортов.

    Модуль, которого в реестре нет, считается именем эксперта и помечается: гейт решит,
    допустимо ли это на стадии стройки.
    """
    по_id = {}
    for а in (реестр.get("automations") or []):
        if а.get("automation_id"):
            по_id[а["automation_id"]] = а
        for имя in (а.get("experts") or []):
            по_id.setdefault(имя, а)
    имена, без_паспорта = [], []
    for м in модули:
        запись = по_id.get(м)
        if not запись:
            без_паспорта.append(м)
            имена.append(м)
            continue
        for имя in (запись.get("experts") or [м]):
            if имя not in имена:
                имена.append(имя)
    return имена, без_паспорта


def провести(папка: pathlib.Path, платформа: Платформа, реестр: dict, только_чтение: bool = False) -> dict:
    план = json.loads((папка / "app.json").read_text(encoding="utf-8"))
    agent_id = str(план.get("agent_id") or "")
    if not agent_id.startswith("agent_"):
        raise пк.Отказ("в app.json нет agent_id вида agent_… — агент приложения создаётся до провижининга")
    if agent_id == КАНОН_АГЕНТ:
        raise пк.Отказ("agent_extella_default — основной агент, в его скоуп приложение не ставится")
    имена, без_паспорта = эксперты_модулей(план.get("modules") or [], реестр)
    строки = []

    for имя in имена:
        видно = платформа.получить(имя, agent_id, True)
        строка = {"expert": имя, "kind": "module", "visible_before": bool(видно), "action": "none",
                  "verified": bool(видно)}
        if not видно and not только_чтение:
            канон = платформа.получить(имя, КАНОН_АГЕНТ, True)
            if not канон:
                строка["action"] = "missing"
                строка["note_ru"] = "эксперта нет ни у агента приложения, ни в общем пространстве"
                строка["note_en"] = "the expert exists neither for the app agent nor globally"
            else:
                код, сырое = платформа.сохранить(имя, описание(канон) or имя, канон, agent_id)
                строка["action"] = "copied"
                if код != 200:
                    строка["note_ru"] = f"платформа не приняла запись: HTTP {код} {сырое}"
                    строка["note_en"] = f"the platform rejected the save: HTTP {код} {сырое}"
                else:
                    строка["verified"] = платформа.получить(имя, agent_id, False).strip() == канон.strip()
                    if not строка["verified"]:
                        строка["note_ru"] = "после записи содержимое отличается от канона"
                        строка["note_en"] = "after saving the content differs from the canon"
        строки.append(строка)

    for путь in sorted((папка / "experts").glob("*.py")) if (папка / "experts").is_dir() else []:
        имя, код_файла = путь.stem, путь.read_text(encoding="utf-8").rstrip()
        оп = описание(код_файла)
        строка = {"expert": имя, "kind": "own", "visible_before": False, "action": "none", "verified": False}
        if not оп:
            строка["note_ru"] = "нет строки # description: — агент не поймёт, зачем эксперт"
            строка["note_en"] = "no # description: line — the agent cannot tell what the expert is for"
        elif только_чтение:
            строка["verified"] = платформа.получить(имя, agent_id, False).strip() == код_файла
            строка["visible_before"] = строка["verified"]
        else:
            код, сырое = платформа.сохранить(имя, оп, код_файла, agent_id)
            строка["action"] = "saved"
            if код != 200:
                строка["note_ru"] = f"платформа не приняла запись: HTTP {код} {сырое}"
                строка["note_en"] = f"the platform rejected the save: HTTP {код} {сырое}"
            else:
                строка["verified"] = платформа.получить(имя, agent_id, False).strip() == код_файла
                if not строка["verified"]:
                    строка["note_ru"] = "после записи содержимое отличается от файла"
                    строка["note_en"] = "after saving the content differs from the file"
        строки.append(строка)

    отчёт = {"schema": "extella.app_provisioning.v1", "agent_id": agent_id,
             "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "read_only": только_чтение, "modules_without_passport": без_паспорта,
             "experts": строки, "all_verified": all(с["verified"] for с in строки),
             "instructions_touched": False}
    return отчёт


def _печать(отчёт: dict) -> None:
    for с in отчёт["experts"]:
        знак = "✓" if с["verified"] else "✗"
        print(f"  {знак} {с['expert']} ({с['kind']}): до — {'виден' if с['visible_before'] else 'не виден'}, "
              f"действие — {с['action']}" + (f" — {с['note_ru']}" if с.get("note_ru") else ""))
    if отчёт["modules_without_passport"]:
        print(f"  ~ без паспорта в реестре: {', '.join(отчёт['modules_without_passport'])}")


def selftest() -> int:
    import tempfile
    ошибки = []
    хранилище = {("agent_extella_default", "toolkit_probe"): "# description: проба\ndef toolkit_probe(): return 1"}
    записи = []
    инструкции_тронуты = []

    def поддельный_запрос(база, путь, *, тело=None, заголовки=None, таймаут=0, **_):
        агент = заголовки["X-Agent-Id"]
        if путь == "/api/expert/get":
            # Подделка видит эксперт только в скоупе агента из заголовка: так проверяется
            # именно невидимость, а не удача общего чтения.
            код = хранилище.get((агент, тело["name"]))
            return (200, json.dumps({"expert_code": код or ""})) if код else (404, "{}")
        if путь == "/api/expert/save":
            записи.append((агент, тело["name"], тело["global"]))
            хранилище[(агент, тело["name"])] = тело["code"]
            return 200, json.dumps({"status": "success"})
        if путь == "/api/agent/update":
            инструкции_тронуты.append(тело)
            return 200, "{}"
        return 500, "неизвестный путь"

    платформа = Платформа(запрос=поддельный_запрос)
    платформа._токен = "проба"
    реестр = {"automations": [{"automation_id": "toolkit_probe", "experts": ["toolkit_probe"]}]}
    with tempfile.TemporaryDirectory() as tmp:
        папка = pathlib.Path(tmp)
        (папка / "experts").mkdir()
        (папка / "experts" / "probe_state.py").write_text("# description: состояние пробы\ndef probe_state(): return {}\n")
        (папка / "app.json").write_text(json.dumps({"agent_id": "agent_app", "modules": ["toolkit_probe", "unknown_thing"]}))

        # 1. Невидимый глобальный эксперт копируется под заголовком агента приложения и сверяется.
        отчёт = провести(папка, платформа, реестр)
        строки = {с["expert"]: с for с in отчёт["experts"]}
        if строки["toolkit_probe"]["action"] == "copied" and строки["toolkit_probe"]["verified"] \
                and ("agent_app", "toolkit_probe", False) in записи:
            print("  ✓ невидимый эксперт модуля скопирован в скоуп агента приложения и сверен")
        else:
            ошибки.append("копия невидимого эксперта не сделана или не сверена")
        if строки["probe_state"]["action"] == "saved" and строки["probe_state"]["verified"]:
            print("  ✓ собственный эксперт приложения записан в скоуп агента и сверен")
        else:
            ошибки.append("собственный эксперт не записан")
        if строки["unknown_thing"]["action"] == "missing" and not отчёт["all_verified"] \
                and отчёт["modules_without_passport"] == ["unknown_thing"]:
            print("  ✓ модуль, которого нет нигде, назван, а не выдуман; отчёт честно не «всё верно»")
        else:
            ошибки.append("отсутствующий модуль не пойман")

        # 2. Повторный прогон: эксперт уже виден — копии нет (одно имя — один скоуп).
        было = len(записи)
        отчёт2 = провести(папка, платформа, реестр)
        if {с["expert"]: с for с in отчёт2["experts"]}["toolkit_probe"]["action"] == "none" \
                and not [з for з in записи[было:] if з[1] == "toolkit_probe"]:
            print("  ✓ видимый эксперт не копируется повторно")
        else:
            ошибки.append("видимый эксперт скопирован второй раз — дубль имени")

        # 3. Инструкции агента не тронуты ни разу.
        if not инструкции_тронуты and отчёт2["instructions_touched"] is False:
            print("  ✓ instructions агента не записывались")
        else:
            ошибки.append("инструмент записал instructions агента")

        # 4. Основной агент как цель — отказ.
        (папка / "app.json").write_text(json.dumps({"agent_id": "agent_extella_default", "modules": ["toolkit_probe"]}))
        try:
            провести(папка, платформа, реестр)
            ошибки.append("установка в скоуп основного агента НЕ отвергнута")
        except пк.Отказ:
            print("  ✓ основной агент как цель — отказ")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main(аргументы) -> int:
    if "--selftest" in аргументы:
        return selftest()
    только_чтение = "--проверить" in аргументы
    пути = [а for а in аргументы if not а.startswith("--")]
    if not пути:
        print(__doc__)
        return 2
    папка = pathlib.Path(пути[0]).expanduser()
    реестр_путь = pathlib.Path(os.environ.get("EXTELLA_DECLARED_REGISTRY") or РЕЕСТР)
    if not (папка / "app.json").exists():
        print(f"ОТКАЗ: нет {папка / 'app.json'}")
        return 2
    if not реестр_путь.exists():
        print(f"ОТКАЗ: нет реестра паспортов {реестр_путь} — собери его: "
              "python3 tools/build_capability_registry.py --roots-file config_registry_roots.txt -o <этот путь>")
        return 2
    try:
        отчёт = провести(папка, Платформа(), json.loads(реестр_путь.read_text(encoding="utf-8")), только_чтение)
    except пк.Отказ as о:
        print(f"ОТКАЗ: {о}")
        return 1
    _печать(отчёт)
    (папка / "provisioning.json").write_text(json.dumps(отчёт, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("  ✓ все эксперты видны агенту " if отчёт["all_verified"] else "  ✗ не все эксперты видны агенту ")
          + отчёт["agent_id"] + f" · отчёт: {папка / 'provisioning.json'}")
    return 0 if отчёт["all_verified"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
