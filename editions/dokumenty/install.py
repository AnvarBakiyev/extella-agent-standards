#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установщик MD Reader на компьютер покупателя (устройственный продукт, раздел B).

ЗАЧЕМ ОН ВООБЩЕ. Замер 25.08.2026: коллега владельца установила «Доску схем» из
магазина, установка прошла успешно — и приложение не заработало. В версии лежала
ОДНА СТРАНИЦА ОКНА, которая смотрит на localhost её машины, а самой программы там
не было и быть не могло: она стояла только у автора, поставленная вручную. Человек
не ошибся — ему продали пустой пакет. Установщик закрывает ровно это.

ЧТО ДЕЛАЕТ (и ничего сверх того):
  1. кладёт файлы приложения в ~/extella-apps/md-reader;
  2. подбирает свободный порт и записывает его в настройку;
  3. прописывает службу автозапуска — своим способом на macOS, Linux, Windows;
  4. ДОКАЗЫВАЕТ, что окно отвечает, и только тогда сообщает об успехе.

ПРАВИЛА, КОТОРЫЕ ОН СОБЛЮДАЕТ (DEPLOY_REQUIREMENTS, раздел B):
  B2 — неинтерактивен: ни одного вопроса, всё нужное приходит средой;
  B3 — код возврата честный: ненулевой при настоящей поломке, иначе покупателя
       спишут за нерабочую установку;
  B4 — пишет привязку агента в файл продукта;
  B6 — поднимает панель сам; где автозапуск не поддержан, честно печатает команду;
  B7 — в архиве нет секретов: сюда едет только код приложения.

ИДЕМПОТЕНТЕН (C2): повторная установка не плодит вторых служб и не рушит готовое —
служба снимается и ставится заново, файлы перезаписываются, данные не трогаются.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
ДОМ = pathlib.Path.home()
ГНЕЗДО = ДОМ / "extella-apps" / "md-reader"
НАСТРОЙКА = ГНЕЗДО / "настройка.json"
ПОРТ_ПО_УМОЛЧАНИЮ = 34796
ИМЯ_СЛУЖБЫ = "md-reader"


def сказать(текст: str) -> None:
    print(текст, flush=True)


def провал(почему: str) -> None:
    # B3: честный ненулевой код. Ноль при поломке = человека спишут за то, что
    # не работает, и он узнает об этом сам, открыв пустое окно.
    сказать(f"УСТАНОВКА НЕ УДАЛАСЬ: {почему}")
    sys.exit(2)


def свободный_порт(начиная_с: int) -> int:
    """Первый порт, который никто не слушает. Занятый порт — обычное дело:
    у человека уже могут стоять наши приложения или чужие службы."""
    import socket
    for порт in range(начиная_с, начиная_с + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as с:
            if с.connect_ex(("127.0.0.1", порт)) != 0:
                return порт
    провал(f"не нашёл свободного порта в диапазоне {начиная_с}–{начиная_с + 40}")


def снять_прежнюю_службу() -> None:
    """Остановить свою же службу ДО того, как искать порт.

    ПОЧЕМУ ЭТО ВАЖНО ИМЕННО ПРИ ПЕРЕУСТАНОВКЕ. Работающая служба занимает свой
    порт — и поиск «свободного» уводит установку на соседний. Служба остаётся
    на старом, окно ищут на новом, и установщик честно валится: «окно не
    ответило». Замер 25.08.2026 на чистой машине: первая установка прошла,
    вторая упала на ровном месте. Сначала освобождаем своё, потом ищем.
    """
    с = sys.platform
    if с == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/ai.extella.{ИМЯ_СЛУЖБЫ}"],
                       capture_output=True)
    elif с.startswith("linux"):
        subprocess.run(["systemctl", "--user", "stop", f"extella-{ИМЯ_СЛУЖБЫ}.service"],
                       capture_output=True)
    elif с.startswith("win"):
        subprocess.run(["schtasks", "/End", "/TN", f"Extella\\{ИМЯ_СЛУЖБЫ}"],
                       capture_output=True)
    # Порт освобождается не мгновенно: даём системе закрыть сокет.
    time.sleep(1.5)


def прежний_порт() -> int:
    """Порт из прошлой установки. Держимся за него: у человека уже могла
    остаться открытая вкладка и ярлык именно на этот адрес."""
    try:
        return int(json.loads(НАСТРОЙКА.read_text(encoding="utf-8")).get("порт") or 0)
    except Exception:
        return 0


def положить_файлы() -> None:
    ГНЕЗДО.mkdir(parents=True, exist_ok=True)
    нужные = ["server.py", "index.html", "icon.png"]
    не_хватает = [и for и in нужные if not (ЗДЕСЬ / и).exists()]
    if не_хватает:
        провал(f"в архиве нет файлов приложения: {', '.join(не_хватает)}. "
               f"Это ошибка сборки пакета, а не вашей машины")
    for и in нужные:
        shutil.copy(ЗДЕСЬ / и, ГНЕЗДО / и)
    сказать(f"  файлы приложения: {ГНЕЗДО}")


