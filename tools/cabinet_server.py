#!/usr/bin/env python3
"""Сервер приложения кабинета: раздаёт файлы и хранит работу НА ДИСКЕ.

ЗАЧЕМ. Приложение в окне ОС оказывается «третьей стороной», и браузер закрывает
ему хранилище: drawio умирает с английской ошибкой, excalidraw открывается и молча
теряет рисунки. Обход «откройте отдельным окном» — не решение, а перекладывание
проблемы на человека.

Здесь хранилище своё. Приложение думает, что пишет в localStorage, а на деле работа
ложится файлом в ~/extella-cabinet/данные/<приложение>.json. Из этого следует то,
чего у обычного excalidraw нет вовсе:

  * работа не пропадает при чистке браузера и не зависит от окна, в котором открыта;
  * её видно как файл — можно скопировать, положить в архив, отдать агенту;
  * приложение работает ВНУТРИ окна ОС, а не «в отдельном окне».

Слушает только 127.0.0.1: сервер, доступный по сети, отдаёт папку любому рядом.

    python3 cabinet_server.py --папка ~/extella-cabinet/board --порт 34785 \
                              --имя board --данные ~/extella-cabinet/данные
"""

import argparse
import http.server
import json
import pathlib
import threading

# Латиницей намеренно: кириллица приезжает процентами и не совпадает.
ПУТЬ_ХРАНИЛИЩА = "/_extella_storage"
ПУТЬ_ВЕРСИИ = "/_extella_version"
# Счётчик изменений. Нужен, чтобы открытое окно узнавало: работу поменял КТО-ТО
# ДРУГОЙ (агент), и надо перечитать. Замер 17.08.2026: без него открытая доска
# сохраняла свою старую сцену поверх нарисованного агентом — и рисунок исчезал.
ВЕРСИЯ = [0]
ЗАМОК = threading.Lock()


def сделать_обработчик(папка: pathlib.Path, файл_данных: pathlib.Path):
    class Обработчик(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(папка), **kw)

        def log_message(self, *a):
            pass                      # тишина: журнал сервера тут ничего не даёт

        def _ответ(self, код, тело: bytes, тип="application/json; charset=utf-8"):
            self.send_response(код)
            self.send_header("Content-Type", тип)
            self.send_header("Content-Length", str(len(тело)))
            self.send_header("Cache-Control", "no-store")
            # Разрешения для страницы ОС ставит end_headers — один раз на любой
            # ответ. Слать их и здесь нельзя: два одинаковых заголовка браузер
            # считает ошибкой и режет запрос целиком.
            self.end_headers()
            self.wfile.write(тело)

        def _прочитать_всё(self) -> dict:
            if not файл_данных.exists():
                return {}
            try:
                return json.loads(файл_данных.read_text())
            except (json.JSONDecodeError, OSError):
                # Битый файл не роняем и не затираем: рядом ляжет копия, а
                # приложение начнёт с пустого — это честнее, чем упасть.
                битый = файл_данных.with_suffix(".битый.json")
                try:
                    файл_данных.replace(битый)
                except OSError:
                    pass
                return {}

        def end_headers(self):
            # Страницы приложений не кэшируем. Замер 15.08.2026: браузер держал
            # старую копию index.html, и наша вставка не доезжала до окна — час
            # ушёл на поиск причины в хранилище, которое было ни при чём.
            if self.path.split("?")[0].rstrip("/").endswith((".html", "")) or \
               self.path.split("?")[0].endswith("/"):
                self.send_header("Cache-Control", "no-store, must-revalidate")
            # Окно ОС — страница из интернета (os.extella.ai), а мы живём на этом
            # компьютере. Браузер такие запросы «наружу→внутрь» блокирует, пока
            # местный сервер не разрешит их ЯВНО. Замер 16.08.2026: без этих двух
            # заголовков окно ОС показывало «проба молчит» и пустую доску, хотя
            # приложение было живо и по адресу открывалось.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            super().end_headers()

        def do_OPTIONS(self):
            # Предполётный запрос. Без него http.server отвечает 501, и браузер
            # считает, что местного сервера нет вовсе.
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def guess_type(self, path):
            # http.server отдаёт HTML без указания кодировки, и браузер угадывает.
            # Для страниц с русским текстом угадывание кончается мусором.
            тип = super().guess_type(path)
            if тип in ("text/html", "text/plain", "application/javascript",
                       "text/javascript", "text/css"):
                return тип + "; charset=utf-8"
            return тип

        def do_GET(self):
            if self.path.split("?")[0] == ПУТЬ_ВЕРСИИ:
                # Дешёвый вопрос «изменилось ли»: приложение спрашивает его часто,
                # и гонять всю работу туда-сюда ради этого нельзя.
                return self._ответ(200, json.dumps({"версия": ВЕРСИЯ[0]}).encode())
            if self.path.split("?")[0] == ПУТЬ_ХРАНИЛИЩА:
                with ЗАМОК:
                    д = self._прочитать_всё()
                д["_версия"] = ВЕРСИЯ[0]
                return self._ответ(200, json.dumps(д, ensure_ascii=False).encode())
            return super().do_GET()

        def do_POST(self):
            if self.path.split("?")[0] != ПУТЬ_ХРАНИЛИЩА:
                return self._ответ(404, '{"ошибка":"нет такого адреса"}'.encode())
            длина = int(self.headers.get("Content-Length") or 0)
            if длина > 32 * 1024 * 1024:
                return self._ответ(413, '{"ошибка":"слишком большая запись"}'.encode())
            try:
                тело = json.loads(self.rfile.read(длина).decode() or "{}")
            except json.JSONDecodeError:
                return self._ответ(400, '{"ошибка":"не json"}'.encode())

            with ЗАМОК:
                д = self._прочитать_всё()
                if тело.get("очистить"):
                    д = {}
                elif "ключ" in тело:
                    if тело.get("значение") is None:
                        д.pop(тело["ключ"], None)
                    else:
                        д[str(тело["ключ"])] = str(тело["значение"])
                файл_данных.parent.mkdir(parents=True, exist_ok=True)
                # Пишем через временный файл: обрыв на записи не должен оставить
                # человека с обрезанным файлом вместо работы.
                врем = файл_данных.with_suffix(".пишется")
                врем.write_text(json.dumps(д, ensure_ascii=False))
                врем.replace(файл_данных)
                ВЕРСИЯ[0] += 1
            return self._ответ(200, json.dumps(
                {"сохранено": True, "версия": ВЕРСИЯ[0]}).encode())

    return Обработчик


def main() -> int:
    р = argparse.ArgumentParser()
    р.add_argument("--папка", required=True)
    р.add_argument("--порт", required=True, type=int)
    р.add_argument("--имя", required=True)
    р.add_argument("--данные", required=True)
    а = р.parse_args()

    файл = pathlib.Path(а.данные).expanduser() / f"{а.имя}.json"
    сервер = http.server.ThreadingHTTPServer(
        ("127.0.0.1", а.порт),
        сделать_обработчик(pathlib.Path(а.папка).expanduser(), файл))
    сервер.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
