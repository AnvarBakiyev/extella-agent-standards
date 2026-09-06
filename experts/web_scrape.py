$extens("include.py")
include("import json", [])
include("import os", [])
include("import subprocess", [])

def web_scrape(url: str = "", extract: str = "", wait: str = "",
               screenshot: str = "", **extra) -> dict:
    """Read a web page on THIS device and return what a JS snippet extracts
    from it — without Docker, without a browser install, without a server.
    Uses Obscura, a 26 MB headless browser built from source on this machine.

    Params: url — the page to open; extract — JS expression evaluated in the
    page (defaults to the page title); wait — seconds to let the page settle
    (default 5); screenshot — optional file path for a PNG of the page.

    ЗАЧЕМ. Замер 06.09.2026: сбор данных с сайтов держался на Docker-контейнере
    с Chromium (лимит 3 ГБ). Obscura делает то же за 26 МБ на лёгкой странице и
    ~280 МБ на тяжёлой, стартует за 0,11 с вместо секунд и не требует ни
    контейнера, ни постоянно живущего процесса: запустился, отдал, умер.

    ЧЕГО НЕ ДЕЛАЕТ. Не рисует карты и видео — у Obscura свой движок, и тяжёлая
    графика ему не по силам (карта 2ГИС на снимке не отрисовалась). Для «человек
    смотрит и кликает в живом браузере» это не замена; для данных — замена.

    ГРАНИЦЫ, КОТОРЫЕ МЫ ДЕРЖИМ САМИ:
      * robots.txt уважаем всегда (--obey-robots): правила сайта — не помеха,
        а условие, на котором нас пускают;
      * режим скрытности НЕ включаем и в сборку не включали — обход защиты
        чужого сайта это риск для того, кто купил приложение, а не для нас;
      * во внутреннюю сеть не ходим: Obscura блокирует локальные адреса сам,
        и мы этот запрет не снимаем.

    Код латиницей: кириллица в идентификаторах валит сборку контейнера на
    Windows (замер 28.08.2026, «invalid decimal literal»).
    """
    import json, os, subprocess, time, platform, socket

    where = {"system": platform.system(), "machine": socket.gethostname()[:40]}
    target = (url or "").strip()
    if not target:
        return dict(where, ok=False, reason="no url given: pass params.url")
    if not (target.startswith("http://") or target.startswith("https://")):
        return dict(where, ok=False,
                    reason="only http(s) pages are read here, got: %s" % target[:60])

    home = os.path.expanduser("~")
    candidates = [os.path.join(home, "extella-apps", "obscura", "obscura"),
                  "/usr/local/bin/obscura", "/opt/homebrew/bin/obscura"]
    binary = next((p for p in candidates if os.path.isfile(p)), "")
    if not binary:
        return dict(where, ok=False,
                    reason="Obscura is not installed on this computer "
                           "(expected ~/extella-apps/obscura/obscura). Installing it "
                           "is the installer expert's job, not this one's")

    cmd = [binary, "fetch", target, "--obey-robots",
           "--wait", str(wait).strip() or "5",
           "--eval", (extract or "").strip() or "document.title"]
    shot = (screenshot or "").strip()
    if shot:
        shot = os.path.expanduser(shot)
        os.makedirs(os.path.dirname(shot) or ".", exist_ok=True)
        cmd += ["--screenshot", shot]

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.time()
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return dict(where, ok=False, reason="the page did not finish loading in 5 minutes")
    took_ms = int((time.time() - started) * 1000)

    out = (done.stdout or "").strip().split("\n")
    # Obscura печатает служебные строки и трассировки чужого JS вперемешку с
    # ответом; наш результат — последняя непустая строка, не похожая на них.
    noise = ("Page loaded:", "    at ", "Error", "warning")
    useful = [s for s in out if s.strip() and not s.startswith(noise)]
    value = useful[-1].strip() if useful else ""

    if done.returncode != 0 and not value:
        return dict(where, ok=False, took_ms=took_ms,
                    reason="Obscura exited with code %d" % done.returncode,
                    output=((done.stdout or "") + (done.stderr or ""))[-500:])

    # РАЗВОРАЧИВАЕМ ДО ДАННЫХ, А НЕ ДО ОБЁРТКИ.
    # Obscura отдаёт результат внутри служебного объекта: сам ответ лежит в
    # поле «evaluation» строкой, рядом — телеметрия прокрутки и прогрева.
    # Агенту и окну нужны данные, а не наша кухня: снимаем обёртку и, если
    # внутри снова JSON, разбираем и его. Замер 06.09.2026: без этого список
    # кофеен приезжал строкой внутри объекта внутри строки.
    data = value
    for _ in range(3):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (ValueError, TypeError):
                break
        elif isinstance(data, dict) and "evaluation" in data:
            data = data["evaluation"]
        else:
            break
    result = dict(where, ok=True, url=target, took_ms=took_ms, data=data)
    if shot and os.path.isfile(shot):
        result["screenshot"] = shot
        result["screenshot_kb"] = round(os.path.getsize(shot) / 1024, 1)
    return result