def прописать_службу(порт: int) -> str:
    """Автозапуск своим способом на каждой системе. Возвращает, как именно."""
    питон = sys.executable or "python3"
    команда = [питон, str(ГНЕЗДО / "server.py"), "--порт", str(порт)]
    система = sys.platform
    журнал = ГНЕЗДО / "служба.log"

    if система == "darwin":
        папка = ДОМ / "Library" / "LaunchAgents"
        папка.mkdir(parents=True, exist_ok=True)
        файл = папка / f"ai.extella.{ИМЯ_СЛУЖБЫ}.plist"
        арг = "".join(f"<string>{ч}</string>" for ч in команда)
        файл.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
            '"-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f'<plist version="1.0"><dict><key>Label</key>'
            f'<string>ai.extella.{ИМЯ_СЛУЖБЫ}</string>'
            f'<key>ProgramArguments</key><array>{арг}</array>'
            '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>'
            f'<key>StandardErrorPath</key><string>{журнал}</string></dict></plist>')
        метка = f"gui/{os.getuid()}"
        # bootout/bootstrap, а не kickstart: kickstart не перечитывает файл, и
        # при переустановке служба осталась бы со старыми настройками.
        subprocess.run(["launchctl", "bootout", f"{метка}/ai.extella.{ИМЯ_СЛУЖБЫ}"],
                       capture_output=True)
        и = subprocess.run(["launchctl", "bootstrap", метка, str(файл)],
                           capture_output=True, text=True)
        if и.returncode != 0:
            провал(f"служба не встала: {(и.stderr or '')[:200]}")
        return f"launchd · {файл}"

    if система.startswith("linux"):
        проба = subprocess.run(["systemctl", "--user", "is-system-running"],
                               capture_output=True, text=True)
        вывод = (проба.stdout or "") + (проба.stderr or "")
        if "Failed to connect to bus" in вывод or "No medium found" in вывод:
            # B6: где автозапуск не поддержан — честно печатаем команду.
            сказать("  ВНИМАНИЕ: своей службы systemd у пользователя нет "
                    "(так бывает на серверах и в контейнерах).")
            сказать(f"  Запускайте вручную: {' '.join(команда)}")
            сказать("  Либо один раз выполните: loginctl enable-linger $USER")
            return "без автозапуска — команда напечатана"
        папка = ДОМ / ".config" / "systemd" / "user"
        папка.mkdir(parents=True, exist_ok=True)
        файл = папка / f"extella-{ИМЯ_СЛУЖБЫ}.service"
        строка = " ".join(f"'{ч}'" if " " in ч else ч for ч in команда)
        файл.write_text(f"[Unit]\nDescription=Extella · MD Reader\n\n"
                        f"[Service]\nExecStart={строка}\nRestart=always\nRestartSec=2\n\n"
                        f"[Install]\nWantedBy=default.target\n")
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        и = subprocess.run(["systemctl", "--user", "enable", "--now",
                            f"extella-{ИМЯ_СЛУЖБЫ}.service"], capture_output=True, text=True)
        if и.returncode != 0:
            провал(f"служба не встала: {(и.stderr or '')[:200]}")
        return f"systemd · {файл}"

    if система.startswith("win"):
        задача = f"Extella\\{ИМЯ_СЛУЖБЫ}"
        строка = " ".join(f'"{ч}"' if " " in ч else ч for ч in команда)
        subprocess.run(["schtasks", "/Delete", "/TN", задача, "/F"], capture_output=True)
        и = subprocess.run(["schtasks", "/Create", "/TN", задача, "/SC", "ONLOGON",
                            "/RL", "LIMITED", "/F", "/TR", строка],
                           capture_output=True, text=True)
        if и.returncode != 0:
            провал(f"задача автозапуска не создалась: {(и.stdout or и.stderr or '')[:200]}")
        subprocess.run(["schtasks", "/Run", "/TN", задача], capture_output=True)
        return f"Планировщик заданий · {задача}"

    сказать(f"  ВНИМАНИЕ: система «{система}» без автозапуска.")
    сказать(f"  Запускайте вручную: {' '.join(команда)}")
    return "без автозапуска — команда напечатана"


def доказать(порт: int) -> None:
    """C3: доказываем работой, а не верим. «Служба создана» ≠ «окно отвечает»."""
    адрес = f"http://127.0.0.1:{порт}/api/health"
    for попытка in range(20):
        try:
            with urllib.request.urlopen(адрес, timeout=3) as о:
                if о.status == 200:
                    сказать(f"  проверка: окно отвечает на порту {порт}")
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    провал(f"служба прописана, но окно не ответило на порту {порт} за 20 секунд. "
           f"Посмотрите {ГНЕЗДО / 'служба.log'}")


def main() -> int:
    сказать("Установка MD Reader")
    агент = os.environ.get("EXTELLA_AGENT_ID", "").strip()
    версия = os.environ.get("EXTELLA_APP_VERSION", "").strip() or "?"

    # Идемпотентность (C2) начинается с освобождения своего же места.
    был = прежний_порт()
    снять_прежнюю_службу()
    положить_файлы()
    порт = свободный_порт(был or ПОРТ_ПО_УМОЛЧАНИЮ)
    # B4: привязка агента — иначе панель не знает, с кем работать.
    НАСТРОЙКА.write_text(json.dumps(
        {"agent_id": агент, "порт": порт, "версия": версия},
        ensure_ascii=False, indent=2), encoding="utf-8")
    сказать(f"  порт: {порт}" + ("" if порт == ПОРТ_ПО_УМОЛЧАНИЮ else " (обычный был занят)"))
    как = прописать_службу(порт)
    сказать(f"  автозапуск: {как}")
    if "без автозапуска" not in как:
        доказать(порт)
    сказать(f"Готово. Откройте MD Reader — он читает документы на этом компьютере.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as е:                       # noqa: BLE001
        провал(f"неожиданная ошибка: {type(е).__name__}: {е}")
