#!/usr/bin/env python3
"""Служба, которая поднимается сама, — одинаково на трёх системах.

    python3 tools/автозапуск.py --selftest
    python3 tools/автозапуск.py --имя tablica --команда "python3 сервер.py --порт 34787"

ЗАЧЕМ. У нас всё держится на маленьких службах: у каждого окна свой прокси. На
Маке они прописаны в LaunchAgents, и это единственное место, которым мы прибиты
к macOS. На чужой машине окна просто не поднимутся — молча, без ошибки: человек
установит приложение и увидит пустоту.

ТРИ СИСТЕМЫ — ТРИ РАЗНЫХ ХОЗЯИНА СЛУЖБ, но обещание одно: «служба живёт, сама
встаёт после перезагрузки, сама поднимается после падения».

  macOS   — launchd, файл в ~/Library/LaunchAgents
  Linux   — systemd пользователя, файл в ~/.config/systemd/user
  Windows — Планировщик заданий, задача с триггером «при входе»

ПОЧЕМУ НЕ «ПРОСТО ЗАПУСТИТЬ ПРОЦЕСС». Запущенный процесс умирает вместе с
терминалом и не переживает перезагрузку. Человек закроет ноутбук, откроет утром
и обнаружит, что половина полки не работает, — а винить будет приложение.
"""

import argparse
import os
import pathlib
import platform
import shlex
import subprocess
import sys

ДОМ = pathlib.Path.home()


def система() -> str:
    """Какая система под нами. Отдельной функцией — чтобы подменять в проверках."""
    з = platform.system().lower()
    if з.startswith("darwin"):
        return "macos"
    if з.startswith("linux"):
        return "linux"
    if з.startswith("windows"):
        return "windows"
    return з or "неизвестно"


# ── macOS ────────────────────────────────────────────────────────────────────
def _plist(имя: str, команда: list[str], журнал: pathlib.Path) -> str:
    арг = "".join(f"<string>{x}</string>" for x in команда)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
            '"-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f'<plist version="1.0"><dict><key>Label</key><string>ai.extella.{имя}</string>'
            f'<key>ProgramArguments</key><array>{арг}</array>'
            '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>'
            f'<key>StandardErrorPath</key><string>{журнал}</string>'
            '</dict></plist>')


def _поставить_macos(имя: str, команда: list[str], журнал: pathlib.Path) -> str:
    папка = ДОМ / "Library" / "LaunchAgents"
    папка.mkdir(parents=True, exist_ok=True)
    файл = папка / f"ai.extella.{имя}.plist"
    файл.write_text(_plist(имя, команда, журнал))
    # bootout/bootstrap, а не kickstart: kickstart НЕ перечитывает файл, и
    # правка настроек молча не доезжает (грабля поймана 22.08.2026).
    метка = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{метка}/ai.extella.{имя}"],
                   capture_output=True)
    итог = subprocess.run(["launchctl", "bootstrap", метка, str(файл)],
                          capture_output=True, text=True)
    if итог.returncode != 0:
        raise RuntimeError(f"launchctl отказал: {(итог.stderr or '')[:200]}")
    return str(файл)


ЛАТИНИЦА = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def безопасное_имя(имя: str) -> str:
    """Имя службы, которое примут все три системы.

    systemd отказывается заводить юнит с кириллицей в имени: «Invalid unit
    name "extella-проба.service"» — замер на живом Linux 23.08.2026. На Маке
    та же строка проходит, поэтому вылезло бы это только у коллеги. Приводим
    имя к латинице тут, в одном месте, а не надеемся, что все имена и так
    латинские.
    """
    низ = (имя or "").strip().lower()
    вышло = "".join(ЛАТИНИЦА.get(з, з) for з in низ)
    вышло = "".join(з if (з.isascii() and (з.isalnum() or з in "-_")) else "-"
                    for з in вышло).strip("-")
    return вышло or "extella"


