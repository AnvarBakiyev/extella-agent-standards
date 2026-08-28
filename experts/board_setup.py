$extens("include.py")
include("import json", [])
include("import os", [])
include("import shutil", [])
include("import subprocess", [])
include("import sys", [])
include("import tempfile", [])
include("import urllib.request", [])
include("import zipfile", [])

def _установить2(app_name: str = "", version: str = "", token: str = "",
                agent_id: str = "", **прочее) -> dict:
    """Installer for «Schemes Board». Downloads the product archive from the
    Extella OS store, unpacks it and runs install.py from the archive root:
    lays out the board, registers an autostart service and proves the window
    answers. Returns a report: what was downloaded, what install.py printed,
    and the exit code. Params: version — optional version to install.

    ПРИНИМАЕМ ВСЁ, ЧТО ШЛЁТ ПЛАТФОРМА, И ЕЩЁ **прочее.
    Замер на Windows владельца 28.08.2026: платформа зовёт установщик с
    четырьмя именованными аргументами — app_name, version, token, agent_id.
    Функция знала только version и падала на первом же:
    «got an unexpected keyword argument 'app_name'». Путь до устройства при
    этом РАБОТАЛ — эксперт доехал и запустился. Открытый **прочее** оставлен
    намеренно: платформа вправе добавить пятый аргумент, и это не должно
    ронять установку у всех покупателей разом.

    ФОРМАТ ЭТОГО ЭКСПЕРТА — ОБЫЧНЫЙ (fython), И ЭТО ГЛАВНОЕ.
    Прежняя редакция была написана как nohup-эксперт: сырой код, запуск в
    фоне, платформе возвращался номер процесса. Из-за этого установка из
    магазина не работала ТРИ ДНЯ, и выглядело это так, будто виноват код
    установки. На деле: платформа зовёт установщик и сразу пишет
    «installer_done» — фоновому запуску нечего ей ответить, ждать нечего.
    А на чужой машине фоновый запуск ещё и требует отдельно
    зарегистрированного обработчика, которого там может не быть вовсе.

    Рабочий образец на том же аккаунте — `install_open_design` — сделан
    обычным экспертом с `def` и `return`. Здесь так же: платформа дожидается
    ответа и видит, чем кончилось.
    """
    import json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile

    ОС_БАЗА = (os.environ.get("EXTELLA_OS_BASE") or "https://os.extella.ai").rstrip("/")
    # Имя и версию берём ОТ ПЛАТФОРМЫ, если она их назвала: она знает, какую
    # именно версию покупает человек, а среда на устройстве — нет.
    ПРИЛОЖЕНИЕ = (app_name or "").strip() or os.environ.get("EXTELLA_APP_NAME") or "Schemes Board"
    # СТАРШИНСТВО ВЕРСИИ, И ПОРЯДОК ЗДЕСЬ НЕ СЛУЧАЕН.
    # 1) что назвала платформа в вызове — она знает, что покупает человек;
    # 2) самая свежая в магазине — если вызов промолчал (кнопка «поставить»);
    # 3) переменная среды — ПОСЛЕДНЯЯ, потому что на устройстве она хранит
    #    версию ПРОШЛОЙ установки. Замер 28.08.2026: из-за неё эксперт снова и
    #    снова качал архив 0.1.1, хотя в магазине лежала 0.2.3, — и каждая
    #    новая попытка честно воспроизводила вчерашнюю ошибку.
    ВЕРСИЯ = (version or "").strip()
    if ВЕРСИЯ.startswith("{{"):
        ВЕРСИЯ = ""

    def свежая_версия():
        """Самая новая версия продукта в магазине.

        ЗАМЕР 28.08.2026, И ЭТО ОБЪЯСНЯЕТ ЦЕЛЫЙ ДЕНЬ ХОЖДЕНИЯ ПО КРУГУ.
        Магазин отдаёт архив, ПРИВЯЗАННЫЙ К ПОКУПКЕ, а не последний: запрос без
        номера версии вернул архив 0.1.1, хотя выложены уже 0.2.3. То есть все
        исправления установщика — английский вывод, кодировка, аргументы —
        лежали в новых версиях, а на устройство покупателя приезжал старый
        файл. Каждая новая попытка честно воспроизводила вчерашнюю ошибку.

        Поэтому: если версию не назвали, спрашиваем магазин сами и берём
        верхнюю. Не вышло спросить — работаем как раньше, по покупке.
        """
        try:
            з = urllib.request.Request(
                ОС_БАЗА + "/api/listing/d117273e-9f8a-46bd-9410-1e2c2f750a07")
            з.add_header("X-Extella-Token", ТОКЕН)
            з.add_header("X-Auth-Token", ТОКЕН)
            д = json.loads(urllib.request.urlopen(з, timeout=60).read())
            версии = [str(в.get("version") or "") for в in (д.get("versions") or [])]
            версии = [в for в in версии if в]
            if not версии:
                return ""
            # Сортируем по числам, а не по буквам: «0.2.10» новее «0.2.9».
            def ключ(в):
                try:
                    return [int(ч) for ч in в.split(".")]
                except ValueError:
                    return [0]
            return sorted(версии, key=ключ)[-1]
        except Exception:
            return ""

    def токен():
        """Токен, которым магазин ОС отдаёт архив.

        У магазина (os.extella.ai) СВОЙ токен, у ядра (api.extella.ai) — свой,
        и они разные: сверено отпечатками 27.08.2026. Эксперт брал только
        ядровый, из среды, и магазин отвечал отказом 401 — установка падала, а
        покупатель видел успешную покупку и пустое окно. Первым спрашиваем
        файл, который САМО приложение Extella заводит на каждой машине.
        """
        дом = os.path.expanduser("~")
        for путь in (os.path.join(дом, ".extella", "os_token.txt"),
                     os.path.join(дом, ".extella", "api_token.txt")):
            try:
                з = open(путь, encoding="utf-8").read().strip()
                if з:
                    return з
            except OSError:
                pass
        из_среды = (os.environ.get("EXTELLA_AUTH_TOKEN") or "").strip()
        if из_среды:
            return из_среды
        try:
            с = json.load(open(os.path.join(дом, "extella_wizard", "app", "config.json"),
                               encoding="utf-8"))
            return str(с.get("auth_token") or "").strip()
        except Exception:
            return ""

    def где_я():
        """Чем машина, на которой всё это происходит. В ответе это важнее
        всего: без такой подписи «установилось» и «установилось НЕ ТУДА»
        выглядят одинаково — замер 27.08.2026, когда установка ушла на
        устройство по умолчанию вместо компьютера покупателя."""
        try:
            import platform, socket
            return {"система": platform.system(), "разрядность": platform.machine(),
                    "машина": socket.gethostname()[:40]}
        except Exception:
            return {}

    # ТОКЕН ОТ ПЛАТФОРМЫ — ПЕРВЫЙ ПО СТАРШИНСТВУ. Он выдан под эту установку
    # и не зависит от того, что лежит на диске у покупателя.
    ТОКЕН = (token or "").strip() or токен()
    где = где_я()
    if not ТОКЕН:
        return dict(где, ok=False,
                    почему="не нашёл токен Extella на этом компьютере. Обычно он "
                           "лежит в ~/.extella/os_token.txt и появляется сам после "
                           "первого запуска приложения Extella — откройте его один "
                           "раз и повторите установку")

    # ОТКУДА ВЗЯЛАСЬ ВЕРСИЯ — записываем прямо в отчёт. Без этого спор
    # «параметр не дошёл» против «запрос упал» не решается ничем, кроме догадок.
    откуда = "вызов" if ВЕРСИЯ else ""
    спрошено = ""
    if not ВЕРСИЯ:
        try:
            спрошено = свежая_версия()
        except Exception as е:
            спрошено = "ОШИБКА: %s" % str(е)[:80]
        if спрошено and not спрошено.startswith("ОШИБКА"):
            ВЕРСИЯ, откуда = спрошено, "магазин"
    if not ВЕРСИЯ:
        ВЕРСИЯ = (os.environ.get("EXTELLA_APP_VERSION") or "").strip()
        откуда = "среда устройства"

    адрес = ОС_БАЗА + "/api/app-archive?app=" + urllib.request.quote(ПРИЛОЖЕНИЕ)
    if ВЕРСИЯ:
        адрес += "&version=" + urllib.request.quote(ВЕРСИЯ)

    временная = tempfile.mkdtemp(prefix="extella_board_")
    архив = os.path.join(временная, "пакет.zip")
    try:
        запрос = urllib.request.Request(адрес)
        # Магазин принимает «X-Extella-Token»; ядро знает обратный заголовок.
        # Шлём оба — лишний никому не мешает, а отсутствующий стоил трёх дней.
        запрос.add_header("X-Extella-Token", ТОКЕН)
        запрос.add_header("X-Auth-Token", ТОКЕН)
        with urllib.request.urlopen(запрос, timeout=600) as о:
            with open(архив, "wb") as ф:
                shutil.copyfileobj(о, ф)
    except Exception as е:
        return dict(где, ok=False, адрес=адрес,
                    почему="архив продукта не скачался: %s" % str(е)[:200])

    размер = os.path.getsize(архив) / 1048576.0
    if размер < 0.01:
        return dict(где, ok=False,
                    почему="архив пустой (%.2f МБ) — платформе нечего было отдать" % размер)

    куда = os.path.join(временная, "распаковано")
    try:
        пакет = zipfile.ZipFile(архив)
        # Пути с «..» и абсолютные — отказ: архив пришёл извне и раскладываться
        # мимо своей папки не должен даже случайно.
        for имя in пакет.namelist():
            чистое = имя.replace("\\", "/")
            if чистое.startswith("/") or ".." in чистое.split("/"):
                return dict(где, ok=False,
                            почему="небезопасный путь в архиве: %s" % имя[:80])
        пакет.extractall(куда)
        пакет.close()
    except zipfile.BadZipFile:
        return dict(где, ok=False,
                    почему="архив версии не является zip (%.2f МБ)" % размер)

    # install.py обязан лежать в КОРНЕ архива (правило B1): если его там нет,
    # пакет собран неверно — говорим прямо, а не ищем по всем папкам.
    установщик = os.path.join(куда, "install.py")
    if not os.path.isfile(установщик):
        return dict(где, ok=False, почему="в корне архива нет install.py",
                    что_есть=sorted(os.listdir(куда))[:8])

    среда = dict(os.environ)
    # ЧИТАЕМ И ПИШЕМ ТОЛЬКО В UTF-8. Установщик говорит по-русски, а консоль
    # Windows живёт в своей однобайтовой кодировке: замер на Windows ARM64
    # владельца 28.08.2026 — поток чтения упал с UnicodeDecodeError, вывод
    # потерялся целиком, и от установщика осталось голое «код 2» без причины.
    # Человек в этот момент видит «не установилось» и ни слова почему.
    среда["PYTHONIOENCODING"] = "utf-8"
    среда["PYTHONUTF8"] = "1"
    среда["EXTELLA_APP_NAME"] = ПРИЛОЖЕНИЕ
    # B4: агента называет платформа — install.py запишет привязку в настройку
    # продукта. Из среды устройства этого не узнать: там мог остаться агент
    # прошлой покупки.
    if agent_id:
        среда["EXTELLA_AGENT_ID"] = agent_id
    if ВЕРСИЯ:
        среда["EXTELLA_APP_VERSION"] = ВЕРСИЯ

    try:
        итог = subprocess.run([sys.executable, установщик], cwd=куда, env=среда,
                              capture_output=True, text=True, timeout=1800,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return dict(где, ok=False, почему="установщик не завершился за 30 минут")

    вывод = ((итог.stdout or "") + (итог.stderr or "")).strip()
    try:
        shutil.rmtree(временная)
    except OSError:
        pass

    if итог.returncode != 0:
        # ПУСТОЙ ВЫВОД — ТОЖЕ ОТВЕТ, и о нём надо сказать словами. Иначе
        # человек получает «код 2» и никакого следа, куда смотреть дальше.
        почему = "установщик вернул код %d" % итог.returncode
        if not вывод:
            почему += " и не сказал ни слова — вывод потерялся по дороге"
        return dict(где, ok=False, вывод=вывод[-900:], почему=почему)
    return dict(где, ok=True, приложение=ПРИЛОЖЕНИЕ, версия=ВЕРСИЯ or "?",
                архив_мб=round(размер, 2), вывод=вывод[-900:],
                версия_откуда=откуда, магазин_ответил=спрошено or "—",
                ос_база=ОС_БАЗА)


def board_setup(app_name: str = "", version: str = "", token: str = "",
                  agent_id: str = "", **прочее) -> dict:
    """Обёртка: делает работу и КЛАДЁТ ОТЧЁТ ТУДА, ГДЕ ЕГО ВИДНО ИЗДАЛЕКА.

    Ответ эксперта уходит в задачу, а списка задач у платформы нет — по номеру
    из окна результат не достать (проверено: /api/tasks/list и соседи отвечают
    404). Пока у покупателя старое окно, отчёт до экрана может не дойти, и
    разбор снова идёт вслепую. След это закрывает.

    Личного здесь нет: имя компьютера, название системы и текст нашего же
    установщика. Сбой записи следа установку не роняет — она вспомогательная.
    """
    import json, os, urllib.request

    итог = _установить2(app_name=app_name, version=version, token=token,
                       agent_id=agent_id, **прочее)
    try:
        з = urllib.request.Request(
            "https://api.extella.ai/api/kv/set",
            data=json.dumps({"key": "board_install_последний_отчёт",
                             "value": json.dumps(итог, ensure_ascii=False)[:4000]}).encode(),
            headers={"X-Auth-Token": os.environ.get("EXTELLA_AUTH_TOKEN") or token or "",
                     "X-Profile-Id": "default",
                     "X-Agent-Id": (agent_id or os.environ.get("EXTELLA_AGENT_ID")
                                    or "agent_YbDQpKySopyi1ejHyQZuQ"),
                     "Content-Type": "application/json"})
        urllib.request.urlopen(з, timeout=60).read()
    except Exception:
        pass
    return итог
