#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установщик Schemes Board на компьютер покупателя (устройственный продукт, раздел B).

ЗАЧЕМ ОН ВООБЩЕ. Замер 25.08.2026: коллега владельца установила «Доску схем» из
магазина, установка прошла успешно — и приложение не заработало. В версии лежала
ОДНА СТРАНИЦА ОКНА, которая смотрит на localhost её машины, а самой программы там
не было и быть не могло: она стояла только у автора, поставленная вручную. Человек
не ошибся — ему продали пустой пакет. Установщик закрывает ровно это.

ЧТО ВЕЗЁТ ДОСКА, В ОТЛИЧИЕ ОТ ЧИТАЛКИ. Тут два куска: сама доска (494 файла
статики, работает целиком в браузере) и НАШ ПРОКСИ — маленький сервер, который
её отдаёт и хранит рисунки файлом на диске. Без прокси доска открылась бы, но
рисунки жили бы в браузере и пропали при первой же чистке: в окне ОС браузерное
хранилище заперто песочницей.

ЧТО ДЕЛАЕТ (и ничего сверх того):
  1. кладёт доску и прокси в ~/extella-apps/schemes-board;
  2. заводит папку для рисунков — она НЕ перезаписывается при переустановке;
  3. подбирает свободный порт и записывает его в настройку;
  4. прописывает службу автозапуска — своим способом на macOS, Linux, Windows;
  5. ДОКАЗЫВАЕТ, что окно отвечает, и только тогда сообщает об успехе.

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
ГНЕЗДО = ДОМ / "extella-apps" / "schemes-board"
ДАННЫЕ = ГНЕЗДО / "drawings"        # работа человека: не трогаем никогда
СТАТИКА = ГНЕЗДО / "board"
НАСТРОЙКА = ГНЕЗДО / "настройка.json"
ПОРТ_ПО_УМОЛЧАНИЮ = 34786
ИМЯ_СЛУЖБЫ = "schemes-board"


# ВЫВОД УСТАНОВЩИКА — ПО-АНГЛИЙСКИ, И ЭТО НЕ ПРО ЯЗЫК ИНТЕРФЕЙСА.
# Замер на Windows ARM64 владельца 28.08.2026, дважды подряд: русский текст
# установщика рушил чтение вывода на стороне вызывающего (cp1252 не знает
# наших букв), и от установки оставалось голое «код 2» без причины. Одна
# незнакомая буква в сообщении об ошибке — и человек не узнаёт ошибку вовсе.
# ASCII читается любой кодировкой, а перевод на язык человека — дело окна.
#
# Ниже — ремень поверх подтяжек: даже английский вывод пишем явным UTF-8. Консоль Windows живёт в однобайтовой
# кодировке, и первый же print с кириллицей там рушит установку — либо саму
# печать, либо чтение вывода на той стороне. Замер на Windows ARM64 владельца
# 28.08.2026: установщик вернул код 2, а вывод пришёл ПУСТОЙ — текст ошибки
# погиб по дороге, и стало непонятно вообще ничего.
for _поток in (sys.stdout, sys.stderr):
    try:
        _поток.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass                      # старый Python или подменённый поток — не беда


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
    """На порту наша же Доска (осталась от прошлой установки или ручной)?

    Спрашиваем служебный адрес прокси. Он отвечает номером версии рисунков —
    такого ответа не даст ни одна чужая программа, а по корню «/» отличить
    нельзя: там просто страница. Ошибиться здесь дорого: приняв чужой сервер за
    свой, установщик снял бы чужую службу.
    """
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{порт}/_extella_version", timeout=2) as о:
            if о.status != 200:
                return False
            ответ = json.loads(о.read(400).decode("utf-8", "replace"))
            return "версия" in ответ
    except Exception:                                # noqa: BLE001
        return False


def занять_порт() -> int:
    """ПОРТ — ЭТО КОНТРАКТ С ОКНОМ, а не «первый свободный».

    ЗАМЕР 27.08.2026. Прежняя версия брала первый незанятый порт — и на моей
    машине встала на 34793. Установка отрапортовала «готово», проверка
    подтвердила «окно отвечает», всё честно. Только окно в магазине смотрит на
    ПРОШИТЫЙ адрес localhost:34786: страница окна одна на всех покупателей и
    подстроиться под чужой порт не может. Программа работала, окно было пустым,
    и виноватым выглядел покупатель.

    Поэтому: занимаем именно свой порт. Если там уже наша Доска — снимаем и
    занимаем заново. Если там ЧУЖАЯ программа — не прячемся на соседнем порту,
    а говорим человеку прямо, потому что молча уехавшее окно он не починит.
    """
    if свободен(ПОРТ_ПО_УМОЛЧАНИЮ):
        return ПОРТ_ПО_УМОЛЧАНИЮ
    if наше_ли(ПОРТ_ПО_УМОЛЧАНИЮ):
        # Прошлая установка — своя же. Снимаем всё, что могло её держать:
        # ручная установка звалась «board», магазинная — «schemes-board».
        for имя in (ИМЯ_СЛУЖБЫ, "board"):
            снять_службу(имя)
        for _ in range(10):
            if свободен(ПОРТ_ПО_УМОЛЧАНИЮ):
                return ПОРТ_ПО_УМОЛЧАНИЮ
            time.sleep(1)
    провал(f"port {ПОРТ_ПО_УМОЛЧАНИЮ} is taken by another program. The Board "
           f"window looks at exactly this address, so moving to a neighbouring "
           f"port would leave the window empty. Free port {ПОРТ_ПО_УМОЛЧАНИЮ} "
           f"and install the Board again")


