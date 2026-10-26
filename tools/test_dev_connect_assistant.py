#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поведение эксперта dev_connect_assistant без сети: устройство и аккаунт (F06).

ЗАЧЕМ. Аудит Guide 26.10.2026: вызов без адреса уходил на устройство по умолчанию,
и успех с чужого компьютера горел зелёным; рабочий ключ другого аккаунта считался
готовым. Здесь эксперт запускается целиком, сеть подменена: проверяется РЕШЕНИЕ
эксперта, а не наличие слов в исходнике.

    python3 tools/test_dev_connect_assistant.py

Код выхода 0 — все сценарии прошли.
"""
import io
import json
import os
import pathlib
import sys
import tempfile
import urllib.request

ЭКСПЕРТ = pathlib.Path(__file__).resolve().parents[1] / "experts" / "dev_connect_assistant.py"
УСТРОЙСТВО = "11111111-2222-3333-4444-555555555555"
ДРУГОЕ = "99999999-8888-7777-6666-555555555555"
КЛЮЧ = "k-existing-0000-1111"


class Ответ(io.BytesIO):
    def __init__(self, тело, статус=200):
        super().__init__(json.dumps(тело).encode("utf-8"))
        self.status = статус

    def __enter__(self):
        return self

    def __exit__(self, *а):
        return False


def загрузить():
    пространство = {}
    exec(compile(ЭКСПЕРТ.read_text(encoding="utf-8"), str(ЭКСПЕРТ), "exec"), пространство)
    return пространство["dev_connect_assistant"]


def прогон(агенты_окна, агенты_ключа, **параметры):
    """Один запуск эксперта в чистом HOME с рабочим ключом и device.txt."""
    вызовы = []

    def сеть(запрос, timeout=0):
        адрес, заголовки = запрос.full_url, {к.lower(): з for к, з in запрос.header_items()}
        вызовы.append(адрес)
        if адрес.endswith("/api/agent/list"):
            if "x-app-token" in заголовки:
                return Ответ({"agents": [{"id": а} for а in агенты_окна]})
            return Ответ({"agents": [{"id": а} for а in агенты_ключа]})
        raise AssertionError("неожиданный вызов " + адрес)

    with tempfile.TemporaryDirectory() as дом:
        папка = pathlib.Path(дом) / ".extella"
        папка.mkdir()
        (папка / "device.txt").write_text(УСТРОЙСТВО, encoding="utf-8")
        (папка / "api_token.txt").write_text(КЛЮЧ + "\n", encoding="utf-8")
        было_дом, было_сеть = os.environ.get("HOME"), urllib.request.urlopen
        os.environ["HOME"] = дом
        urllib.request.urlopen = сеть
        try:
            ответ = json.loads(загрузить()(app_token="P" * 60, **параметры))
            ключ_после = (папка / "api_token.txt").read_text(encoding="utf-8").strip()
        finally:
            urllib.request.urlopen = было_сеть
            if было_дом is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = было_дом
    return ответ, вызовы, ключ_после


def main() -> int:
    беды = []

    о, вызовы, ключ = прогон(["agent_A"], ["agent_A"], ожидаемое_устройство=ДРУГОЕ)
    if о.get("код") != "не_то_устройство" or о.get("подключено"):
        беды.append(f"чужое устройство не отвергнуто: {о.get('код')}")
    if вызовы:
        беды.append("при чужом устройстве эксперт ходил в сеть — отказ должен быть до изменений")
    if ключ != КЛЮЧ:
        беды.append("при чужом устройстве ключ на диске изменён")
    print("  ✓ чужое устройство: отказ до любых изменений" if not беды else "  ✗ чужое устройство")

    о, _, _ = прогон(["agent_A", "agent_B"], ["agent_B"], ожидаемое_устройство=УСТРОЙСТВО.upper())
    if о.get("код") != "уже_подключено" or о.get("аккаунт_сверен") is not True:
        беды.append(f"тот же аккаунт и устройство не признаны: {о.get('код')}, {о.get('аккаунт_сверен')}")
    if о.get("устройство") != УСТРОЙСТВО or о.get("версия_эксперта") != 2:
        беды.append("ответ не называет устройство или версию эксперта — окно не сверит")
    print("  ✓ своё устройство и аккаунт: ключ готов, сверка названа")

    о, _, ключ = прогон(["agent_A"], ["agent_Z"])
    if о.get("код") != "чужой_аккаунт" or о.get("подключено"):
        беды.append(f"ключ другого аккаунта выдан за готовый: {о.get('код')}")
    if ключ != КЛЮЧ:
        беды.append("ключ другого аккаунта перезаписан без спроса")
    print("  ✓ ключ другого аккаунта: не готов и не перезаписан без спроса")

    о, _, _ = прогон(["agent_extella_default"], ["agent_extella_default"])
    if о.get("код") != "уже_подключено" or о.get("аккаунт_сверен") is not False:
        беды.append("новый аккаунт без своих агентов: сверка должна быть названа несостоявшейся")
    print("  ✓ сверить не по чему: ключ готов, но аккаунт честно не сверен")

    for б in беды:
        print("  ✗ " + б)
    print("ИТОГ: " + ("провалы есть" if беды else "все сценарии прошли"))
    return 1 if беды else 0


if __name__ == "__main__":
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
