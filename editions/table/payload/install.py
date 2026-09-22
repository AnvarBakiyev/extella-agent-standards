#!/usr/bin/env python3
"""Установщик «Таблицы» для Extella Desktop.

Пакет самодостаточен: внутри лежит сервер кабинета и само приложение
(LuckySheet). После распаковки ничего доустанавливать не нужно — ни Docker,
ни пакетов: сервер написан на стандартной библиотеке Python.

Работает на macOS, Linux и Windows. Замер 19.09.2026: прежние карточки
офисного набора («Таблица», «Диаграммы», «Заметки», «Задачи и календарь»)
не имели НИ архива, НИ установщика — это были только страницы, которые
стучались в localhost, куда службу никто никогда не клал. На Маке автора они
работали, потому что он поднимал их руками; на машине покупателя — никогда.
Этот файл закрывает ровно это.

Два правила, оплаченные чужими поломками:

* **автозапуск не решает успех установки.** Если машина не даёт
  зарегистрировать службу (нет пользовательской сессии, контейнер,
  служебная учётка) — файлы всё равно разложены, сервер поднят, ручная
  команда напечатана. Молчаливый провал хуже честной строки.
* **свой процесс снимается по pid-файлу, чужой порт обходится.** Проверять
  «а вдруг на порту уже наше приложение» недостаточно: если прежний процесс
  жив, новый сервер на этот порт не встанет, а установка отрапортует успех.
  Поэтому: снять своё по записанному pid, занять первый свободный порт,
  а отпечаток `luckysheet` использовать для проверки, что поднялись именно мы.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


APP_ID = "table"
APP_NAME = "Таблица"
VERSION = os.environ.get("EXTELLA_APP_VERSION") or "1.0.0"
DEFAULT_PORT = 34787
LABEL = "ai.extella.table"
HERE = Path(__file__).resolve().parent
# Строка, по которой узнаём именно наше приложение на порту.
ОТПЕЧАТОК = "luckysheet"

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")


# На Windows консоль по умолчанию не UTF-8: печать русского текста роняет
# установщик с 'charmap' codec can't encode. Поймано на чистом стенде 19.09.2026 —
# на Маке этого не видно никогда. Приводим вывод к UTF-8 до первой печати.
for _поток in (sys.stdout, sys.stderr):
    try:
        _поток.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — старый Python или подменённый поток
        pass


def log(event: str, **extra: object) -> None:
    строка = json.dumps({"app": APP_ID, "event": event, **extra}, ensure_ascii=False)
    try:
        print(строка, flush=True)
    except UnicodeEncodeError:
        # Последний рубеж: лучше выдать ASCII-экранирование, чем упасть.
        print(json.dumps({"app": APP_ID, "event": event, **extra}), flush=True)


def наше_приложение(port: int) -> bool:
    """True, только если на порту отвечает именно «Таблица»."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2.0) as ответ:
            if ответ.status != 200:
                return False
            тело = ответ.read(200000).decode("utf-8", errors="replace").lower()
        return ОТПЕЧАТОК in тело
    except Exception:
        return False


