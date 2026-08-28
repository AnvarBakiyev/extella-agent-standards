$extens("include.py")
include("import os", [])
include("import subprocess", [])

def pkg_install(package: str = "", **extra) -> dict:
    """Install a system package on THIS device via its native package manager
    (brew on macOS, winget on Windows, apt on Linux) and prove the install by
    finding the binary afterwards. Params: package — the package name.

    Проба гипотезы Тимура 28.08.2026: эксперт-установщик может ставить не
    только наши приложения, а ЛЮБОЙ софт — dmg, exe, пакеты. Это делает
    канал «магазин → устройство» универсальной доставкой.

    ГРАНИЦЫ. Ставит — да; удалять и обновлять чужое — нет. Один пакет за
    вызов, имя без пробелов и флагов: командную строку из параметров не
    собираем.
    """
    import os, subprocess, sys, time, platform, socket, shutil

    where = {"system": platform.system(), "machine": socket.gethostname()[:40]}
    name = (package or "").strip()
    if not name or any(c in name for c in " ;|&$"):
        return dict(where, ok=False, reason="pass a bare package name in params.package")

    system = sys.platform
    if system == "darwin":
        brew = next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew")
                     if os.path.isfile(p)), "")
        if not brew:
            return dict(where, ok=False, reason="Homebrew is not installed")
        cmd = [brew, "install", name]
    elif system.startswith("win"):
        cmd = ["winget", "install", "--id", name, "--silent",
               "--accept-package-agreements", "--accept-source-agreements"]
    else:
        cmd = ["sudo", "-n", "apt-get", "install", "-y", name]

    started = time.time()
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return dict(where, ok=False, reason="install did not finish in 15 minutes")
    took_ms = int((time.time() - started) * 1000)

    found = shutil.which(name) or next(
        (p for p in ("/opt/homebrew/bin/" + name, "/usr/local/bin/" + name)
         if os.path.isfile(p)), "")
    if done.returncode != 0 and not found:
        return dict(where, ok=False, took_ms=took_ms,
                    reason="package manager exited with code %d" % done.returncode,
                    output=((done.stdout or "") + (done.stderr or ""))[-400:])
    # Доказательство — бинарь на диске, а не код возврата менеджера.
    if not found:
        return dict(where, ok=False, took_ms=took_ms,
                    reason="manager reported success but the binary was not found")
    return dict(where, ok=True, package=name, binary=found, took_ms=took_ms)
