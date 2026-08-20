#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проба окна: открывает купленную страницу как покупатель и смотрит, что видно.

ЗАЧЕМ. Установка и самопроверка не ловят класс «страница отдаётся, но человек
видит пустоту»: замер 15–16.08.2026 — три окна из трёх выглядели сломанными при
работающих звеньях. Пробе нужно то, что видит ГЛАЗ: рисуется ли текст, молчит ли
консоль, не светится ли подстановка.

КАК УСТРОЕНА. Страница продукта отвечает только по заголовку X-Extella-Token —
навигацией браузер его не пошлёт. Поэтому проба поднимает прокси на 127.0.0.1,
который добавляет заголовок, и открывает страницу двумя способами:

  А. напрямую — читается DOM: есть ли текст, нет ли «{{» в видимом;
  Б. в рамке с ФЛАГАМИ ПЕСОЧНИЦЫ ОС (sandbox без allow-same-origin) — читается
     консоль: падения, SecurityError, наши классы отказов. Происхождение внутри
     рамки пустое, ровно как у покупателя.

Чего проба НЕ умеет: оценить понятность экрана и увидеть содержимое рамки Б в
DOM (браузер не отдаёт его снаружи). Скриншоты обеих проб складываются рядом —
для глаз человека.

    python3 probe_window.py <listing_id>
    python3 probe_window.py --selftest

Коды выхода: 0 — окно живое, 1 — есть беды, 2 — проба не смогла.
"""
import http.server
import json
import pathlib
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

ОС = "https://os.extella.ai"
ТОКЕН_ФАЙЛ = pathlib.Path.home() / "extella-bench" / "bench_token.txt"
ХРОМ = "/snap/bin/chromium"
ПОРТ = 34981
# Ровно те флаги, что ставит рабочий стол ОС (замер 19.08.2026, desktop.js).
ФЛАГИ_ПЕСОЧНИЦЫ = "allow-scripts allow-forms allow-popups allow-modals allow-downloads"

# Классы консольных бед. Порядок = серьёзность.
БЕДЫ_КОНСОЛИ = ("Uncaught", "SecurityError", "is not defined", "Failed to fetch",
                "net::ERR", "404 (", "500 (")


def сделать_прокси(токен: str, лид: str):
    class Прокси(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _отдать(self, код: int, тело: bytes, тип: str):
            self.send_response(код)
            self.send_header("Content-Type", тип)
            self.send_header("Content-Length", str(len(тело)))
            self.end_headers()
            self.wfile.write(тело)

        def do_GET(self):
            путь = urllib.parse.unquote(self.path)
            if путь == "/probe-frame":
                тело = (f'<!doctype html><meta charset="utf-8"><title>проба</title>'
                        f'<iframe sandbox="{ФЛАГИ_ПЕСОЧНИЦЫ}" '
                        f'src="/app-page/{лид}/" '
                        f'style="width:1200px;height:750px;border:0"></iframe>'
                        ).encode()
                return self._отдать(200, тело, "text/html; charset=utf-8")
            self._пробросить("GET", None)

        def do_POST(self):
            длина = int(self.headers.get("Content-Length") or 0)
            self._пробросить("POST", self.rfile.read(длина) if длина else None)

        def _пробросить(self, метод: str, тело):
            з = urllib.request.Request(ОС + self.path, data=тело, method=метод,
                                       headers={"X-Extella-Token": токен})
            if self.headers.get("Content-Type"):
                з.add_header("Content-Type", self.headers["Content-Type"])
            try:
                with urllib.request.urlopen(з, timeout=60) as о:
                    self._отдать(о.status, о.read(),
                                 о.headers.get("Content-Type", "text/html"))
            except urllib.error.HTTPError as e:
                self._отдать(e.code, e.read(), "application/json")
            except Exception as e:                     # noqa: BLE001
                self._отдать(502, json.dumps({"проба": str(e)[:120]}).encode(),
                             "application/json")

    return Прокси


def хром(адрес: str, врем: pathlib.Path, скрин: pathlib.Path | None) -> tuple:
    """DOM и консоль после исполнения скриптов страницы."""
    команда = [ХРОМ, "--headless=new", f"--user-data-dir={врем}",
               "--no-sandbox", "--disable-gpu", "--window-size=1280,900",
               "--enable-logging=stderr", "--v=0",
               "--virtual-time-budget=20000", "--timeout=40000"]
    if скрин:
        команда.append(f"--screenshot={скрин}")
    else:
        команда.append("--dump-dom")
    команда.append(адрес)
    итог = subprocess.run(команда, capture_output=True, text=True, timeout=90)
    консоль = [с for с in (итог.stderr or "").splitlines() if "CONSOLE" in с]
    return итог.stdout or "", консоль


def видимый_текст(dom: str) -> str:
    dom = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", dom, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dom)).strip()


def разобрать(dom: str, консоль_а: list, консоль_б: list) -> list:
    """Верддикт по собранному. Отдельно от сбора — чтобы селфтест жил без сети."""
    беды = []
    текст = видимый_текст(dom)
    отказ_словами = any(с in текст for с in ("Повторить", "Retry", "Связь",
                                             "недоступ", "Ошибка", "ошибка"))
    if len(текст) < 60 and not отказ_словами:
        беды.append(f"страница почти пуста: видимого текста {len(текст)} знаков — "
                    f"человек увидит белый экран")
    elif len(текст) < 60 and отказ_словами:
        print(f"  ~ окно живо и показывает отказ словами: «{текст[:80]}» — связь "
              f"с платформой в пробе ограничена, у покупателя её даёт домен ОС")
    if "{{" in текст:
        кусок = текст[текст.find("{{"):][:60]
        беды.append(f"подстановка светится в видимом тексте: «{кусок}» — "
                    f"покупатель прочитает метку вместо значения")
    for имя, консоль in (("напрямую", консоль_а), ("в песочнице ОС", консоль_б)):
        серьёзные = [с for с in консоль if any(б in с for б in БЕДЫ_КОНСОЛИ)]
        for с in серьёзные[:3]:
            суть = с.split("CONSOLE")[-1][:160]
            беды.append(f"консоль ({имя}): {суть}")
    return беды


def прогнать(лид: str) -> int:
    if not ТОКЕН_ФАЙЛ.exists():
        print("нет токена стенда:", ТОКЕН_ФАЙЛ)
        return 2
    токен = ТОКЕН_ФАЙЛ.read_text().strip()
    штамп = time.strftime("%Y%m%d-%H%M%S")
    папка = pathlib.Path.home() / "extella-bench" / "runs" / f"окно-{штамп}"
    папка.mkdir(parents=True, exist_ok=True)

    сервер = http.server.ThreadingHTTPServer(("127.0.0.1", ПОРТ),
                                             сделать_прокси(токен, лид))
    threading.Thread(target=сервер.serve_forever, daemon=True).start()
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as врем:
            в = pathlib.Path(врем)
            dom, конс_а = хром(f"http://127.0.0.1:{ПОРТ}/app-page/{лид}/",
                               в / "а", None)
            if len(dom) < 100:
                # Разовый флак: первый холодный ответ платформы медленнее
                # бюджета браузера, и DOM выходит пустым (замер 20.08.2026 —
                # прогон подряд дал 40 байт и тут же 21 КБ). Повтор безопасен.
                time.sleep(3)
                dom, конс_а = хром(f"http://127.0.0.1:{ПОРТ}/app-page/{лид}/",
                                   в / "а2", None)
            _, конс_б = хром(f"http://127.0.0.1:{ПОРТ}/probe-frame", в / "б", None)
            хром(f"http://127.0.0.1:{ПОРТ}/probe-frame", в / "с",
                 папка / "окно_в_песочнице.png")
    finally:
        сервер.shutdown()

    (папка / "dom.html").write_text(dom, encoding="utf-8")
    (папка / "консоль.txt").write_text("\n".join(конс_а + ["── песочница ──"] + конс_б),
                                       encoding="utf-8")
    беды = разобрать(dom, конс_а, конс_б)
    print(f"проба окна {лид}: " + ("живое" if not беды else f"бед {len(беды)}"))
    for б in беды:
        print("  ·", б)
    print(f"  скриншот и консоль: {папка}")
    return 1 if беды else 0


def selftest() -> int:
    ошибки = []
    хороший = "<html><body><h1>Агент 1С</h1><p>" + "Живой текст панели. " * 8 + "</p></body></html>"
    if разобрать(хороший, [], []):
        ошибки.append("живое окно признано битым")
    if not any("белый экран" in б for б in разобрать("<html><body></body></html>", [], [])):
        ошибки.append("пустая страница не поймана")
    плашка = "<html><body>Связь с Extella: отказ. Повторить</body></html>"
    if разобрать(плашка, [], []):
        ошибки.append("честная плашка отказа принята за белый экран")
    метка = хороший.replace("</p>", " {{token}}</p>")
    if not any("подстановка" in б for б in разобрать(метка, [], [])):
        ошибки.append("светящаяся подстановка не поймана")
    консоль = ['[123:456:INFO:CONSOLE(1)] "Uncaught TypeError: x is not a function"']
    if not any("консоль" in б for б in разобрать(хороший, консоль, [])):
        ошибки.append("падение в консоли не поймано")
    if not any("песочнице" in б for б in разобрать(хороший, [], консоль)):
        ошибки.append("падение в песочнице не помечено источником")
    for о in ошибки:
        print("  ✗", о)
    print("selftest:", "провален" if ошибки else "пройден")
    return 1 if ошибки else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(прогнать(sys.argv[1]))
