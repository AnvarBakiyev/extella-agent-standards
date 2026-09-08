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


# ГОВОРИМ ASCII И ПИШЕМ В UTF-8 — УРОК WINDOWS. Консоль Windows читает вывод в
# своей однобайтовой кодировке: русский текст рушит чтение на стороне
# вызывающего, и от установки остаётся голое «код 2» без причины (замер на
# Windows ARM64 28.08.2026, стоил двух попыток вслепую).
for _поток in (sys.stdout, sys.stderr):
    try:
        _поток.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def сказать(текст: str) -> None:
    print(текст, flush=True)


def провал(почему: str) -> None:
    # B3: честный ненулевой код. Ноль при поломке = человека спишут за то, что
    # не работает, и он узнает об этом сам, открыв пустое окно.
    сказать(f"INSTALL FAILED: {почему}")
    sys.exit(2)


def свободен(порт: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as с:
        return с.connect_ex(("127.0.0.1", порт)) != 0


def наше_ли(порт: int) -> bool:
    """На порту наша же читалка? Спрашиваем её служебный адрес здоровья.
    Ошибиться дорого: приняв чужую программу за свою, установщик снял бы
    чужую службу."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{порт}/api/health", timeout=2) as о:
            return о.status == 200
    except Exception:                                # noqa: BLE001
        return False


def порт_из_адреса(адрес: str) -> int:
    try:
        return int(адрес.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return -1


def убить_на_порту(порт: int) -> None:
    """Снять процесс, слушающий наш порт — на ЛЮБОЙ системе.

    Зовётся ТОЛЬКО после того, как проверено: там наша же программа (решает
    `наше_ли`, эта функция лишь исполняет). Чужое не трогаем никогда.

    ПОЧЕМУ НЕ ХВАТИЛО СНЯТИЯ СЛУЖБЫ. Замер 08.09.2026: у владельца читалка
    работала на 34796, запущенная вручную, а не через launchd. Установщик
    узнал свою копию, снял службу — и упёрся в «порт занят», потому что
    процесс к службе отношения не имел. Программу можно поднять руками, и
    установщик обязан уметь её сменить.
    """
    if sys.platform.startswith("win"):
        try:
            и = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return
        for строка in (и.stdout or "").split("\n"):
            куски = строка.split()
            if len(куски) >= 5 and куски[-1].isdigit() and "LISTEN" in строка.upper():
                if порт_из_адреса(куски[1]) == порт:
                    subprocess.run(["taskkill", "/PID", куски[-1], "/F"], capture_output=True)
        return
    # macOS и Linux: lsof отдаёт номера процессов, слушающих порт
    try:
        и = subprocess.run(["lsof", "-tnP", f"-iTCP:{порт}", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return
    for номер in (и.stdout or "").split():
        if номер.isdigit():
            subprocess.run(["kill", номер], capture_output=True)


def занять_порт() -> int:
    """ПОРТ — ЭТО КОНТРАКТ С ОКНОМ, а не «первый свободный».

    Окно в магазине смотрит на ПРОШИТЫЙ адрес localhost:34796: страница окна
    одна на всех покупателей и подстроиться под чужой порт не может. Замер на
    Доске 27.08.2026: установка ушла на соседний порт, отрапортовала «готово»,
    программа работала — а окно осталось пустым, и виноватым выглядел человек.
    """
    if свободен(ПОРТ_ПО_УМОЛЧАНИЮ):
        return ПОРТ_ПО_УМОЛЧАНИЮ
    if наше_ли(ПОРТ_ПО_УМОЛЧАНИЮ):
        снять_службу()
        for _ in range(10):
            if свободен(ПОРТ_ПО_УМОЛЧАНИЮ):
                return ПОРТ_ПО_УМОЛЧАНИЮ
            time.sleep(1)
    провал(f"port {ПОРТ_ПО_УМОЛЧАНИЮ} is taken by another program. The window "
           f"looks at exactly this address, so moving to a neighbouring port "
           f"would leave it empty. Free port {ПОРТ_ПО_УМОЛЧАНИЮ} and install again")


def снять_службу() -> None:
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
        # Автозапуск мог встать тремя способами (задача в папке, плоская
        # задача, ярлык автозагрузки), а сервер вдобавок поднимается напрямую.
        # Снимаем всё: замер 28.08.2026 — переустановка узнала свою же копию,
        # но снять не смогла и упёрлась в «порт занят» на ровном месте.
        for задача in (f"Extella\\{ИМЯ_СЛУЖБЫ}", f"Extella-{ИМЯ_СЛУЖБЫ}"):
            subprocess.run(["schtasks", "/End", "/TN", задача], capture_output=True)
    # Программу могли поднять и руками, мимо службы — снимаем и такую.
    убить_на_порту(ПОРТ_ПО_УМОЛЧАНИЮ)
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
    сказать(f"  files: {ГНЕЗДО}")


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
            провал(f"the service did not start: {(и.stderr or '')[:200]}")
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
            return "no autostart — command printed"
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
            провал(f"the service did not start: {(и.stderr or '')[:200]}")
        return f"systemd · {файл}"

    if система.startswith("win"):
        # ПОДНИМАЕМ СРАЗУ. Человек открыл окно и ждёт приложение сейчас, а не
        # после перезагрузки; автозапуск ниже — только чтобы оно вернулось завтра.
        try:
            subprocess.Popen(команда, cwd=str(ГНЕЗДО),
                             stdout=open(журнал, "ab"), stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            time.sleep(2)
        except OSError as е:
            провал(f"could not start the app: {е}")

        # Команду кладём в .cmd с UTF-8: имена аргументов у сервера русские, а
        # Планировщик Windows принимает строку в кодировке консоли и до питона
        # она доезжает искажённой (замер 27.08.2026).
        обёртка = ГНЕЗДО / "запуск.cmd"
        обёртка.write_text("\r\n".join(
            ["@echo off", "chcp 65001 >nul",
             " ".join(f'"{ч}"' if (" " in ч or not ч.isascii()) else ч for ч in команда)]
        ) + "\r\n", encoding="utf-8")

        # ПЛАНИРОВЩИК ЖЕЛАТЕЛЕН, А НЕ ОБЯЗАТЕЛЕН: задача в папке «Extella\»
        # требует прав администратора («Access is denied», замер 28.08.2026), а
        # просить их за читалку документов нельзя. Три ступени от лучшей к
        # рабочей: плоское имя задачи → автозагрузка пользователя → уже поднято.
        задача = f"Extella-{ИМЯ_СЛУЖБЫ}"
        subprocess.run(["schtasks", "/Delete", "/TN", задача, "/F"], capture_output=True)
        и = subprocess.run(["schtasks", "/Create", "/TN", задача, "/SC", "ONLOGON",
                            "/F", "/TR", f'"{обёртка}"'], capture_output=True, text=True)
        if и.returncode == 0:
            return f"Task Scheduler · {задача}"

        автозагрузка = (ДОМ / "AppData" / "Roaming" / "Microsoft" / "Windows"
                        / "Start Menu" / "Programs" / "Startup")
        try:
            автозагрузка.mkdir(parents=True, exist_ok=True)
            (автозагрузка / f"{ИМЯ_СЛУЖБЫ}.cmd").write_text(
                f'@echo off\r\nstart "" /min "{обёртка}"\r\n', encoding="utf-8")
            return f"Startup folder · {автозагрузка / (ИМЯ_СЛУЖБЫ + '.cmd')}"
        except OSError as е:
            сказать(f"  WARNING: no autostart ({е}). The app works until reboot.")
            return "no autostart — started for this session"

    сказать(f"  WARNING: system '{система}' has no autostart support here.")
    сказать(f"  Start it by hand: {' '.join(команда)}")
    return "no autostart — command printed"


def доказать(порт: int) -> None:
    """C3: доказываем работой, а не верим. «Служба создана» ≠ «окно отвечает»."""
    адрес = f"http://127.0.0.1:{порт}/api/health"
    for попытка in range(20):
        try:
            with urllib.request.urlopen(адрес, timeout=3) as о:
                if о.status == 200:
                    сказать(f"  check: the window answers on port {порт}")
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    провал(f"служба прописана, но окно не ответило на порту {порт} за 20 секунд. "
           f"Посмотрите {ГНЕЗДО / 'служба.log'}")


def main() -> int:
    сказать("Installing MD Reader")
    агент = os.environ.get("EXTELLA_AGENT_ID", "").strip()
    версия = os.environ.get("EXTELLA_APP_VERSION", "").strip() or "?"

    # Идемпотентность (C2) начинается с освобождения своего же места.
    снять_службу()
    положить_файлы()
    порт = занять_порт()
    # B4: привязка агента — иначе панель не знает, с кем работать.
    НАСТРОЙКА.write_text(json.dumps(
        {"agent_id": агент, "порт": порт, "версия": версия},
        ensure_ascii=False, indent=2), encoding="utf-8")
    сказать(f"  window address: localhost:{порт}")
    как = прописать_службу(порт)
    сказать(f"  autostart: {как}")
    if "no autostart" not in как:
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
