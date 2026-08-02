#!/usr/bin/env python3
"""Гейт договора обязан ОДНОВРЕМЕННО видеть дыру и не выдумывать её.

ЗАЧЕМ ЭТОТ ТЕСТ. 02.08 гейт сказал про Багу: два маршрута импорта не отвечают.
Оба существовали и работали — сервер отдаёт 404 на любое исключение внутри общего
except, и «маршрута нет» стало неотличимо от «сохранённый поиск не найден».
Правка (сравнивать тело ответа с эталонным 404) убрала ложное обвинение — и заодно
ослепила гейт: подставной /api/zzz-does-not-exist он назвал живым, потому что эталон
снимался POST-ом, а на GET сервер отдаёт html-страницу ошибки, а не json.

Слепой гейт опаснее крикливого: крикливый раздражает, слепой молча пропускает релиз.
Поэтому обе стороны закреплены здесь и проверяются без живого продукта — на сервере,
который ведёт себя как настоящий: html-404 на GET, json-404 на POST, и живой маршрут,
который на пустое тело честно отвечает 404 своим текстом.

Запуск: python3 tools/tests/test_contract_gate_sees_holes.py
Коды выхода: 0 — гейт различает оба случая, 1 — нет.
"""
import http.server
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "check_ui_api_contract.py"

LIVE = "/api/live-route"      # существует, но на пустое тело отвечает 404 своим текстом
HOLE = "/api/no-such-route"   # не существует вовсе


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, "<html></html>", "text/html")
        # как настоящий BaseHTTPRequestHandler: неизвестный GET → html-страница ошибки
        self._send(404, "<!DOCTYPE HTML><html><title>Error response</title></html>", "text/html")

    def do_POST(self):
        if self.path == LIVE:
            return self._send(404, json.dumps({"error": "Сохранённый поиск не найден"}))
        self._send(404, json.dumps({"error": "Маршрут не найден"}))


def run_gate(calls, port):
    d = Path(tempfile.mkdtemp())
    (d / "web").mkdir()
    body = "".join(f'fetch("{c}", {{method:"POST"}});\n' for c in calls)
    (d / "web" / "index.html").write_text(f"<html><script>{body}</script></html>", encoding="utf-8")
    r = subprocess.run([sys.executable, str(GATE), str(d), str(port)],
                       capture_output=True, text=True, timeout=120)
    return r.stdout + r.stderr


def main() -> int:
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    failures = []

    out = run_gate([LIVE], port)
    if "✗" in out:
        failures.append("ЛОЖНОЕ ОБВИНЕНИЕ: живой маршрут, ответивший своим 404, "
                        "объявлен мёртвым — так гейт соврал про Багу")

    out = run_gate([HOLE], port)
    if "✗" not in out:
        failures.append("СЛЕПОТА: несуществующий маршрут признан живым — "
                        "гейт пропустил бы пустой экран в релиз")

    out = run_gate([LIVE, HOLE], port)
    if HOLE not in out or LIVE in out.split("✗", 1)[-1].split("\n", 1)[0]:
        failures.append("вместе: гейт не указал ровно на дыру")

    srv.shutdown()
    for f in failures:
        print(f"  ✗ {f}")
    if failures:
        print("\nГЕЙТ ДОГОВОРА НЕИСПРАВЕН.")
        return 1
    print("  ✓ гейт видит дыру и не выдумывает её на живом маршруте")
    return 0


if __name__ == "__main__":
    sys.exit(main())