def порт_занят(port: int) -> bool:
    """Осторожно: «не смог проверить» считаем ЗАНЯТО.

    Замер самопроверкой 19.09.2026: у службы с переполненной очередью
    соединений connect не проходит, и наивная проверка объявляла порт
    свободным — установщик занял бы порт под чужой службой. Неизвестность
    здесь должна толковаться не в нашу пользу."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return True


def выбрать_порт(start: int) -> int:
    """Берём первый СВОБОДНЫЙ порт.

    Соблазн «порт занят нашим приложением — значит можно переиспользовать»
    ложный: если прежний процесс не остановлен, новый сервер просто не сможет
    встать на этот порт, а установка отрапортует успех. Прежний свой процесс
    снимается по pid-файлу до этого вызова; всё, что осталось занятым, —
    чужое, и его надо обойти."""
    for port in range(start, start + 100):
        if not порт_занят(port):
            return port
    raise RuntimeError("Нет свободного порта для «Таблицы»")


def разложить(destination: Path) -> None:
    staged = destination.with_name(destination.name + ".next")
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir(parents=True)
    for name in ("cabinet_server.py", "apps"):
        source = HERE / name
        if not source.exists():
            raise RuntimeError(f"Архив неполон: нет {name}")
        target = staged / name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    (staged / "release.json").write_text(
        json.dumps({"app": APP_ID, "version": VERSION}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    backup = destination.with_name(destination.name + ".previous")
    shutil.rmtree(backup, ignore_errors=True)
    if destination.exists():
        destination.rename(backup)
    staged.rename(destination)
    # Работу пользователя не трогаем: данные лежат отдельно от кода.
    shutil.rmtree(backup, ignore_errors=True)


def команда(root: Path, port: int) -> list[str]:
    текущий = root / "current"
    данные = root / "data"
    данные.mkdir(parents=True, exist_ok=True)
    return [sys.executable, str(текущий / "cabinet_server.py"),
            "--папка", str(текущий / "apps" / "tablica"),
            "--порт", str(port),
            "--имя", APP_ID,
            "--данные", str(данные)]


def реестр(root: Path, port: int) -> dict:
    приложение = root / "current" / "apps" / "tablica"
    return {
        "id": APP_ID,
        "name": APP_NAME,
        "tagline": "Таблица с формулами — работа хранится файлом на вашем компьютере",
        "description": "Электронная таблица на LuckySheet. Всё считается и хранится локально, "
                       "ничего не уходит наружу.",
        "category": "productivity",
        "type": "custom",
        "version": VERSION,
        "mode": "repo_ui",
        "standalone": True,
        "ui": {"type": "local_server", "port": port, "rootPath": str(приложение),
               "mainFile": "index.html", "healthPath": "/", "openInBrowser": False,
               "expectsHealth": True},
        "service": {"isApp": True, "port": port, "healthPath": "/",
                    "launchCmd": subprocess.list2cmdline(команда(root, port)), "ready": True},
        "artifacts": {"rootPath": str(root / "current"),
                      "registryFile": f"~/extella-plugins/_registry/{APP_ID}.json"},
        "installed": True,
    }


def снять_по_pid(root: Path) -> None:
    """Снимаем ровно свой прежний процесс, записанный при прошлой установке."""
    файл = root / "server.pid"
    try:
        pid = int(файл.read_text(encoding="utf-8").strip())
    except Exception:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=False)
        else:
            os.kill(pid, 15)
        time.sleep(1.0)
    except Exception:
        pass
    finally:
        файл.unlink(missing_ok=True)


def остановить_прежнее() -> None:
    if IS_MAC:
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
                       capture_output=True, check=False)
    elif IS_LINUX and shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "stop", f"{LABEL}.service"],
                       capture_output=True, check=False)
    elif IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/FI", f"WINDOWTITLE eq {LABEL}"],
                       capture_output=True, check=False)


def запустить_отдельно(root: Path, port: int) -> None:
    """Запуск, переживающий установщика. На Windows — своей группой процессов,
    иначе сервер уходит вместе с деревом процессов установки (этот дефект
    уже ловили на Human Atlas и MD Reader)."""
    журналы = root / "logs"
    журналы.mkdir(parents=True, exist_ok=True)
    поток = open(журналы / "server.log", "ab", buffering=0)
    kwargs: dict = {"stdout": поток, "stderr": поток, "stdin": subprocess.DEVNULL}
    if IS_WINDOWS:
        # DETACHED_PROCESS | NEW_PROCESS_GROUP мало: если установщик запущен
        # внутри «задания» (job object) — а так работают и OpenSSH-сеанс, и
        # некоторые службы — потомок умирает вместе с родителем, сколько его
        # ни отвязывай. Замер 19.09.2026 на стенде: сервер отвечал в момент
        # установки и исчезал через минуту. CREATE_BREAKAWAY_FROM_JOB выводит
        # процесс из задания; если задание этого не разрешает, Windows вернёт
        # ошибку — тогда стартуем как раньше, но честно пишем об этом.
        БАЗА = 0x00000008 | 0x00000200
        ОТРЫВ = 0x01000000
        try:
            процесс = subprocess.Popen(команда(root, port), creationflags=БАЗА | ОТРЫВ, **kwargs)
        except OSError:
            процесс = subprocess.Popen(команда(root, port), creationflags=БАЗА, **kwargs)
    else:
        kwargs["start_new_session"] = True
        процесс = subprocess.Popen(команда(root, port), **kwargs)  # noqa: S603
    (root / "server.pid").write_text(str(процесс.pid), encoding="utf-8")


def автозапуск_мак(root: Path, port: int) -> str:
    каталог = Path.home() / "Library" / "LaunchAgents"
    каталог.mkdir(parents=True, exist_ok=True)
    plist = каталог / f"{LABEL}.plist"
    экран = lambda v: str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    аргументы = "".join(f"<string>{экран(v)}</string>" for v in команда(root, port))
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>'
        f"<key>Label</key><string>{LABEL}</string>"
        f"<key>ProgramArguments</key><array>{аргументы}</array>"
        "<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
        "</dict></plist>\n", encoding="utf-8")
    uid = str(os.getuid())
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True, check=False)
    готово = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)],
                            capture_output=True, text=True, check=False)
    return "launchd" if готово.returncode == 0 else f"нет: launchd отказал ({готово.stderr.strip()[:80]})"


def автозапуск_линукс(root: Path, port: int) -> str:
    каталог = Path.home() / ".config" / "systemd" / "user"
    каталог.mkdir(parents=True, exist_ok=True)
    (каталог / f"{LABEL}.service").write_text(
        f"[Unit]\nDescription={APP_NAME}\n\n[Service]\n"
        f"ExecStart={subprocess.list2cmdline(команда(root, port))}\n"
        "Restart=on-failure\n\n[Install]\nWantedBy=default.target\n", encoding="utf-8")
    if not shutil.which("systemctl"):
        return "нет: systemctl отсутствует"
    for argv in (["systemctl", "--user", "daemon-reload"],
                 ["systemctl", "--user", "enable", "--now", f"{LABEL}.service"]):
        if subprocess.run(argv, capture_output=True, check=False).returncode:
            return "нет: пользовательской сессии systemd нет (обычное дело на серверах)"
    return "systemd --user"


def автозапуск_windows(root: Path, port: int) -> str:
    каталог = Path(os.environ.get("APPDATA", str(Path.home()))) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    каталог.mkdir(parents=True, exist_ok=True)
    запускатель = Path(sys.executable)
    тихий = запускатель.with_name("pythonw.exe")
    if тихий.exists():
        запускатель = тихий
    строка = [str(запускатель)] + команда(root, port)[1:]
    (каталог / f"{LABEL}.cmd").write_text(
        "@echo off\r\nstart \"\" " + subprocess.list2cmdline(строка) + "\r\n", encoding="utf-8")
    return "папка автозагрузки Windows"


def дождаться(port: int, секунд: float = 8.0) -> bool:
    предел = time.time() + секунд
    while time.time() < предел:
        if наше_приложение(port):
            return True
        time.sleep(0.3)
    return False


def _selftest() -> int:
    """Самопроверка с зубами: проверяет ПОВЕДЕНИЕ, а не наличие файлов.

    Если убрать любой из проверяемых методов, она обязана покраснеть — именно
    это и требует гейт check_self_check негативным контролем.
    """
    import http.server, tempfile, threading, urllib.error
    провалы = []

    def проба(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка установщика «Таблицы»:")

    # 1. Занятый порт обходится, свободный берётся.
    гнездо = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    гнездо.bind(("127.0.0.1", 0)); гнездо.listen(5)
    занятый = гнездо.getsockname()[1]
    try:
        проба("занятый порт распознаётся занятым", порт_занят(занятый))
        проба("выбор порта обходит занятый", выбрать_порт(занятый) != занятый)
    finally:
        гнездо.close()

    # 2. Отпечаток отличает наше приложение от чужого на том же порту.
    class Чужой(http.server.BaseHTTPRequestHandler):
        тело = b"<html>some other app</html>"
        def do_GET(с):  # noqa: N805
            с.send_response(200); с.send_header("Content-Length", str(len(с.тело)))
            с.end_headers(); с.wfile.write(с.тело)
        def log_message(с, *а):  # noqa: N805, D102
            pass

    class Наш(Чужой):
        тело = b"<html>luckysheet inside</html>"

    for класс, ожидаем, подпись in ((Чужой, False, "чужая служба на порту НЕ принимается за свою"),
                                     (Наш, True, "своё приложение на порту узнаётся")):
        сервер = http.server.HTTPServer(("127.0.0.1", 0), класс)
        нить = threading.Thread(target=сервер.serve_forever, daemon=True); нить.start()
        try:
            проба(подпись, наше_приложение(сервер.server_address[1]) is ожидаем)
        finally:
            сервер.shutdown(); сервер.server_close()

    # 3. Команда запуска и реестр собираются связно.
    корень = Path(tempfile.mkdtemp(prefix="table_selftest_"))
    строка = команда(корень, 41234)
    проба("в команде есть папка приложения", any("tablica" in ч for ч in строка))
    проба("в команде есть порт", "41234" in строка)
    проба("в команде есть имя и данные", "--имя" in строка and "--данные" in строка)
    док = реестр(корень, 41234)
    проба("реестр знает порт", док["ui"]["port"] == 41234)
    проба("реестр помечен установленным", док["installed"] is True)
    shutil.rmtree(корень, ignore_errors=True)

    # 4. СКВОЗНАЯ ПРОВЕРКА: поднимаем ТОТ САМЫЙ сервер, что уезжает покупателю.
    #
    # Без неё самопроверка щупала только свою обвязку: гейт check_self_check
    # вырезал у сервера метод do_DELETE, а проверка всё равно отвечала успехом —
    # то есть давала ложную уверенность. Поэтому здесь запускается настоящий
    # сервер и опрашиваются его методы.
    корень2 = Path(tempfile.mkdtemp(prefix="table_e2e_"))
    (корень2 / "current").mkdir(parents=True, exist_ok=True)
    for имя_файла in ("cabinet_server.py", "apps"):
        источник = HERE / имя_файла
        назначение = корень2 / "current" / имя_файла
        if источник.is_dir():
            shutil.copytree(источник, назначение)
        else:
            shutil.copy2(источник, назначение)
    порт2 = выбрать_порт(41500)
    сервер2 = subprocess.Popen(команда(корень2, порт2),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        проба("упакованный сервер поднимается и отдаёт приложение", дождаться(порт2, 15.0))

        def код_ответа(метод):
            запрос = urllib.request.Request(f"http://127.0.0.1:{порт2}/", method=метод)
            try:
                with urllib.request.urlopen(запрос, timeout=4) as о:
                    return о.status
            except urllib.error.HTTPError as о:
                return о.code
            except Exception:
                return 0

        проба("DELETE отвечает осознанным отказом 405", код_ответа("DELETE") == 405)
        проба("PUT отвечает осознанным отказом 405", код_ответа("PUT") == 405)
        проба("PATCH отвечает осознанным отказом 405", код_ответа("PATCH") == 405)
    finally:
        сервер2.terminate()
        try:
            сервер2.wait(timeout=10)
        except Exception:  # noqa: BLE001
            сервер2.kill()
        shutil.rmtree(корень2, ignore_errors=True)

    if провалы:
        print("ИТОГ: провалы — " + "; ".join(провалы))
        return 1
    print("ИТОГ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("--root", type=Path, default=Path.home() / ".extella" / APP_ID)
    р.add_argument("--registry-root", type=Path,
                   default=Path.home() / "extella-plugins" / "_registry")
    р.add_argument("--no-autostart", dest="no_autostart", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return _selftest()
    root = а.root.expanduser().resolve()
    реестр_путь = а.registry_root.expanduser().resolve()
    try:
        снять_по_pid(root)
        остановить_прежнее()
        разложить(root / "current")
        порт = выбрать_порт(DEFAULT_PORT)
        реестр_путь.mkdir(parents=True, exist_ok=True)
        файл = реестр_путь / f"{APP_ID}.json"
        файл.write_text(json.dumps(реестр(root, порт), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        вручную = subprocess.list2cmdline(команда(root, порт))
        if а.no_autostart:
            log("installed", version=VERSION, port=порт, autostart="пропущен по просьбе",
                registry=str(файл), start_by_hand=вручную)
            return 0
        if IS_MAC:
            авто = автозапуск_мак(root, порт)
        elif IS_LINUX:
            авто = автозапуск_линукс(root, порт)
        elif IS_WINDOWS:
            авто = автозапуск_windows(root, порт)
        else:
            авто = f"нет: неизвестная платформа {sys.platform}"
        запустить_отдельно(root, порт)
        живой = дождаться(порт)
        log("installed", version=VERSION, port=порт, autostart=авто, healthy=живой,
            registry=str(файл), start_by_hand=вручную,
            hint=None if живой else "сервер пока не ответил — поднимите его командой start_by_hand")
        return 0 if живой else 1
    except Exception as ошибка:  # noqa: BLE001
        log("failed", error=str(ошибка))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