def снять_службу(имя: str = "") -> None:
    """Остановить свою же службу ДО того, как занимать порт.

    ПОЧЕМУ ЭТО ВАЖНО ИМЕННО ПРИ ПЕРЕУСТАНОВКЕ. Работающая служба занимает свой
    порт — и поиск «свободного» уводит установку на соседний. Служба остаётся
    на старом, окно ищут на новом, и установщик честно валится: «окно не
    ответило». Замер 25.08.2026 на чистой машине: первая установка прошла,
    вторая упала на ровном месте. Сначала освобождаем своё, потом ищем.
    """
    имя = имя or ИМЯ_СЛУЖБЫ
    с = sys.platform
    if с == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/ai.extella.{имя}"],
                       capture_output=True)
    elif с.startswith("linux"):
        subprocess.run(["systemctl", "--user", "stop", f"extella-{имя}.service"],
                       capture_output=True)
    elif с.startswith("win"):
        subprocess.run(["schtasks", "/End", "/TN", f"Extella\\{имя}"],
                       capture_output=True)
    # Порт освобождается не мгновенно: даём системе закрыть сокет.
    time.sleep(1.5)


def положить_файлы() -> None:
    ГНЕЗДО.mkdir(parents=True, exist_ok=True)
    # РИСУНКИ ЗАВОДИМ, НО НЕ ТРОГАЕМ. Переустановка обязана оставить работу
    # человека нетронутой — это первое, что он проверит после обновления.
    ДАННЫЕ.mkdir(parents=True, exist_ok=True)

    if not (ЗДЕСЬ / "cabinet_server.py").exists():
        провал("cabinet_server.py is missing from the archive: the board would "
               "open, but drawings would have nowhere to live. This is a packaging "
               "error, not a problem with your computer")
    if not (ЗДЕСЬ / "board" / "index.html").exists():
        провал("the board itself is missing from the archive (board/index.html). "
               "This is a packaging error, not a problem with your computer")
    shutil.copy(ЗДЕСЬ / "cabinet_server.py", ГНЕЗДО / "cabinet_server.py")
    # Статику кладём заново целиком: старые файлы версии не должны остаться
    # вперемешку с новыми.
    if СТАТИКА.exists():
        shutil.rmtree(СТАТИКА)
    shutil.copytree(ЗДЕСЬ / "board", СТАТИКА)
    сколько = sum(1 for _ in СТАТИКА.rglob("*") if _.is_file())
    сказать(f"  board: {СТАТИКА} ({сколько} files)")
    сказать(f"  drawings: {ДАННЫЕ}")


def перенести_прежнюю_работу() -> None:
    """Забрать рисунки прежней, доустановочной Доски — один раз, при первой
    установке из магазина.

    ЗАМЕР 27.08.2026. До магазина Доска стояла руками, и её рисунки лежат в
    другом месте — в папке кабинета. Установщик заводит СВОЮ пустую папку и
    занимает тот же порт; окно после установки открылось бы чистым листом, и
    выглядело бы это как «обновление стёрло всю работу». Файл прежней Доски
    держал 531 версию рисунков.

    Копируем, а не переносим: прежний файл остаётся на месте нетронутым. И
    только если своего файла ещё нет — иначе обновление затирало бы свежую
    работу старой.
    """
    свой = ДАННЫЕ / "board.json"
    if свой.exists():
        return
    прежний = ДОМ / "extella-cabinet" / "данные" / "доска.json"
    if not прежний.is_file():
        return
    try:
        shutil.copy(прежний, свой)
        сказать(f"  earlier drawings carried over: {прежний.name} -> {свой.name}")
    except OSError as е:
        # Не повод валить установку: доска откроется, работа не потеряна —
        # она лежит в прежнем файле. Но человек должен знать.
        сказать(f"  WARNING: earlier drawings were not carried over ({е}). "
                f"They are intact in {прежний}")


