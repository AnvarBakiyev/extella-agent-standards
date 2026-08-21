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
# Банка кук прокси-режима: песочница окна ОС сетевые куки режет нацело, поэтому
# сессию контейнера держит прокси в памяти процесса (шестая дверь, 21.08.2026).
КУКИ = {}
ЗАМОК = threading.Lock()

# ── Действия по кнопке ────────────────────────────────────────────────────────
# Пульт в окне ОС нажимает кнопку — здесь выполняется НАЗВАННОЕ действие.
# Список закрытый: произвольных команд с этого адреса запускать нельзя, иначе
# любая открытая в браузере страница получит право хозяйничать на компьютере.
ПУТЬ_ДЕЙСТВИЯ = "/_extella_action"
ИНСТРУМЕНТЫ = pathlib.Path.home() / "Documents/Extella/extella-agent-standards/tools"
ДЕЙСТВИЯ = {
    "схема":       ("board_to_app.py", ["--нарисовать-схему", "{название}"]),
    "приложение":  ("board_to_app.py", ["--собрать", "--slug", "{slug}", "--имя", "{название}"]),
    "отток":       ("astra_churn_to_board.py", ["--топ", "8"]),
    "правила":     ("board_rules_to_astra.py", []),
    "правила_в_платформу": ("board_rules_to_astra.py", ["--в-правила", "--сухой"]),
    "пример_правила": ("board_rules_to_astra.py", ["--пример"]),
    "витрина":     ("check_listing_meta.py", ["{издание}"]),
    "выложить":    ("deploy_page_product.py", ["{издание}"]),
    # Главный вход. Не кнопка на каждое приложение, а одна строка: что умеет
    # система, решает реестр источников, а не длина этого списка. Вместе с
    # фразой едет имя окна, из которого она сказана: «возьми из астры» без
    # названного получателя кладёт данные в ЭТО окно (контекст «здесь»).
    "скажи":       ("скажи.py", ["{фраза}", "--учись", "--окно", "{окно}"]),
}
# Publish среди действий НЕТ намеренно: публичность включает владелец в магазине.

# Кому разрешено нажимать. Заголовки «всем можно» нужны, чтобы окно ОС вообще
# достучалось до этого компьютера, — но для ДЕЙСТВИЙ это опасно: любая открытая
# вкладка получила бы право их запускать. Поэтому здесь список поимённый.
СВОИ_АДРЕСА = ("https://os.extella.ai", "http://localhost", "http://127.0.0.1")

# Действия, которые выходят за пределы этого компьютера: они трогают магазин и
# правила агента. Для них мало «свой адрес» — нужно слово человека, набранное
# в пульте. Рисование на доске в этот список не входит: испортить им нечего,
# а лишнее подтверждение на каждый чих люди перестают читать.
ОПАСНЫЕ = {"выложить", "правила_в_платформу"}
СЛОВО = "подтверждаю"


def _свой(происхождение: str) -> bool:
    if not происхождение:
        return True                       # запрос не из браузера (curl, эксперт)
    # «null» — это песочница окна ОС: она намеренно лишает страницу адреса, и
    # поимённый список её отвергал. Замер 18.08.2026: пульт в окне ОС получал
    # «не достучался». Пускаем — но за платформенные действия отвечает уже не
    # адрес, а подтверждение человека (см. ОПАСНЫЕ).
    if происхождение.strip().lower() == "null":
        return True
    return any(происхождение.startswith(а) for а in СВОИ_АДРЕСА)


