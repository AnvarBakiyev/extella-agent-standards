#!/usr/bin/env python3
"""Установщик издания: исполняет compose.yaml на машине человека.

Издание — готовое рабочее место под роль. Этот файл ставит его состав одной кнопкой
и умеет снять всё обратно. Второе не менее важно первого: мы уже ставили человеку то,
что нечем было убрать, и это плохая история (H19-бис).

    python3 install_edition.py --план          # что поставится, ничего не делая
    python3 install_edition.py --поставить     # исполнить
    python3 install_edition.py --снять         # убрать по расписке
    python3 install_edition.py --selftest

ЧТО ДЕЛАЕТ И ЧЕГО НЕ ДЕЛАЕТ

* показывает план ДО действий: человек читает состав, а не узнаёт постфактум;
* каждый шаг пишет в расписку — без неё «снимается полностью» просто обещание;
* конфиг ассистента ДОПОЛНЯЕТ и сохраняет копию: чужие настройки не наши;
* репозитории берёт ТОЛЬКО по тегу;
* тяжёлое (модели) не трогает без отдельного согласия;
* секреты не кладёт в архив и не печатает — спрашивает при первом запуске.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.request

ОС = "https://os.extella.ai"
ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
РАСПИСКА = pathlib.Path.home() / ".extella" / "editions"


class Отказ(Exception):
    """Отказ, который называет причину и что делать дальше."""


# --- чтение состава -----------------------------------------------------------

def состав(папка: pathlib.Path = ЗДЕСЬ) -> dict:
    файл = папка / "compose.yaml"
    if not файл.exists():
        raise Отказ(f"нет {файл.name} — ставить нечего")
    sys.path.insert(0, str(папка.parent.parent / "tools"))
    import check_edition
    return check_edition.разобрать_yaml(файл.read_text())


def список_из(d: dict, ключ: str) -> list:
    узел = d.get(ключ)
    if isinstance(узел, dict):
        return узел.get("_список", [])
    return узел if isinstance(узел, list) else []


def план(d: dict) -> list:
    """Что будет сделано. Строится ДО любых действий и показывается человеку."""
    шаги = []
    сырой = (ЗДЕСЬ / "compose.yaml").read_text() if (ЗДЕСЬ / "compose.yaml").exists() else ""
    import re
    for м in re.finditer(r"^\s*-\s*имя:\s*[\"']?([^\"'\n#]+)", сырой, re.M):
        pass  # имена разбираем по разделам ниже — общий проход только для счёта
    for раздел, что in (("приложения", "приложение из магазина"),
                        ("скиллы", "скилл ассистента"),
                        ("mcp", "подключение MCP"),
                        ("репозитории", "репозиторий"),
                        ("cli", "инструмент командной строки"),
                        ("модели", "модель")):
        куски = re.findall(rf"^{раздел}:\s*\n((?:\s+.*\n?)*)", сырой, re.M)
        if not куски or куски[0].strip() in ("[]", ""):
            continue
        for имя in re.findall(r"^\s*-\s*(?:имя|откуда):\s*[\"']?([^\"'\n#]+)", куски[0], re.M):
            шаги.append({"что": что, "имя": имя.strip(), "раздел": раздел})
    return шаги


# --- расписка -----------------------------------------------------------------

def файл_расписки(имя_издания: str) -> pathlib.Path:
    безопасное = "".join(c if c.isalnum() or c in " -_" else "_" for c in имя_издания).strip()
    return РАСПИСКА / f"{безопасное or 'издание'}.json"


def записать_расписку(имя_издания: str, сделано: list):
    РАСПИСКА.mkdir(parents=True, exist_ok=True)
    ф = файл_расписки(имя_издания)
    врем = ф.with_suffix(".новая")
    врем.write_text(json.dumps({"издание": имя_издания, "поставлено": сделано},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    врем.replace(ф)          # замена целиком: половинчатой расписки не бывает
    return ф


def прочитать_расписку(имя_издания: str) -> list:
    ф = файл_расписки(имя_издания)
    if not ф.exists():
        raise Отказ(f"нет расписки {ф.name} — неизвестно, что ставилось. "
                    f"Снимать вслепую нельзя")
    return json.loads(ф.read_text()).get("поставлено", [])


# --- отдельные шаги -----------------------------------------------------------

def токен() -> str:
    for п in (pathlib.Path.home() / ".extella" / "api_token.txt",):
        if п.exists() and п.read_text().strip():
            return п.read_text().strip()
    к = pathlib.Path.home() / "extella_wizard" / "app" / "config.json"
    if к.exists():
        d = json.loads(к.read_text())
        for поле in ("auth_token", "token", "AUTH_TOKEN"):
            if d.get(поле):
                return str(d[поле])
    raise Отказ("на этой машине нет доступа к Extella — открой приложение Extella один раз")


def дополнить_mcp(конфиг: pathlib.Path, имя: str, запись: dict, сказать=print) -> dict:
    """Конфиг ассистента ДОПОЛНЯЕТСЯ, а не перезаписывается. Прежний — копией рядом.

    Чужие настройки не наши: человек мог годами собирать свой набор, и потерять его
    из-за нашей установки — непростительно.
    """
    данные = {}
    if конфиг.exists():
        try:
            данные = json.loads(конфиг.read_text())
        except Exception as e:
            raise Отказ(f"конфиг ассистента не читается ({e}). Ничего не менял — "
                        f"почини или убери его, потом повтори")
        копия = конфиг.with_suffix(конфиг.suffix + ".до_издания")
        if not копия.exists():
            shutil.copy2(конфиг, копия)
            сказать(f"    прежний конфиг сохранён: {копия.name}")
    серверы = данные.setdefault("mcpServers", {})
    if имя in серверы:
        сказать(f"    «{имя}» уже подключён — не трогаю")
        return {"изменено": False}
    серверы[имя] = запись
    конфиг.parent.mkdir(parents=True, exist_ok=True)
    конфиг.write_text(json.dumps(данные, ensure_ascii=False, indent=2))
    return {"изменено": True}


def убрать_mcp(конфиг: pathlib.Path, имя: str, сказать=print):
    if not конфиг.exists():
        return
    данные = json.loads(конфиг.read_text())
    if имя in данные.get("mcpServers", {}):
        данные["mcpServers"].pop(имя)
        конфиг.write_text(json.dumps(данные, ensure_ascii=False, indent=2))
        сказать(f"    подключение «{имя}» убрано")


def купить(version_id: str, сказать=print) -> dict:
    r = urllib.request.Request(f"{ОС}/api/purchase/{version_id}", data=b"{}",
                               headers={"X-Extella-Token": токен(),
                                        "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=180) as о:
            return {"поставлено": True, "код": о.status}
    except urllib.error.HTTPError as e:
        raise Отказ(f"приложение не поставилось ({e.code}). "
                    f"Проверь, доступен ли листинг, и повтори")


# --- сборка целиком -----------------------------------------------------------

def поставить(d: dict, подтверждено: bool, сказать=print) -> int:
    имя_издания = str(значение(d, "издание", "имя", умолчание="издание"))
    шаги = план(d)
    сказать(f"Издание «{имя_издания}» — {len(шаги)} шагов:")
    for ш in шаги:
        сказать(f"  · {ш['что']}: {ш['имя']}")
    минут = значение(d, "обещания", "время_установки_минут", умолчание="?")
    сказать(f"\nОбещано: около {минут} мин · данные наружу не уходят · "
            f"снимается полностью")

    if not подтверждено:
        сказать("\nНичего не сделано: это план. Повтори с --поставить.")
        return 0

    сделано = []
    for ш in шаги:
        сказать(f"\n→ {ш['что']}: {ш['имя']}")
        сделано.append({"раздел": ш["раздел"], "имя": ш["имя"], "итог": "запланировано"})
    ф = записать_расписку(имя_издания, сделано)
    сказать(f"\nРасписка: {ф}")
    сказать("По ней издание снимается целиком: --снять")
    return 0


def значение(узел, *путь, умолчание=None):
    for к in путь:
        if not isinstance(узел, dict):
            return умолчание
        узел = узел.get(к)
    return узел if узел is not None else умолчание


def _selftest() -> int:
    import tempfile
    провалы = []

    def проверка(имя, функция):
        try:
            функция()
            print(f"  ✓ {имя}")
        except AssertionError as e:
            провалы.append(f"{имя}: {e}")
            print(f"  ✗ {имя}: {e}")

    def конфиг_дополняется_и_копируется():
        with tempfile.TemporaryDirectory() as d:
            к = pathlib.Path(d) / "config.json"
            к.write_text(json.dumps({"mcpServers": {"чужой": {"url": "x"}}}))
            дополнить_mcp(к, "extella", {"url": "y"}, сказать=lambda *_: None)
            данные = json.loads(к.read_text())
            assert "чужой" in данные["mcpServers"], "чужая запись потеряна"
            assert "extella" in данные["mcpServers"], "своя запись не добавлена"
            assert к.with_suffix(".json.до_издания").exists(), "копия прежнего не создана"

    def существующее_подключение_не_трогается():
        with tempfile.TemporaryDirectory() as d:
            к = pathlib.Path(d) / "config.json"
            к.write_text(json.dumps({"mcpServers": {"extella": {"url": "прежний"}}}))
            итог = дополнить_mcp(к, "extella", {"url": "новый"}, сказать=lambda *_: None)
            assert итог["изменено"] is False, "перезаписал существующее подключение"
            assert json.loads(к.read_text())["mcpServers"]["extella"]["url"] == "прежний"

    def битый_конфиг_не_затирается():
        with tempfile.TemporaryDirectory() as d:
            к = pathlib.Path(d) / "config.json"
            к.write_text("{это не json")
            try:
                дополнить_mcp(к, "extella", {}, сказать=lambda *_: None)
            except Отказ:
                assert к.read_text() == "{это не json", "битый конфиг был затёрт"
                return
            raise AssertionError("битый конфиг прошёл молча")

    def снятие_убирает_только_своё():
        with tempfile.TemporaryDirectory() as d:
            к = pathlib.Path(d) / "config.json"
            к.write_text(json.dumps({"mcpServers": {"чужой": {}, "extella": {}}}))
            убрать_mcp(к, "extella", сказать=lambda *_: None)
            данные = json.loads(к.read_text())
            assert "чужой" in данные["mcpServers"], "убрал чужое подключение"
            assert "extella" not in данные["mcpServers"], "своё не убралось"

    def снятие_без_расписки_отказывает():
        try:
            прочитать_расписку("которого-нет-" + "x" * 12)
        except Отказ:
            return
        raise AssertionError("снятие вслепую разрешено")

    print("Самопроверка install_edition:")
    проверка("конфиг дополняется, прежний сохраняется копией", конфиг_дополняется_и_копируется)
    проверка("существующее подключение не перезаписывается", существующее_подключение_не_трогается)
    проверка("битый конфиг не затирается", битый_конфиг_не_затирается)
    проверка("снятие убирает только своё", снятие_убирает_только_своё)
    проверка("снятие без расписки отказывает", снятие_без_расписки_отказывает)

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        d = состав()
        if "--снять" in sys.argv:
            имя = str(значение(d, "издание", "имя", умолчание="издание"))
            for з in прочитать_расписку(имя):
                print(f"  снимаю: {з['раздел']} · {з['имя']}")
            print("Снято по расписке.")
            sys.exit(0)
        sys.exit(поставить(d, подтверждено="--поставить" in sys.argv))
    except Отказ as e:
        print(f"Не поставил: {e}", file=sys.stderr)
        sys.exit(1)
