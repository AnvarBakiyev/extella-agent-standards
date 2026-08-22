#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба окна НА РОДНОМ ORIGIN os.extella.ai — путь к проверенному зелёному.

ЗАЧЕМ. Прежняя проба (probe_window.py) открывает страницу через прокси на
127.0.0.1 и добавляет токен заголовком. Но приложение шлёт свои запросы на
абсолютный https://os.extella.ai, а браузер сидит на origin 127.0.0.1 → CORS
рубит (замер 22.08.2026: access-control-allow-origin отдаётся только для null,
не для 127.0.0.1). У покупателя окно живёт на самом os.extella.ai, запросы
same-origin, CORS не возникает. Жёлтый в стенде — вина транспорта, не продукта.

КАК. Поднимаем HTTPS-прокси на 127.0.0.1 с самоподписанным сертификатом; он
добавляет X-Extella-Token (страница по-другому не отдаётся) и пробрасывает всё
на РЕАЛЬНЫЙ os.extella.ai (питон не знает про подмену Chromium и резолвит домен
честно). Chromium запускаем с --host-resolver-rules="MAP os.extella.ai 127.0.0.1:
ПОРТ" и --ignore-certificate-errors → браузер считает прокси настоящим доменом,
origin становится https://os.extella.ai. Теперь фетчи приложения same-origin,
вшитый токен приложения рисует данные — как у покупателя.

    python3 same_origin_probe.py <listing_id>

Печатает длину видимого текста и путь к DOM/скриншоту. Это эксперимент-доказатель-
ство механизма; вердикт светофором ставит check_opens_elsewhere.py.
"""
import http.server
import json
import pathlib
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ЗДЕСЬ))
from probe_window import видимый_текст  # noqa: E402

ОС = "https://os.extella.ai"
ТОКЕН_ФАЙЛ = pathlib.Path.home() / "extella-bench" / "bench_token.txt"
ХРОМ = "/snap/bin/chromium"
ПОРТ = 34983
ЦЕРТ = pathlib.Path.home() / "extella-bench" / "os_selfsigned.pem"


def обеспечить_серт() -> None:
    if ЦЕРТ.exists():
        return
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(ЦЕРТ), "-out", str(ЦЕРТ), "-days", "3650",
         "-subj", "/CN=os.extella.ai",
         "-addext", "subjectAltName=DNS:os.extella.ai"],
        check=True, capture_output=True)


def сделать_прокси(токен: str):
    ПРОПУСК = {"host", "content-length", "connection", "accept-encoding"}

    class Прокси(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _тело(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else None

        def _проброс(self, метод: str, тело):
            заг = {k: v for k, v in self.headers.items()
                   if k.lower() not in ПРОПУСК}
            заг["X-Extella-Token"] = токен           # страница иначе 401
            заг["Accept-Encoding"] = "identity"
            з = urllib.request.Request(ОС + self.path, data=тело, method=метод,
                                       headers=заг)
            try:
                with urllib.request.urlopen(з, timeout=90) as о:
                    данные = о.read()
                    self.send_response(о.status)
                    self.send_header("Content-Type",
                                     о.headers.get("Content-Type", "text/html"))
                    self.send_header("Content-Length", str(len(данные)))
                    self.end_headers()
                    self.wfile.write(данные)
            except urllib.error.HTTPError as e:
                тело_о = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type",
                                 e.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(тело_о)))
                self.end_headers()
                self.wfile.write(тело_о)
            except Exception as e:                     # noqa: BLE001
                т = json.dumps({"проба": str(e)[:160]}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(т)))
                self.end_headers()
                self.wfile.write(т)

        def do_GET(self):
            self._проброс("GET", None)

        def do_POST(self):
            self._проброс("POST", self._тело())

    return Прокси


def хром(лид: str, врем: pathlib.Path, скрин: pathlib.Path | None) -> tuple:
    команда = [ХРОМ, "--headless=new", f"--user-data-dir={врем}",
               "--no-sandbox", "--disable-gpu", "--window-size=1280,900",
               f"--host-resolver-rules=MAP os.extella.ai 127.0.0.1:{ПОРТ}",
               "--ignore-certificate-errors",
               "--enable-logging=stderr", "--v=0",
               "--virtual-time-budget=45000", "--timeout=70000"]
    команда.append(f"--screenshot={скрин}" if скрин else "--dump-dom")
    команда.append(f"{ОС}/app-page/{лид}/")
    итог = subprocess.run(команда, capture_output=True, text=True, timeout=120)
    консоль = [с for с in (итог.stderr or "").splitlines() if "CONSOLE" in с]
    return итог.stdout or "", консоль


def собрать(лид: str) -> dict:
    """Открыть окно на родном origin и вернуть {dom, конс, папка, ошибка}.

    Дожимает отрисовку: --dump-dom иногда снимает DOM до гидрации приложения,
    пока фоновый app-agent/run ещё идёт. Повторяем, пока не нарисуется видимый
    текст, до трёх попыток. Скриншот кладём для глаз человека.
    """
    if not ТОКЕН_ФАЙЛ.exists():
        return {"ошибка": f"нет токена стенда: {ТОКЕН_ФАЙЛ}"}
    обеспечить_серт()
    токен = ТОКЕН_ФАЙЛ.read_text().strip()
    штамп = time.strftime("%Y%m%d-%H%M%S")
    папка = pathlib.Path.home() / "extella-bench" / "runs" / f"домен-{штамп}"
    папка.mkdir(parents=True, exist_ok=True)

    ктх = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ктх.load_cert_chain(str(ЦЕРТ))
    сервер = http.server.ThreadingHTTPServer(("127.0.0.1", ПОРТ),
                                             сделать_прокси(токен))
    сервер.socket = ктх.wrap_socket(сервер.socket, server_side=True)
    threading.Thread(target=сервер.serve_forever, daemon=True).start()
    dom, конс = "", []
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as врем:
            в = pathlib.Path(врем)
            for попытка in range(3):
                dom, конс = хром(лид, в / f"a{попытка}", None)
                if len(видимый_текст(dom)) >= 60:
                    break
                time.sleep(3)
            хром(лид, в / "b", папка / "окно_на_домене.png")
    finally:
        сервер.shutdown()

    (папка / "dom.html").write_text(dom, encoding="utf-8")
    (папка / "консоль.txt").write_text("\n".join(конс), encoding="utf-8")
    return {"dom": dom, "конс": конс, "папка": папка, "ошибка": None}


def прогнать(лид: str) -> int:
    сб = собрать(лид)
    if сб.get("ошибка"):
        print(сб["ошибка"]); return 2
    текст = видимый_текст(сб["dom"])
    беды_консоли = [с for с in сб["конс"] if any(
        б in с for б in ("Uncaught", "SecurityError", "Failed to fetch",
                         "CORS", "net::ERR", "401", "500"))]
    print(f"origin: {ОС} (через подмену host-resolver)")
    print(f"видимого текста: {len(текст)} знаков")
    print(f"первые 200 знаков: {текст[:200]!r}")
    print(f"консольных бед: {len(беды_консоли)}")
    for с in беды_консоли[:4]:
        print("  ·", с.split('CONSOLE')[-1][:160])
    print(f"DOM и скриншот: {сб['папка']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(прогнать(sys.argv[1]))