# ── Linux ────────────────────────────────────────────────────────────────────
def _кавычки(часть: str) -> str:
    """Кавычки только там, где они нужны.

    `shlex.quote` считает небезопасным всё не-ASCII и заковычивает КАЖДЫЙ наш
    аргумент — у нас они сплошь кириллические («--порт», «--папка»). Строка
    остаётся рабочей, но читать её человеку невозможно, а в чужом файле служб
    это первое, куда он посмотрит. Кавычим по делу: пробелы и кавычки.
    """
    if not часть:
        return "''"
    if any(з in часть for з in " \t\n'\"\\$`"):
        return "'" + часть.replace("'", "'\\''") + "'"
    return часть


def _unit(имя: str, команда: list[str]) -> str:
    return (f"[Unit]\nDescription=Extella · {имя}\n\n"
            f"[Service]\nExecStart={' '.join(_кавычки(ч) for ч in команда)}\n"
            "Restart=always\nRestartSec=2\n\n"
            "[Install]\nWantedBy=default.target\n")


def _systemd_доступен() -> str:
    """Есть ли у пользователя своя шина systemd. Пустая строка — есть."""
    итог = subprocess.run(["systemctl", "--user", "is-system-running"],
                          capture_output=True, text=True)
    вывод = (итог.stdout or "") + (итог.stderr or "")
    if "Failed to connect to bus" in вывод or "No medium found" in вывод:
        return вывод.strip().splitlines()[0][:120]
    return ""


def _поставить_linux(имя: str, команда: list[str], журнал: pathlib.Path) -> str:
    беда = _systemd_доступен()
    if беда:
        # Обычный Linux на столе у человека такую шину имеет; нет её на
        # серверах и в контейнерах, где входа в сеанс не происходило. Молчать
        # тут нельзя: служба не встанет, а окно будет «просто не работать».
        raise RuntimeError(
            f"своей службы systemd у пользователя нет ({беда}). Так бывает на "
            f"серверах и в контейнерах: сеанса нет, шину поднимать некому. "
            f"Лечится одной командой администратора: "
            f"loginctl enable-linger $USER — после неё служба встанет и будет "
            f"жить без входа в систему")
    папка = ДОМ / ".config" / "systemd" / "user"
    папка.mkdir(parents=True, exist_ok=True)
    файл = папка / f"extella-{имя}.service"
    файл.write_text(_unit(имя, команда))
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    итог = subprocess.run(["systemctl", "--user", "enable", "--now",
                           f"extella-{имя}.service"], capture_output=True, text=True)
    if итог.returncode != 0:
        raise RuntimeError(f"systemctl отказал: {(итог.stderr or '')[:200]}")
    return str(файл)


# ── Windows ──────────────────────────────────────────────────────────────────
def _поставить_windows(имя: str, команда: list[str], журнал: pathlib.Path) -> str:
    # schtasks — штатный планировщик, есть в любой Windows и не требует
    # установки. Триггер ONLOGON: служба поднимается при входе человека, а не
    # при старте машины, — ей нужен его рабочий стол и его домашняя папка.
    строка = " ".join(f'"{ч}"' if " " in ч else ч for ч in команда)
    задача = f"Extella\\{имя}"
    subprocess.run(["schtasks", "/Delete", "/TN", задача, "/F"], capture_output=True)
    итог = subprocess.run(["schtasks", "/Create", "/TN", задача, "/SC", "ONLOGON",
                           "/RL", "LIMITED", "/F", "/TR", строка],
                          capture_output=True, text=True)
    if итог.returncode != 0:
        raise RuntimeError(f"schtasks отказал: {(итог.stdout or итог.stderr or '')[:200]}")
    subprocess.run(["schtasks", "/Run", "/TN", задача], capture_output=True)
    return задача


СТАВЯТ = {"macos": _поставить_macos, "linux": _поставить_linux,
          "windows": _поставить_windows}


def поставить(имя: str, команда: list[str], журнал: pathlib.Path | None = None) -> str:
    """Прописать службу в хозяина автозапуска текущей системы."""
    с = система()
    if с not in СТАВЯТ:
        raise RuntimeError(
            f"система «{с}» не поддержана: автозапуск умеет macOS, Linux и "
            f"Windows. Служба «{имя}» не поставлена — окно не поднимется само, "
            f"и человек увидит пустоту вместо приложения")
    имя = безопасное_имя(имя)
    журнал = журнал or (ДОМ / "extella-cabinet" / f"{имя}.log")
    журнал.parent.mkdir(parents=True, exist_ok=True)
    return СТАВЯТ[с](имя, команда, журнал)