def выполнить(имя: str, параметры: dict) -> dict:
    import re as _re
    import subprocess as _sp
    if имя not in ДЕЙСТВИЯ:
        return {"ошибка": f"неизвестное действие «{имя}»"}
    if имя in ОПАСНЫЕ and str(параметры.get("подтверждение", "")).strip().lower() != СЛОВО:
        return {"ошибка": f"это действие выходит за пределы компьютера — "
                          f"наберите в пульте слово «{СЛОВО}»"}
    файл, образец = ДЕЙСТВИЯ[имя]
    название = str(параметры.get("название") or "Панель")[:60]
    # Фраза человека едет отдельным аргументом списка, а не в оболочку: строка
    # от человека внутри shell-команды — это чужой код на его же машине.
    фраза = " ".join(str(параметры.get("фраза") or "").split())[:300]
    if имя == "скажи" and not фраза:
        return {"ошибка": "скажите словами, что взять и куда положить — "
                          "например «возьми из астры первые 9 и нарисуй на доске»"}
    slug = str(параметры.get("slug") or "")
    if "{slug}" in " ".join(образец) and not _re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        return {"ошибка": "имя латиницей: строчные буквы, цифры и дефис"}
    # Имя окна, из которого сказана фраза, — контекст «здесь». Пустое имя
    # допустимо: фраза из терминала или чата контекста окна не имеет.
    окно = " ".join(str(параметры.get("окно") or "").split())[:60]
    издание = str(ИНСТРУМЕНТЫ.parent / "editions" / slug)
    аргументы = [а.replace("{название}", название).replace("{slug}", slug)
                  .replace("{издание}", издание).replace("{фраза}", фраза)
                  .replace("{окно}", окно)
                 for а in образец]
    try:
        # ТЕМ ЖЕ питоном, что крутит сервер. Звать «python3» по имени нельзя:
        # в фоновой службе это оказался старый 3.9 из Xcode, и инструменты
        # падали на современном синтаксисе. Замер 17.08.2026, кнопка «отток».
        итог = _sp.run([__import__("sys").executable, str(ИНСТРУМЕНТЫ / файл), *аргументы],
                       capture_output=True, text=True, timeout=180)
    except _sp.TimeoutExpired:
        return {"ошибка": "действие не уложилось в три минуты"}
    return {"код": итог.returncode,
            "вывод": ((итог.stdout or "") + (итог.stderr or "")).strip()[-4000:]}


def _вставить_шим(данные: bytes, шим: str) -> bytes:
    """Вшить подмену хранилища в чужой HTML на лету.

    ЗАЧЕМ. Docker-приложения сами отдают свои страницы — в файлы на диске шим не
    вставить, а без него страница в песочнице окна ОС умирает о запертое
    хранилище (белое окно Сторожа, замер 20.08.2026; «отдельное окно» Электрона
    наследует ту же песочницу и не спасает). Прокси решает это по-взрослому:
    страница едет через нас и получает шим, как будто всегда с ним жила.
    """
    текст = данные.decode("utf-8", errors="replace")
    for метка in ("<head>", "<HEAD>"):
        if метка in текст:
            return текст.replace(метка, метка + шим, 1).encode()
    н = текст.find("<head")
    if н >= 0:
        к = текст.find(">", н)
        if к > 0:
            return (текст[:к + 1] + шим + текст[к + 1:]).encode()
    return (шим + текст).encode()


