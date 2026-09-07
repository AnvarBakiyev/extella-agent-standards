#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Утренняя сводка доски-каталога на стол владельца, без захода на VPS.

Доска считается ночью на стенде (VPS, чистый bench-аккаунт). Эта команда бежит
НА МАШИНЕ ВЛАДЕЛЬЦА: забирает последнюю доску с VPS и кладёт заметку в «Мои
документы» ОС твоим личным токеном (стенду он недоступен — там другой аккаунт).

    python3 morning_board.py            # забрать и положить заметку
    python3 morning_board.py --print    # только показать, без заметки

Токен — из ~/.extella/os_token.txt; в вывод и лог не печатается.
"""
import json
import subprocess
import sys
import urllib.request
import pathlib
import datetime

VPS = "ubuntu@82.115.42.21"
КЛЮЧ = str(pathlib.Path.home() / ".ssh" / "extella_hosting_ed25519")
ОС = "https://os.extella.ai"
ЗНАЧОК = {"зелёный": "🟢", "жёлтый": "🟡", "красный": "🔴", "серый": "⚪"}


def токен() -> str:
    п = pathlib.Path.home() / ".extella" / "os_token.txt"
    if not п.exists():
        raise SystemExit("нет ~/.extella/os_token.txt — открой приложение Extella "
                         "под своим аккаунтом (см. канон H78)")
    return п.read_text().strip()


def доска_с_vps() -> list:
    итог = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-i", КЛЮЧ, VPS,
         "cat ~/extella-bench/board_latest.json"],
        capture_output=True, text=True, timeout=40)
    if итог.returncode != 0:
        raise SystemExit("не забрать доску с VPS: " + итог.stderr[:160])
    return json.loads(итог.stdout)


def свести(доска: list) -> str:
    счёт = {c: sum(1 for x in доска if x["цвет"] == c)
            for c in ("зелёный", "жёлтый", "красный", "серый")}
    дата = datetime.date.today().isoformat()
    строки = [f"Доска приложений — {дата}",
              f"🟢 {счёт['зелёный']}  🟡 {счёт['жёлтый']}  "
              f"🔴 {счёт['красный']}  ⚪ {счёт['серый']}", ""]
    for c in доска:
        if c["цвет"] not in ("красный", "серый", "жёлтый"):
            continue
        строки.append(f"{ЗНАЧОК[c['цвет']]} {c['имя']}")
        if c["цвет"] == "серый":
            строки.append("   прогон сорвался по таймауту — флак стенда, "
                          "перепроверится сам следующей ночью")
            continue
        for б in (c.get("жёсткие") or [])[:1]:
            строки.append("   " + б[:110])
        for б in (c.get("мягкие") or [])[:1]:
            строки.append("   " + б[:110])
    if счёт["красный"] == 0 and счёт["серый"] == 0:
        строки.append("Сломанного нет. Жёлтые — сервис на стенде не поднят или "
                      "оговорка связи, не поломка.")
    return "\n".join(строки)


def положить_заметку(текст: str) -> None:
    з = urllib.request.Request(
        ОС + "/api/desktop/instruction",
        data=json.dumps({"name": "Доска приложений", "text": текст}).encode(),
        headers={"X-Extella-Token": токен(), "Content-Type": "application/json"})
    with urllib.request.urlopen(з, timeout=30) as о:
        d = json.loads(о.read())
    print("заметка положена на стол:", d.get("status", d))


def main(argv) -> int:
    текст = свести(доска_с_vps())
    print(текст)
    if "--print" not in argv:
        print("---")
        положить_заметку(текст)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
