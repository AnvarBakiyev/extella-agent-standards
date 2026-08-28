$extens("include.py")
include("import os", [])
include("import subprocess", [])
include("import tempfile", [])

def doc_to_pdf(source: str = "", out_dir: str = "", **extra) -> dict:
    """Convert an office document (docx/xlsx/pptx/odt/txt/html) to PDF on THIS
    device using the LibreOffice command line — no Docker, no server. Params:
    source — path to the input file; out_dir — where to put the PDF (default:
    next to the source). Returns the PDF path, size and the machine it ran on.

    ЗАЧЕМ. Проба гипотезы 28.08.2026: Docker-контейнер Stirling-PDF держали
    ради конвертации, а конвертирует внутри него тот же LibreOffice. CLI
    `soffice --headless --convert-to pdf` делает это одной командой за
    секунды. Эксперт = «руки» приложения; лицо рисует окно ОС.

    Код латиницей: кириллица в идентификаторах валит сборку контейнера на
    Windows (замер 28.08.2026, «invalid decimal literal»).
    """
    import os, subprocess, tempfile, time, platform, socket

    where = {"system": platform.system(), "machine": socket.gethostname()[:40]}

    src = os.path.expanduser((source or "").strip())
    if not src:
        return dict(where, ok=False, reason="no source file given: pass params.source")
    if not os.path.isfile(src):
        return dict(where, ok=False, reason="file not found: %s" % src[:200])

    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",   # macOS app
        "/opt/homebrew/bin/soffice", "/usr/local/bin/soffice",    # brew
        "/usr/bin/soffice", "/usr/bin/libreoffice",               # linux
        r"C:\Program Files\LibreOffice\program\soffice.com",      # windows CLI
        r"C:\Program Files\LibreOffice\program\soffice.exe",
    ]
    soffice = next((p for p in candidates if os.path.isfile(p)), "")
    if not soffice:
        return dict(where, ok=False,
                    reason="LibreOffice is not installed on this computer. "
                           "Installing it is the installer expert's job, not this one's")

    dest = os.path.expanduser((out_dir or "").strip()) or os.path.dirname(src)
    os.makedirs(dest, exist_ok=True)

    # Отдельный одноразовый профиль: без него headless-запуск спотыкается о
    # замок профиля, когда LibreOffice открыт у человека окном.
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    profile_uri = "file:///" + profile.replace("\\", "/").lstrip("/")

    started = time.time()
    try:
        done = subprocess.run(
            [soffice, "--headless", "--norestore",
             "-env:UserInstallation=" + profile_uri,
             "--convert-to", "pdf", "--outdir", dest, src],
            capture_output=True, text=True, timeout=300,
            encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return dict(where, ok=False, reason="conversion did not finish in 5 minutes")
    took_ms = int((time.time() - started) * 1000)

    base = os.path.splitext(os.path.basename(src))[0]
    pdf = os.path.join(dest, base + ".pdf")
    if done.returncode != 0 or not os.path.isfile(pdf):
        return dict(where, ok=False, took_ms=took_ms,
                    reason="LibreOffice exited with code %d" % done.returncode,
                    output=((done.stdout or "") + (done.stderr or ""))[-400:])
    # Доказательство файлом, а не кодом возврата: PDF начинается с %PDF.
    head = open(pdf, "rb").read(5)
    if head != b"%PDF-":
        return dict(where, ok=False, took_ms=took_ms,
                    reason="the output file is not a PDF (starts with %r)" % head)
    return dict(where, ok=True, pdf=pdf,
                size_kb=round(os.path.getsize(pdf) / 1024, 1), took_ms=took_ms)