def сделать_обработчик(папка: pathlib.Path, файл_данных: pathlib.Path,
                       прокси_на: int | None = None, шим: str = "",
                       автовход: str = ""):
    class Обработчик(http.server.SimpleHTTPRequestHandler):
        def _автовход(self) -> bool:
            """Войти в контейнер за человека — машинным секретом из файла.

            Решение владельца 21.08.2026: в локальном контуре паролей нет —
            вход уже охраняет Extella, а порт наружу не торчит. Файл автовхода
            (права 600, рядом с .env) держит {"путь", "тело"}; куки сессии
            ложатся в банку прокси. Секрет машинный, человеку не показывается."""
            import http.client
            try:
                конф = json.loads(pathlib.Path(автовход).expanduser().read_text())
                с = http.client.HTTPConnection("127.0.0.1", прокси_на, timeout=30)
                с.request("POST", конф.get("путь") or "/api/login",
                          body=json.dumps(конф.get("тело") or {}).encode(),
                          headers={"Content-Type": "application/json"})
                о = с.getresponse()
                о.read()
                for к, з in о.getheaders():
                    if к.lower() == "set-cookie":
                        кусок = з.split(";", 1)[0]
                        if "=" in кусок:
                            и, зн = кусок.split("=", 1)
                            КУКИ[и.strip()] = зн.strip()
                return о.status < 400 and bool(КУКИ)
            except (OSError, json.JSONDecodeError, ValueError):
                return False

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

        # ── прокси на контейнер ────────────────────────────────────────────
        def _служебный(self) -> bool:
            путь = self.path.split("?")[0]
            return путь in (ПУТЬ_ХРАНИЛИЩА, ПУТЬ_ВЕРСИИ, ПУТЬ_ДЕЙСТВИЯ)

        def _проксировать(self):
            import http.client
            длина = int(self.headers.get("Content-Length") or 0)
            тело = self.rfile.read(длина) if длина else None
            заг = {к: з for к, з in self.headers.items()
                   if к.lower() not in ("host", "accept-encoding", "connection")}
            # Сжатие просим выключить: вшивать шим в gzip-поток — себе дороже.
            заг["Accept-Encoding"] = "identity"
            заг["Host"] = f"127.0.0.1:{прокси_на}"
            # ШЕСТАЯ ДВЕРЬ, грань «куки»: песочница окна ОС режет сетевые куки
            # нацело — Set-Cookie не сохраняется, сессия логина не живёт.
            # Куки держит САМ ПРОКСИ: банка в памяти процесса, на каждый запрос
            # доклеивается. Контур одного пользователя на 127.0.0.1 — честно.
            исходный_cookie = заг.get("Cookie", "")
            for попытка in (1, 2):
                if КУКИ:
                    банка = "; ".join(f"{и}={з}" for и, з in КУКИ.items())
                    заг["Cookie"] = f"{исходный_cookie}; {банка}".strip("; ")
                с = http.client.HTTPConnection("127.0.0.1", прокси_на, timeout=90)
                try:
                    с.request(self.command, self.path, body=тело, headers=заг)
                    о = с.getresponse()
                    данные = о.read()
                except OSError as е:
                    return self._ответ(502, json.dumps(
                        {"ошибка": f"приложение в контейнере молчит: {е}"},
                        ensure_ascii=False).encode())
                # Сессия умерла или её не было: прокси входит сам и повторяет
                # запрос один раз (решение владельца о беспарольном контуре).
                if (о.status == 401 and автовход and попытка == 1
                        and self._автовход()):
                    continue
                break
            if шим and "text/html" in (о.getheader("Content-Type") or ""):
                данные = _вставить_шим(данные, шим)
            self.send_response(о.status)
            for к, з in о.getheaders():
                # Хоп-заголовки и CSP не переносим: длину мы поменяли шимом, а
                # CSP контейнера зарезал бы наш встроенный скрипт. Контур свой,
                # 127.0.0.1 — ослабление честное и локальное.
                # X-Frame-Options контейнера — убийца окна ОС: браузер скачивает
                # документ, но ОТКАЗЫВАЕТСЯ рисовать его во вложенном окне —
                # белое полотно без скриптов и без единой ошибки. Замер
                # 20.08.2026, Сторож: запросы в журнале есть, рендера нет.
                # ШЕСТАЯ ДВЕРЬ (замер 21.08.2026, tududi + helmet): семейство
                # Cross-Origin-* — прежде всего Cross-Origin-Resource-Policy:
                # same-origin — душит В ПЕСОЧНИЦЕ каждый скрипт и fetch: у окна
                # происхождение null, для него всё «кросс». В обычной вкладке
                # приложение живёт, в окне ОС — белое. Снимаем семейство и куки
                # (их держит банка прокси, наружу не отдаём).
                if к.lower() in ("content-length", "transfer-encoding", "connection",
                                 "content-security-policy", "content-encoding",
                                 "x-frame-options",
                                 "access-control-allow-origin",
                                 "cross-origin-resource-policy",
                                 "cross-origin-opener-policy",
                                 "cross-origin-embedder-policy",
                                 "origin-agent-cluster",
                                 "set-cookie"):
                    if к.lower() == "set-cookie":
                        кусок = з.split(";", 1)[0]
                        if "=" in кусок:
                            и, зн = кусок.split("=", 1)
                            КУКИ[и.strip()] = зн.strip()
                    continue
                self.send_header(к, з)
            # Свой допуск (ACAO) НЕ шлём здесь: его добавляет end_headers ко
            # всем ответам сервера — второй экземпляр даёт «multiple values»,
            # и браузер отвергает CORS целиком. Замер 21.08.2026, tududi.
            self.send_header("Content-Length", str(len(данные)))
            self.end_headers()
            self.wfile.write(данные)

        def do_HEAD(self):
            if прокси_на and not self._служебный():
                return self._проксировать()
            super().do_HEAD()

        def do_PUT(self):
            if прокси_на and not self._служебный():
                return self._проксировать()
            self._ответ(405, b'{}')

        def do_DELETE(self):
            if прокси_на and not self._служебный():
                return self._проксировать()
            self._ответ(405, b'{}')

        def do_PATCH(self):
            if прокси_на and not self._служебный():
                return self._проксировать()
            self._ответ(405, b'{}')

        def do_OPTIONS(self):
            # Предполёт проксируемых путей отвечаем САМИ: helmet контейнера о
            # происхождении null может и не договориться, а нам нужен только
            # зелёный свет для песочницы (шестая дверь, 21.08.2026, tududi).
            if прокси_на and not self._служебный():
                # ACAO не шлём — его добавит end_headers, дубль ломает CORS.
                self.send_response(204)
                self.send_header("Access-Control-Allow-Methods",
                                 "GET, POST, PUT, DELETE, PATCH, OPTIONS")
                self.send_header("Access-Control-Allow-Headers",
                                 self.headers.get("Access-Control-Request-Headers")
                                 or "Content-Type, Authorization")
                self.send_header("Access-Control-Max-Age", "600")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            # Действия — только своим: чужому предполёт не отдаём, и запрос
            # до нас просто не доедет.
            if self.path.split("?")[0] == ПУТЬ_ДЕЙСТВИЯ and \
               not _свой(self.headers.get("Origin", "")):
                return self._ответ(403, '{"ошибка":"чужой адрес"}'.encode())
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
            if прокси_на and not self._служебный():
                return self._проксировать()
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
            if прокси_на and not self._служебный():
                return self._проксировать()
            if self.path.split("?")[0] == ПУТЬ_ДЕЙСТВИЯ:
                if not _свой(self.headers.get("Origin", "")):
                    return self._ответ(403, '{"ошибка":"чужой адрес"}'.encode())
                длина = int(self.headers.get("Content-Length") or 0)
                try:
                    тело = json.loads(self.rfile.read(длина).decode() or "{}")
                except json.JSONDecodeError:
                    return self._ответ(400, '{"ошибка":"не json"}'.encode())
                итог = выполнить(str(тело.get("действие") or ""), тело)
                return self._ответ(200, json.dumps(итог, ensure_ascii=False).encode())
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
    р.add_argument("--прокси-на", dest="прокси_на", type=int, default=None,
                   help="проксировать всё (кроме служебных путей) на этот локальный порт")
    р.add_argument("--шим", default="", help="файл шима для вставки в проксируемый HTML")
    р.add_argument("--автовход", default="",
                   help="json-файл {путь, тело} — прокси входит в контейнер сам "
                        "(беспарольный локальный контур по решению владельца)")
    а = р.parse_args()

    шим = pathlib.Path(а.шим).expanduser().read_text() if а.шим else ""
    файл = pathlib.Path(а.данные).expanduser() / f"{а.имя}.json"
    сервер = http.server.ThreadingHTTPServer(
        ("127.0.0.1", а.порт),
        сделать_обработчик(pathlib.Path(а.папка).expanduser(), файл, а.прокси_на,
                           шим, а.автовход))
    сервер.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