def снять(имя: str) -> None:
    """Убрать службу. Молча терпим отсутствие — снятие должно быть идемпотентным."""
    имя = безопасное_имя(имя)
    с = система()
    if с == "macos":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/ai.extella.{имя}"],
                       capture_output=True)
        (ДОМ / "Library" / "LaunchAgents" / f"ai.extella.{имя}.plist").unlink(missing_ok=True)
    elif с == "linux":
        subprocess.run(["systemctl", "--user", "disable", "--now",
                        f"extella-{имя}.service"], capture_output=True)
        (ДОМ / ".config" / "systemd" / "user" / f"extella-{имя}.service").unlink(missing_ok=True)
    elif с == "windows":
        subprocess.run(["schtasks", "/Delete", "/TN", f"Extella\\{имя}", "/F"],
                       capture_output=True)


def питон() -> str:
    """Каким питоном запускать службы.

    На Маке у нас прибит python.org-питон; на чужой машине его нет, и жёсткий
    путь превратился бы в «служба не стартует, причина не названа». Берём тот,
    которым запущены сами: он заведомо есть и заведомо той же версии.
    """
    return sys.executable or "python3"


def _самопроверка() -> int:
    ошибки = []
    if система() in ("macos", "linux", "windows"):
        print(f"  ✓ система распознана: {система()}")
    else:
        ошибки.append(f"система не распознана: {система()}")

    # Тексты описаний служб проверяем НА ВСЕХ трёх системах, а не только на
    # своей: иначе ошибка в чужой ветке всплывёт у коллеги, а не у нас.
    п = _plist("проба", ["/usr/bin/python3", "с.py", "--порт", "1"], pathlib.Path("/tmp/п.log"))
    if "<string>--порт</string>" in п and "KeepAlive" in п:
        print("  ✓ macOS: описание службы собирается, перезапуск включён")
    else:
        ошибки.append("plist собран неверно")
    ю = _unit("проба", ["/usr/bin/python3", "с.py", "--порт", "1"])
    if "Restart=always" in ю and "ExecStart=/usr/bin/python3 с.py --порт 1" in ю:
        print("  ✓ Linux: unit собирается, перезапуск включён")
    else:
        ошибки.append(f"unit собран неверно: {ю!r}")
    ю2 = _unit("проба", ["/usr/bin/python3", "путь с пробелом.py"])
    if "'путь с пробелом.py'" in ю2:
        print("  ✓ Linux: путь с пробелом экранируется, служба не рассыпается")
    else:
        ошибки.append("путь с пробелом не экранирован")
    if безопасное_имя("проба") == "proba" and безопасное_имя("PDF-инструменты") == "pdf-instrumenty":
        print("  ✓ имя службы приводится к латинице — systemd кириллицу не принимает")
    else:
        ошибки.append(f"имя не приведено: {безопасное_имя('проба')!r}, "
                      f"{безопасное_имя('PDF-инструменты')!r}")
    if безопасное_имя("!!!") == "extella":
        print("  ✓ пустое после чистки имя не превращается в пустую строку")
    else:
        ошибки.append("пустое имя не подстраховано")
    if питон().endswith("python3") or "python" in питон().lower():
        print(f"  ✓ питон для служб берётся живой: {питон()}")
    else:
        ошибки.append(f"питон определён странно: {питон()}")
    for о in ошибки:
        print(f"  ✗ {о}")
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("--имя")
    р.add_argument("--команда", help="строка команды целиком")
    р.add_argument("--снять", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return _самопроверка()
    if not а.имя:
        р.error("нужно --имя")
    if а.снять:
        снять(а.имя)
        print(f"служба «{а.имя}» снята ({система()})")
        return 0
    if not а.команда:
        р.error("нужна --команда")
    где = поставить(а.имя, shlex.split(а.команда))
    print(f"служба «{а.имя}» поставлена ({система()}): {где}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