def прописать_службу(порт: int) -> str:
    """Автозапуск своим способом на каждой системе. Возвращает, как именно."""
    питон = sys.executable or "python3"
    # ЛАТИНИЦЕЙ, А НЕ ПО-РУССКИ. Прокси понимает оба написания, но эта команда
    # уезжает в службу операционной системы, и на Windows русские имена по
    # дороге искажаются (замер 27.08.2026). Пути тоже держим латинскими.
    команда = [питон, str(ГНЕЗДО / "cabinet_server.py"),
               "--folder", str(СТАТИКА), "--port", str(порт),
               "--name", "board", "--data", str(ДАННЫЕ)]
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
            сказать("  WARNING: this user has no systemd session "
                    "(usual on servers and inside containers).")
            сказать(f"  Start it by hand: {' '.join(команда)}")
            сказать("  Or run once: loginctl enable-linger $USER")
            return "no autostart — command printed"
        папка = ДОМ / ".config" / "systemd" / "user"
        папка.mkdir(parents=True, exist_ok=True)
        файл = папка / f"extella-{ИМЯ_СЛУЖБЫ}.service"
        строка = " ".join(f"'{ч}'" if " " in ч else ч for ч in команда)
        файл.write_text(f"[Unit]\nDescription=Extella · Schemes Board\n\n"
                        f"[Service]\nExecStart={строка}\nRestart=always\nRestartSec=2\n\n"
                        f"[Install]\nWantedBy=default.target\n")
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        и = subprocess.run(["systemctl", "--user", "enable", "--now",
                            f"extella-{ИМЯ_СЛУЖБЫ}.service"], capture_output=True, text=True)
        if и.returncode != 0:
            провал(f"the service did not start: {(и.stderr or '')[:200]}")
        return f"systemd · {файл}"

    if система.startswith("win"):
        # КОМАНДУ КЛАДЁМ В ФАЙЛ, А НЕ В СТРОКУ ПЛАНИРОВЩИКА. У прокси имена
        # аргументов кириллические («--папка», «--данные»), да и пути内 бывают
        # нелатинскими. Планировщик Windows принимает такую строку в своей
        # кодировке консоли, и до питона она доезжает искажённой — служба
        # создаётся, а запуститься не может. Обёртка .cmd переключает кодовую
        # страницу на UTF-8 и запускает уже нормальную команду.
        обёртка = ГНЕЗДО / "запуск.cmd"
        строки = ["@echo off", "chcp 65001 >nul",
                  " ".join(f'"{ч}"' if (" " in ч or not ч.isascii()) else ч
                           for ч in команда)]
        обёртка.write_text("\r\n".join(строки) + "\r\n", encoding="utf-8")
        задача = f"Extella\\{ИМЯ_СЛУЖБЫ}"
        subprocess.run(["schtasks", "/Delete", "/TN", задача, "/F"], capture_output=True)
        и = subprocess.run(["schtasks", "/Create", "/TN", задача, "/SC", "ONLOGON",
                            "/RL", "LIMITED", "/F", "/TR", f'"{обёртка}"'],
                           capture_output=True, text=True)
        if и.returncode != 0:
            провал(f"the autostart task was not created: {(и.stdout or и.stderr or '')[:200]}")
        subprocess.run(["schtasks", "/Run", "/TN", задача], capture_output=True)
        return f"Планировщик заданий · {задача} (через {обёртка.name})"

    сказать(f"  WARNING: system '{система}' has no autostart support here.")
    сказать(f"  Start it by hand: {' '.join(команда)}")
    return "no autostart — command printed"


def доказать(порт: int) -> None:
    """C3: доказываем работой, а не верим. «Служба создана» ≠ «окно отвечает»."""
    # У прокси нет служебного адреса здоровья: спрашиваем саму доску.
    адрес = f"http://127.0.0.1:{порт}/"
    for попытка in range(20):
        try:
            with urllib.request.urlopen(адрес, timeout=3) as о:
                if о.status == 200:
                    сказать(f"  check: the window answers on port {порт}")
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    провал(f"the service is registered, but the window did not answer on port "
           f"{порт} within 20 seconds. Look into {ГНЕЗДО / 'служба.log'}")


def main() -> int:
    сказать("Installing Schemes Board")
    агент = os.environ.get("EXTELLA_AGENT_ID", "").strip()
    версия = os.environ.get("EXTELLA_APP_VERSION", "").strip() or "?"

    # Идемпотентность (C2) начинается с освобождения своего же места.
    снять_службу()
    положить_файлы()
    перенести_прежнюю_работу()
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
    сказать("Done. Open Schemes Board — drawings are kept as a file on this computer.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as е:                       # noqa: BLE001
        провал(f"unexpected error: {type(е).__name__}: {е}")
