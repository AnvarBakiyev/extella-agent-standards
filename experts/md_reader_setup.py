$extens("include.py")
include("import json", [])
include("import os", [])
include("import shutil", [])
include("import subprocess", [])
include("import sys", [])
include("import tempfile", [])
include("import urllib.request", [])
include("import zipfile", [])

def md_reader_setup(app_name: str = "", version: str = "", token: str = "",
                agent_id: str = "", **extra) -> dict:
    """Installer for «MD Reader». Picks the newest published version,
    downloads its archive from the Extella OS store, unpacks it and runs
    install.py from the archive root: lays out the board, registers an
    autostart service and proves the window answers. Returns a report naming
    the machine it ran on. The platform passes app_name, version, token,
    agent_id; extra keyword arguments are accepted and ignored on purpose.

    ВЕСЬ КОД ЗДЕСЬ ЛАТИНИЦЕЙ, И ЭТО НЕ ВКУСОВЩИНА.
    Замер на Windows владельца 28.08.2026: тот же самый эксперт с русскими
    именами переменных падал на его устройстве с «invalid decimal literal
    (<container>, line 1)» — сборка контейнера не пережила кириллицу в
    идентификаторах. На macOS код работал, поэтому поломка выглядела как «у
    него что-то с машиной», и на этом мы потеряли день. Рабочий эталон
    платформы (install_open_design) написан латиницей целиком — теперь и этот.

    ОДНА ФУНКЦИЯ НА ФАЙЛ. Когда рядом лежала вторая (обёртка, писавшая отчёт),
    листенер взял ПЕРВУЮ по файлу и упал ещё до кода: «Function: _установить2».

    ФОРМАТ — ОБЫЧНЫЙ (fython), НЕ nohup. Фоновому запуску нечего ответить
    платформе: она пишет «installer_done» сразу и не ждёт, а на чужой машине
    фоновый запуск ещё и требует отдельно зарегистрированного обработчика.
    """
    import json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile

    OS_BASE = (os.environ.get("EXTELLA_OS_BASE") or "https://os.extella.ai").rstrip("/")
    LISTING = "f3c3c08a-3491-4ba9-ba77-9541c1c3dccf"
    APP = (app_name or "").strip() or os.environ.get("EXTELLA_APP_NAME") or "MD Reader"

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
        API one — verified by fingerprint 27.08.2026, and the mismatch cost
        three days of silent 401s. The file below is written by the Extella app
        itself, so every buyer has it on any system. A token supplied by the
        platform wins: it is issued for this very install."""
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
        from_env = (os.environ.get("EXTELLA_AUTH_TOKEN") or "").strip()
        if from_env:
            return from_env
        try:
            cfg = json.load(open(os.path.join(home, "extella_wizard", "app",
                                              "config.json"), encoding="utf-8"))
            return str(cfg.get("auth_token") or "").strip()
        except Exception:
            return ""

    def fetch(url, auth):
        req = urllib.request.Request(url)
        # The store accepts «X-Extella-Token»; the core knows the other one.
        # Sending both costs nothing; sending only one cost three days.
        req.add_header("X-Extella-Token", auth)
        req.add_header("X-Auth-Token", auth)
        return urllib.request.urlopen(req, timeout=900)

    def newest_version(auth):
        """The store serves the archive BOUND TO THE PURCHASE, not the latest
        one: a request without a version returned 0.1.1 while 0.3.0 was already
        published. Every fix shipped in a new version therefore never reached
        the device. Ask the store for the top version instead."""
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
                    reason="no Extella token on this computer. It normally lives in "
                           "~/.extella/os_token.txt and appears after the first run "
                           "of the Extella app — open it once and install again")

    wanted = (version or "").strip()
    if wanted.startswith("{{"):
        wanted = ""
    picked_from = "call" if wanted else ""
    if not wanted:
        wanted = newest_version(auth)
        picked_from = "store" if wanted else ""
    if not wanted:
        wanted = (os.environ.get("EXTELLA_APP_VERSION") or "").strip()
        picked_from = "device env"

    url = OS_BASE + "/api/app-archive?app=" + urllib.request.quote(APP)
    if wanted:
        url += "&version=" + urllib.request.quote(wanted)

    workdir = tempfile.mkdtemp(prefix="extella_mdreader_")
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
