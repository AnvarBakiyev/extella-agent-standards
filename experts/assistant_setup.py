$extens("include.py")
include("import json", [])
include("import os", [])
include("import shutil", [])
include("import subprocess", [])
include("import sys", [])
include("import tempfile", [])
include("import urllib.request", [])
include("import zipfile", [])

def assistant_setup(app_name: str = "", version: str = "", token: str = "",
                agent_id: str = "", **extra) -> dict:
    """Installer for «Personal Assistant». Picks the newest published version,
    downloads its archive from the Extella OS store, unpacks it and runs
    install.py from the archive root: runs the product installer from the archive root and reports its output. Returns a report naming the machine
    it ran on. The platform passes app_name, version, token, agent_id; extra
    keyword arguments are accepted and ignored on purpose.

    ЗАЧЕМ ЭТОТ ФАЙЛ ПОЯВИЛСЯ. Замер витрины 18.09.2026: архив и install.py на месте (в архиве есть Dockerfile,
    requirements.txt и assistant.py), а поле installer_expert пустое. Автозапуска
    install.py не ставит вовсе — это законно, но установить продукт было нечем.
    Канон H98: объявлен архив — обязан быть installer_expert.

    ВЕСЬ КОД ЗДЕСЬ ЛАТИНИЦЕЙ, И ЭТО НЕ ВКУСОВЩИНА. Замер на Windows владельца
    28.08.2026: тот же эксперт с русскими именами переменных падал на его
    устройстве с «invalid decimal literal (<container>, line 1)» — сборка
    контейнера не переживает кириллицу в идентификаторах.

    ОДНА ФУНКЦИЯ НА ФАЙЛ. Когда рядом лежала вторая, листенер брал ПЕРВУЮ по
    файлу и падал ещё до кода. Поэтому здесь нет ни помощников, ни selftest.

    ФОРМАТ — ОБЫЧНЫЙ (fython), НЕ nohup: фоновому запуску нечего ответить
    платформе, она пишет «installer_done» сразу и не ждёт.
    """
    import json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile

    OS_BASE = (os.environ.get("EXTELLA_OS_BASE") or "https://os.extella.ai").rstrip("/")
    LISTING = "c65b47cf-8a6e-496c-af1d-2752ce73896d"
    APP = (app_name or "").strip() or os.environ.get("EXTELLA_APP_NAME") or "Personal Assistant"

    def where_am_i():
        """Which machine this actually ran on. Without it «installed» and
        «installed ON THE WRONG MACHINE» look identical from outside."""
        try:
            import platform, socket
            return {"system": platform.system(), "arch": platform.machine(),
                    "machine": socket.gethostname()[:40]}
        except Exception:
            return {}

    def find_token():
        """The store (os.extella.ai) has its OWN token, different from the core
        API one. A token supplied by the platform wins: it is issued for this
        very install.

        ВНИМАНИЕ, ЗАМЕР 16.09.2026 НА ЧИСТОЙ WINDOWS. Прежняя редакция этого
        комментария утверждала, что файл пишет само приложение Extella «и
        поэтому он есть у каждого покупателя на любой системе». Это неверно:
        на Windows приложение кладёт в ~/.extella только device.txt, токена там
        нет, и установщик умирает молча. Поэтому отказ ниже назван словами —
        человек должен понять, что делать."""
        if (token or "").strip():
            return token.strip()
        home = os.path.expanduser("~")
        for path in (os.path.join(home, ".extella", "os_token.txt"),
                     os.path.join(home, ".extella", "api_token.txt")):
            try:
                value = open(path, encoding="utf-8").read().strip()
                if value:
                    return value
            except OSError:
                pass
        return (os.environ.get("EXTELLA_AUTH_TOKEN") or "").strip()

    def fetch(url, auth):
        req = urllib.request.Request(url)
        # The store accepts «X-Extella-Token»; the core knows the other one.
        # Sending both costs nothing; sending only one cost three days.
        req.add_header("X-Extella-Token", auth)
        req.add_header("X-Auth-Token", auth)
        return urllib.request.urlopen(req, timeout=900)

    def newest_version(auth):
        """The store serves the archive BOUND TO THE PURCHASE, not the latest
        one. Ask the store for the top version instead."""
        try:
            data = json.loads(fetch(OS_BASE + "/api/listing/" + LISTING, auth).read())
            names = [str(v.get("version") or "") for v in (data.get("versions") or [])]
            names = [n for n in names if n]
            if not names:
                return ""

            def as_numbers(name):
                try:
                    return [int(part) for part in name.split(".")]
                except ValueError:
                    return [0]

            return sorted(names, key=as_numbers)[-1]
        except Exception:
            return ""

    where = where_am_i()
    auth = find_token()
    if not auth:
        return dict(where, ok=False,
                    reason="no Extella store token on this computer. The platform "
                           "did not pass one, and the file is missing too. Expected "
                           "at ~/.extella/os_token.txt. On Windows the Extella app "
                           "does not create this file (measured 16.09.2026) — copy "
                           "it there by hand from a machine that has it, then "
                           "install again")

    wanted = (version or "").strip()
    if wanted.startswith("{{"):
        wanted = ""
    picked_from = "call" if wanted else ""
    if not wanted:
        wanted = newest_version(auth)
        picked_from = "store" if wanted else ""

    url = OS_BASE + "/api/app-archive?app=" + urllib.request.quote(APP)
    if wanted:
        url += "&version=" + urllib.request.quote(wanted)

    workdir = tempfile.mkdtemp(prefix="extella_assistant_")
    archive = os.path.join(workdir, "package.zip")
    try:
        with open(archive, "wb") as out:
            shutil.copyfileobj(fetch(url, auth), out)
    except Exception as err:
        return dict(where, ok=False, url=url,
                    reason="could not download the product archive: %s" % str(err)[:200])

    size_mb = os.path.getsize(archive) / 1048576.0
    if size_mb < 0.01:
        return dict(where, ok=False,
                    reason="the archive is empty (%.2f MB) — the store had nothing to give" % size_mb)

    unpacked = os.path.join(workdir, "unpacked")
    try:
        bundle = zipfile.ZipFile(archive)
        # Paths with «..» or absolute ones are refused: the archive comes from
        # outside and must not unpack anywhere but its own folder.
        for name in bundle.namelist():
            clean = name.replace("\\", "/")
            if clean.startswith("/") or ".." in clean.split("/"):
                return dict(where, ok=False, reason="unsafe path in archive: %s" % name[:80])
        bundle.extractall(unpacked)
        bundle.close()
    except zipfile.BadZipFile:
        return dict(where, ok=False,
                    reason="the version archive is not a zip (%.2f MB)" % size_mb)

    installer = os.path.join(unpacked, "install.py")
    if not os.path.isfile(installer):
        return dict(where, ok=False, reason="no install.py in the archive root",
                    found=sorted(os.listdir(unpacked))[:8])

    env = dict(os.environ)
    # Read and write UTF-8 only: a Windows console decodes in its own code page
    # and silently drops the installer's output otherwise.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["EXTELLA_APP_NAME"] = APP
    if wanted:
        env["EXTELLA_APP_VERSION"] = wanted
    if agent_id:
        env["EXTELLA_AGENT_ID"] = agent_id

    try:
        done = subprocess.run([sys.executable, installer], cwd=unpacked, env=env,
                              capture_output=True, text=True, timeout=1800,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return dict(where, ok=False, reason="the installer did not finish within 30 minutes")

    output = ((done.stdout or "") + (done.stderr or "")).strip()
    try:
        shutil.rmtree(workdir)
    except OSError:
        pass

    if done.returncode != 0:
        reason = "the installer exited with code %d" % done.returncode
        if not output:
            reason += " and said nothing — its output was lost on the way"
        return dict(where, ok=False, output=output[-900:], reason=reason)
    return dict(where, ok=True, app=APP, version=wanted or "?",
                version_from=picked_from, archive_mb=round(size_mb, 2),
                output=output[-900:])
