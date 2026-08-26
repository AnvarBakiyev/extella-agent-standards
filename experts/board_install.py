# Эксперт-установщик продукта «Schemes Board» (cspl=nohup, скоуп агента продукта)
# description: Installer for the «Schemes Board» product. The platform runs this expert on the buyer's device right after purchase or reinstall. It downloads the product archive from the store, unpacks it into a temporary folder and runs install.py from the archive root, which lays out the board, registers an autostart service and proves the window answers. Returns a JSON report: what was downloaded, where it was unpacked, what install.py printed and its exit code. Params: version — optional version to install (default: the one the platform passes in EXTELLA_APP_VERSION).
#
# ЗАЧЕМ ОН ЕСТЬ. Замер 25–26.08.2026: коллега владельца установила Доску из
# магазина, установка «прошла» — приложение не заработало. Разбор показал два
# разных промаха подряд:
#   1) в версии не было программы вовсе — только страница окна;
#   2) когда программу приложили, я записал в installer_expert ИМЯ ФАЙЛА
#      («install.py»). А платформа зовёт ЭКСПЕРТА по имени: такого эксперта не
#      нашлось, и установка тихо не произошла. Снаружи опять «успешно».
#
# УСТРОЙСТВО. Платформа запускает этого эксперта НА УСТРОЙСТВЕ покупателя.
# Он забирает архив версии по адресу /api/app-archive, распаковывает и отдаёт
# работу install.py — тому самому, что уже проверен на чистой машине.
#
# ГРАНИЦЫ. Ничего не решает сам: вся логика раскладки живёт в install.py внутри
# архива, и меняется вместе с продуктом, а не с этим экспертом.

import json, os, subprocess, sys, tempfile, urllib.request, zipfile, shutil

ОС_БАЗА = (os.environ.get("EXTELLA_OS_BASE") or "https://os.extella.ai").rstrip("/")
ПРИЛОЖЕНИЕ = os.environ.get("EXTELLA_APP_NAME") or "Schemes Board"
ВЕРСИЯ = """{{version}}""".strip()
if not ВЕРСИЯ or ВЕРСИЯ.startswith("{{"):
    ВЕРСИЯ = (os.environ.get("EXTELLA_APP_VERSION") or "").strip()
ТОКЕН = (os.environ.get("EXTELLA_AUTH_TOKEN") or "").strip()


def отчёт(**поля):
    print(json.dumps(поля, ensure_ascii=False), flush=True)


def беда(почему, **ещё):
    # Честный отказ: платформа и человек должны узнать причину сразу, а не
    # обнаружить пустое окно через неделю.
    отчёт(ok=False, почему=почему, **ещё)
    raise SystemExit(2)


адрес = ОС_БАЗА + "/api/app-archive?app=" + urllib.request.quote(ПРИЛОЖЕНИЕ)
if ВЕРСИЯ:
    адрес += "&version=" + urllib.request.quote(ВЕРСИЯ)

временная = tempfile.mkdtemp(prefix="extella_board_")
архив = os.path.join(временная, "пакет.zip")
try:
    запрос = urllib.request.Request(адрес)
    if ТОКЕН:
        запрос.add_header("X-Auth-Token", ТОКЕН)
    with urllib.request.urlopen(запрос, timeout=600) as о, open(архив, "wb") as ф:
        shutil.copyfileobj(о, ф)
except Exception as е:
    беда("архив продукта не скачался: %s" % str(е)[:200], адрес=адрес)

размер = os.path.getsize(архив) / 1048576.0
if размер < 0.01:
    беда("архив пустой (%.2f МБ) — платформе нечего было отдать" % размер)

куда = os.path.join(временная, "распаковано")
try:
    with zipfile.ZipFile(архив) as пакет:
        # Пути с «..» и абсолютные — отказ: архив пришёл извне, и разложить его
        # мимо своей папки он не должен даже случайно.
        for имя in пакет.namelist():
            чистое = имя.replace("\\", "/")
            if чистое.startswith("/") or ".." in чистое.split("/"):
                беда("небезопасный путь в архиве: %s" % имя[:80])
        пакет.extractall(куда)
except zipfile.BadZipFile:
    беда("архив версии не является zip (%.2f МБ)" % размер)

# install.py обязан лежать в КОРНЕ архива (правило B1). Если его там нет —
# пакет собран неверно, и говорим об этом прямо, а не ищем по всем папкам.
установщик = os.path.join(куда, "install.py")
if not os.path.isfile(установщик):
    беда("в корне архива нет install.py",
         что_есть=sorted(os.listdir(куда))[:8])

среда = dict(os.environ)
среда.setdefault("EXTELLA_APP_NAME", ПРИЛОЖЕНИЕ)
if ВЕРСИЯ:
    среда["EXTELLA_APP_VERSION"] = ВЕРСИЯ

try:
    итог = subprocess.run([sys.executable, установщик], cwd=куда, env=среда,
                          capture_output=True, text=True, timeout=1800)
except subprocess.TimeoutExpired:
    беда("установщик не завершился за 30 минут")

вывод = ((итог.stdout or "") + (итог.stderr or "")).strip()
if итог.returncode != 0:
    беда("установщик вернул код %d" % итог.returncode, вывод=вывод[-800:])

отчёт(ok=True, приложение=ПРИЛОЖЕНИЕ, версия=ВЕРСИЯ or "?",
      архив_мб=round(размер, 2), вывод=вывод[-800:])
try:
    shutil.rmtree(временная)
except OSError:
    pass
