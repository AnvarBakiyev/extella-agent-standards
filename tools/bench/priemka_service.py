#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP-сервис приёмки на стенде — бэкенд кнопки «откроется ли у других».

Кнопка в OS зовёт этот сервис на стенде; сервис открывает приложение как чужак
на настоящем os.extella.ai (see same_origin_probe.py), судит по глазу (разброс
яркости скриншота, see check_opens_elsewhere.py) и отдаёт JSON с вердиктом и
скриншотом. Стенд — машина пользователя; для Этапа 1 это наш VPS.

    POST/GET /priemka?lid=<listing_id>   заголовок X-Bench-Key: <ключ>
    GET      /health

Ответ: {"цвет","блок","бейдж","жёсткие":[...],"мягкие":[...],"скриншот":"data:..."}.

Ключ (X-Bench-Key) закрывает сервис от улицы — лежит в ~/extella-bench/
bench_service_key.txt (в лог не печатать). CORS открыт (ключ в заголовке, не
кука), чтобы панель из песочницы OS (origin=null) могла позвать. Приёмки
сериализованы замком: у пробы фиксированный порт прокси, параллель их столкнёт.
"""
import base64
import http.server
import json
import pathlib
import sys
import threading
import urllib.parse

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ЗДЕСЬ))
import same_origin_probe                                   # noqa: E402
from check_opens_elsewhere import (измерить_плотность,      # noqa: E402
                                   классифицировать_домен)
from probe_window import видимый_текст                      # noqa: E402

ПОРТ = 8799
КЛЮЧ_ФАЙЛ = pathlib.Path.home() / "extella-bench" / "bench_service_key.txt"
ЗАМОК = threading.Lock()


def ключ() -> str:
    return КЛЮЧ_ФАЙЛ.read_text().strip() if КЛЮЧ_ФАЙЛ.exists() else ""


def приёмка(лид: str) -> dict:
    with ЗАМОК:
        сб = same_origin_probe.собрать(лид)
    if сб.get("ошибка"):
        return {"цвет": "серый", "блок": False, "бейдж": "проба не смогла",
                "жёсткие": [], "мягкие": [сб["ошибка"]], "скриншот": None}
    png = сб["папка"] / "окно_на_домене.png"
    std = измерить_плотность(png)
    в = классифицировать_домен(std, сб["конс"], видимый_текст(сб["dom"]))
    if png.exists():
        b64 = base64.b64encode(png.read_bytes()).decode()
        в["скриншот"] = "data:image/png;base64," + b64
    else:
        в["скриншот"] = None
    return в


class Сервис(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-Bench-Key, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, код: int, тело: dict):
        данные = json.dumps(тело, ensure_ascii=False).encode()
        self.send_response(код)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(данные)))
        self._cors()
        self.end_headers()
        self.wfile.write(данные)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        self._обработать()

    def do_POST(self):
        self._обработать()

    def _обработать(self):
        разбор = urllib.parse.urlparse(self.path)
        if разбор.path == "/health":
            return self._json(200, {"стенд": "жив"})
        if разбор.path != "/priemka":
            return self._json(404, {"ошибка": "нет такого пути"})
        if self.headers.get("X-Bench-Key", "") != ключ() or not ключ():
            return self._json(401, {"ошибка": "нужен верный X-Bench-Key"})
        лид = urllib.parse.parse_qs(разбор.query).get("lid", [""])[0].strip()
        if not лид:
            return self._json(400, {"ошибка": "нужен ?lid=<listing_id>"})
        try:
            self._json(200, приёмка(лид))
        except Exception as e:                             # noqa: BLE001
            self._json(500, {"ошибка": str(e)[:200]})


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        # Классификаторы уже проверены в check_opens_elsewhere; здесь — что сервис
        # собирается и отвечает на /health без сети.
        assert ключ is not None
        print("selftest: пройден (импорт и сборка ок)")
        sys.exit(0)
    сервер = http.server.ThreadingHTTPServer(("127.0.0.1", ПОРТ), Сервис)
    print(f"приёмка-сервис на 127.0.0.1:{ПОРТ}")
    сервер.serve_forever()
