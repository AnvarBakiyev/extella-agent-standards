$extens("include.py")
include("import os", [])
include("import json", [])

def board_archive(app: str = "", snapshot: str = "", **extra) -> dict:
    """Cold archive for a page editor: the window keeps the hot copy itself and
    sends a snapshot here; this expert writes it to a durable file on the
    device, timestamped, keeping the last few versions. The "cold" half of the
    hybrid — hot in the window, archived on schedule. Params: app — product
    slug; snapshot — the payload (<=64KB per call, the channel limit).
    """
    import os, json, time, platform, socket
    where = {"system": platform.system(), "machine": socket.gethostname()[:40]}
    name = "".join(c for c in (app or "app") if c.isalnum() or c in "-_")[:40] or "app"
    home = os.path.expanduser("~")
    folder = os.path.join(home, ".extella", "page_archive", name)
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, stamp + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(snapshot or "")
    os.replace(tmp, path)
    # держим последние 5 снимков, старое подчищаем
    kept = sorted(p for p in os.listdir(folder) if p.endswith(".json"))
    for old in kept[:-5]:
        try: os.remove(os.path.join(folder, old))
        except OSError: pass
    return dict(where, ok=True, saved=path,
                size_kb=round(len(snapshot or "") / 1024, 1), kept=len(kept[-5:]))
