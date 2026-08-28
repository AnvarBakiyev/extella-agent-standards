$extens("include.py")
include("import os", [])
include("import json", [])
include("import urllib.request", [])

def uptime_check(**extra) -> dict:
    """Check the health of local Extella apps and key sites, write a snapshot
    file for the window to read, return a summary. This is the «pulse without
    a daemon» probe: a system scheduler wakes this code up every few minutes —
    no always-running process, no Docker, no socket.io.

    Проба гипотезы 28.08.2026: uptime-kuma (Docker + демон) заменяется на
    «эксперт по расписанию + окно читает снимок файлом».
    """
    import os, json, time, socket, platform, urllib.request

    checks = [
        ("Schemes Board", "http://127.0.0.1:34786/_extella_version"),
        ("Table",         "http://127.0.0.1:34787/"),
        ("MD Reader",     "http://127.0.0.1:34796/"),
        ("Extella OS",    "https://os.extella.ai/"),
    ]
    results = []
    for name, url in checks:
        started = time.time()
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                ok = 200 <= r.status < 400
        except Exception:
            ok = False
        results.append({"name": name, "url": url, "ok": ok,
                        "ms": int((time.time() - started) * 1000)})

    snapshot = {"when": time.strftime("%Y-%m-%d %H:%M:%S"),
                "machine": socket.gethostname()[:40],
                "system": platform.system(),
                "results": results}
    path = os.path.join(os.path.expanduser("~"), ".extella", "watchman_snapshot.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

    up = sum(1 for r in results if r["ok"])
    return {"ok": True, "up": up, "total": len(results),
            "snapshot": path, "when": snapshot["when"],
            "machine": snapshot["machine"]}
