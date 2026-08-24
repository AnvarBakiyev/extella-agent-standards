#!/usr/bin/env python3
"""Сохранить всю работу Extella в облако — одной командой.

    python3 tools/save_all.py                  # сохранить и отправить
    python3 tools/save_all.py --посмотреть     # только показать, что изменилось
    python3 tools/save_all.py --selftest

ЗАЧЕМ. Наша работа живёт в четырёх папках, и в каждой git — свой. Чтобы
сохранить всё, человеку пришлось бы помнить четыре пути и по три команды в
каждом. Это не работа человека; это работа инструмента.

ЧЕСТНОСТЬ ВЫВОДА. Сказать «сохранено» и промолчать о папке, где отправка не
прошла, — худшее, что может сделать такой инструмент: человек уйдёт спокойным,
а копии не будет. Поэтому каждая папка отчитывается отдельно, а итог называет
и удачи, и беды.

ЧЕГО НЕ ДЕЛАЕТ. Не трогает данные и секреты — они и так вне git по правилам
`.gitignore` каждой папки. Не создаёт репозитории и не меняет их видимость:
это решения владельца, принимаемые один раз и руками.
"""

import argparse
import datetime
import pathlib
import subprocess
import sys

ДОМ = pathlib.Path.home()
ПАПКИ = [
    ДОМ / "extella-plugins",
    ДОМ / "extella-cabinet",
    ДОМ / "Documents" / "Extella" / "extella-agent-standards",
    ДОМ / "Documents" / "Extella" / "extella-core-portal",
]


def _git(папка: pathlib.Path, *арг, таймаут: int = 180):
    return subprocess.run(["git", "-C", str(папка), *арг],
                          capture_output=True, text=True, timeout=таймаут)


def состояние(папка: pathlib.Path) -> dict:
    """Что в папке: сколько правок, есть ли облако, отстаёт ли оно."""
    если = {"папка": папка.name, "есть": папка.is_dir()}
    if not если["есть"]:
        return если
    если["под_git"] = _git(папка, "rev-parse", "--git-dir").returncode == 0
    if not если["под_git"]:
        return если
    правки = _git(папка, "status", "--porcelain").stdout.strip()
    если["правок"] = len([с for с in правки.split("\n") if с.strip()])
    если["облако"] = bool(_git(папка, "remote").stdout.strip())
    if если["облако"]:
        _git(папка, "fetch", "--quiet", таймаут=120)
        неотправлено = _git(папка, "log", "--oneline", "@{u}..HEAD").stdout.strip()
        если["неотправлено"] = len([с for с in неотправлено.split("\n") if с.strip()])
    return если


def сохранить(папка: pathlib.Path, подпись: str) -> dict:
    """Сохранить правки папки и отправить в облако. Возвращает, что вышло."""
    итог = состояние(папка)
    if not итог.get("есть") or not итог.get("под_git"):
        итог["что"] = "пропущена: не папка Extella под git"
        return итог
    if итог["правок"]:
        _git(папка, "add", "-A")
        # Имя и почта берутся из настроек git человека; если их нет, ставим
        # свои — иначе коммит просто не создастся, и человек не поймёт почему.
        кто = _git(папка, "config", "user.email").stdout.strip()
        доп = [] if кто else ["-c", "user.name=Anvar Bakiyev",
                              "-c", "user.email=abakiyev@gmail.com"]
        зап = subprocess.run(["git", "-C", str(папка), *доп, "commit", "-q",
                              "-m", подпись], capture_output=True, text=True, timeout=180)
        if зап.returncode != 0:
            итог["что"] = f"не сохранилось: {(зап.stderr or зап.stdout)[:160]}"
            итог["беда"] = True
            return итог
    if not итог.get("облако"):
        итог["что"] = (f"сохранено на диске ({итог['правок']} правок), "
                       f"но облака у папки нет")
        return итог
    отпр = _git(папка, "push", "--quiet", таймаут=300)
    if отпр.returncode != 0:
        итог["что"] = f"в облако НЕ ушло: {(отпр.stderr or '')[:160]}"
        итог["беда"] = True
        return итог
    итог["что"] = (f"сохранено и отправлено: правок {итог['правок']}"
                   if итог["правок"] else "нечего сохранять, облако уже в курсе")
    return итог


def _самопроверка() -> int:
    ошибки = []
    с = состояние(ДОМ / "нет-такой-папки-extella")
    if с.get("есть") is False:
        print("  ✓ отсутствующая папка не роняет инструмент")
    else:
        ошибки.append("отсутствующая папка обработана неверно")
    с = состояние(pathlib.Path("/tmp"))
    if с.get("под_git") is False:
        print("  ✓ папка без git узнаётся и пропускается")
    else:
        ошибки.append("папка без git не распознана")
    свои = [п for п in ПАПКИ if п.is_dir()]
    print(f"  · папок Extella на этой машине: {len(свои)} из {len(ПАПКИ)}")
    for п in свои:
        с = состояние(п)
        облако = "облако есть" if с.get("облако") else "БЕЗ ОБЛАКА"
        print(f"    {п.name}: правок {с.get('правок', '?')}, {облако}")
    for о in ошибки:
        print(f"  ✗ {о}")
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("--посмотреть", dest="посмотреть", action="store_true",
                   help="ничего не менять, только показать, что изменилось")
    р.add_argument("--подпись", default="",
                   help="чем подписать сохранение (по умолчанию — дата и время)")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return _самопроверка()

    подпись = а.подпись or (
        "Сохранение работы " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))
    беды = []
    print()
    for папка in ПАПКИ:
        if а.посмотреть:
            с = состояние(папка)
            if not с.get("есть"):
                continue
            хвост = ""
            if с.get("облако") and с.get("неотправлено"):
                хвост = f", в облако не ушло: {с['неотправлено']}"
            print(f"  {папка.name}: правок {с.get('правок', '—')}{хвост}")
            continue
        итог = сохранить(папка, подпись)
        if not итог.get("есть"):
            continue
        знак = "✗" if итог.get("беда") else "✓"
        print(f"  {знак} {папка.name}: {итог.get('что')}")
        if итог.get("беда"):
            беды.append(папка.name)
    print()
    if а.посмотреть:
        print("  Это был просмотр — ничего не менялось.")
        return 0
    if беды:
        print(f"  ИТОГ: не всё сохранилось — {', '.join(беды)}. "
              f"Скажите чату, разберём.")
        return 1
    print("  ИТОГ: вся работа сохранена и лежит в облаке.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
