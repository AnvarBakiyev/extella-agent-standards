#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Номера секций канона уникальны: два чата не должны занять один H молча.

ЗАЧЕМ. 21.08.2026 несколько чатов одновременно вносили находки в
DEPLOY_REQUIREMENTS.md, каждый назначал H-номер сам — и H34–H39 задвоились,
каждый номер стал означать две разные вещи. Это тот же класс, что «две копии
разъезжаются»: файл общий, а порядковый номер каждый ставит по памяти.

Проверка простая и злая: если один `### H<N>.` встречается дважды — красный.
Суффиксы-поправки (`H19-бис`, `H38-П`) разрешены: это осознанное дополнение к
номеру, а не столкновение.

  python3 check_canon_numbers.py
  python3 check_canon_numbers.py --selftest

Коды выхода: 0 — номера уникальны, 1 — есть дубль, 2 — файл не прочитан.
"""
import pathlib
import re
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parents[1]
ФАЙЛ = КОРЕНЬ / "DEPLOY_REQUIREMENTS.md"
# H<число>. — базовый номер. H19-бис / H38-П — намеренная поправка, не дубль.
БАЗОВЫЙ = re.compile(r"^### (H\d+)\.\s", re.M)


def дубли(текст: str) -> dict:
    from collections import defaultdict
    счёт = defaultdict(int)
    for м in БАЗОВЫЙ.finditer(текст):
        счёт[м.group(1)] += 1
    return {н: к for н, к in счёт.items() if к > 1}


def следующий_свободный(текст: str) -> int:
    номера = [int(м.group(1)[1:]) for м in БАЗОВЫЙ.finditer(текст)]
    return (max(номера) + 1) if номера else 1


def свободный_по_веткам() -> int:
    """Свободный номер H с учётом ЛЕТЯЩИХ веток origin, а не только main.

    Гейт ловит дубль в слитом файле. Но два чата в параллельных ветках берут один
    номер по памяти, и столкновение всплывает лишь на merge (замер 22.08.2026:
    H51–H53 заняты одной веткой, гейт main молчал). Этот режим смотрит номера во
    ВСЕХ ветках origin и отдаёт число выше всех занятых — его чат и берёт.
    """
    import subprocess
    номера = set()
    try:
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=str(КОРЕНЬ), timeout=60)
        ветки = subprocess.run(["git", "branch", "-r"], cwd=str(КОРЕНЬ),
                               capture_output=True, text=True).stdout.split()
        for в in ветки:
            в = в.strip()
            if not в.startswith("origin/") or в.endswith("HEAD"):
                continue
            вывод = subprocess.run(
                ["git", "grep", "-hoE", r"^### H[0-9]+\.", в, "--", "DEPLOY_REQUIREMENTS.md"],
                cwd=str(КОРЕНЬ), capture_output=True, text=True).stdout
            for м in re.finditer(r"H(\d+)", вывод):
                номера.add(int(м.group(1)))
    except Exception:
        pass
    # плюс локальный файл
    for м in БАЗОВЫЙ.finditer(ФАЙЛ.read_text(encoding="utf-8")):
        номера.add(int(м.group(1)[1:]))
    return (max(номера) + 1) if номера else 1


def main(аргументы: list) -> int:
    if "--резерв" in аргументы:
        print(f"H{свободный_по_веткам()}")
        return 0

    if "--selftest" in аргументы:
        чисто = "### H1. А\n\n### H2. Б\n\n### H2-бис. поправка\n"
        грязно = "### H1. А\n\n### H2. Б\n\n### H2. В\n"
        беды = []
        if дубли(чисто):
            беды.append(f"уникальные номера объявлены дублями: {дубли(чисто)}")
        if "H2-бис" in str(дубли(чисто)):
            беды.append("суффикс-поправка принят за дубль")
        if дубли(грязно) != {"H2": 2}:
            беды.append(f"настоящий дубль не пойман: {дубли(грязно)}")
        if следующий_свободный(чисто) != 3:
            беды.append("следующий свободный номер посчитан неверно")
        for б in беды:
            print("  ✗", б)
        print("selftest:", "провален" if беды else "пройден")
        return 1 if беды else 0

    if not ФАЙЛ.exists():
        print("нет", ФАЙЛ)
        return 2
    текст = ФАЙЛ.read_text(encoding="utf-8")
    д = дубли(текст)
    if not д:
        print(f"номера канона уникальны (следующий свободный — H{следующий_свободный(текст)})")
        return 0
    print("ДУБЛИ НОМЕРОВ КАНОНА — один H означает две разные вещи:")
    for н in sorted(д, key=lambda x: int(x[1:])):
        названия = re.findall(rf"^### {н}\.\s*(.+)$", текст, re.M)
        print(f"  ✗ {н} ×{д[н]}:")
        for назв in названия:
            print(f"      • {назв[:70]}")
    print(f"\nследующий свободный номер — H{следующий_свободный(текст)}.")
    print("Чинить: поздним по коммиту находкам дать свободные номера; правит один "
          "человек, чтобы не столкнуть заново.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
