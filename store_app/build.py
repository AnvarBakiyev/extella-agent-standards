#!/usr/bin/env python3
"""Собрать index.html из шаблона и content.json.

Замысел: **текст живёт в одном месте** — в `content.json`. Оболочка (`page.template.html`)
меняется редко, содержимое — часто. Сборщик вкладывает снимок содержимого в страницу, чтобы
она рисовалась мгновенно и без сети, а живьём страница подтягивает тот же файл из репозитория
и подменяет себя, если версия новее.

Отсюда два способа обновить гид:
  1. коммит в `content.json` — у всех обновится при следующем открытии, ничего не публикуя;
  2. `python3 build.py` + замена страницы (update.py или форма) — если менялась сама оболочка.

Использование:
    python3 build.py            — собрать index.html
    python3 build.py --check    — проверить, что собранное совпадает с источниками
"""

import base64
import json
import pathlib
import re
import shutil
import subprocess
import sys

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
ШАБЛОН = ЗДЕСЬ / "page.template.html"
ДАННЫЕ = ЗДЕСЬ / "content.json"
ВЫХОД = ЗДЕСЬ / "index.html"

МЕТКА = re.compile(r"/\*СОДЕРЖИМОЕ\*/.*?/\*КОНЕЦ\*/", re.S)
# Строки оболочки — кнопки, статусы, отказы — вкладываются вторым блоком. Держать их
# в шаблоне россыпью значило иметь двуязычное содержимое внутри одноязычного окна.
МЕТКА_ОБОЛОЧКИ = re.compile(r"/\*ОБОЛОЧКА\*/.*?/\*КОНЕЦ_ОБОЛОЧКИ\*/", re.S)
ОБОЛОЧКА = ЗДЕСЬ / "shell.json"
МЕТКА_APP_TOKEN = '/*APP_TOKEN*/""'
ЛИМИТ_HTML = 3 * 1024 * 1024


def конструктор_скрипт() -> str:
    """Закреплённый TypeScript даёт одинаковый JS на всех поддерживаемых Node."""
    node = shutil.which("node")
    if not node:
        отказ("для TypeScript конструктора нужен Node.js и npm --prefix store_app ci")
    if not (ЗДЕСЬ / "node_modules" / "typescript").exists():
        отказ("сначала установи сборщик: npm --prefix store_app ci")
    try:
        результат = subprocess.run(
            [node, "-e",
             "const ts=require('typescript');const fs=require('node:fs');"
             "const out=ts.transpileModule(fs.readFileSync(0,'utf8'),{compilerOptions:{"
             "target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.None,newLine:ts.NewLineKind.LineFeed}});"
             "process.stdout.write(out.outputText);"],
            input=(ЗДЕСЬ / "constructor.ts").read_text(encoding="utf-8"),
            text=True, capture_output=True, check=True, cwd=ЗДЕСЬ)
    except subprocess.CalledProcessError as e:
        отказ("не удалось собрать constructor.ts: " + e.stderr.strip())
    return результат.stdout.replace("</script", "<\\/script")


def вставить(страница: str, метка: str, значение: str) -> str:
    if страница.count(метка) != 1:
        отказ(f"в шаблоне должно быть ровно одно место {метка}")
    return страница.replace(метка, значение, 1)


def отказ(что_делать: str):
    print(f"Не собрал: {что_делать}", file=sys.stderr)
    sys.exit(1)


def проверить_данные(d: dict):
    беды = []
    if not d.get("версия_содержимого"):
        беды.append("нет поля «версия_содержимого» — страница не поймёт, что появилось новее")
    разделы = d.get("разделы") or []
    if not разделы:
        беды.append("нет разделов")
    for i, р in enumerate(разделы, 1):
        для = f"раздел {i}"
        for поле in ("номер", "заголовок", "тело"):
            if not р.get(поле):
                беды.append(f"{для}: нет поля «{поле}»")
        тело = р.get("тело") or ""
        if "<script" in тело.lower():
            беды.append(f"{для}: внутри <script> — содержимое обязано быть данными, не кодом")
        if "{" + "{" in тело:
            беды.append(f"{для}: метка подстановки в тексте — платформа заменит её значением")
        if тело.count("<div") != тело.count("</div>"):
            беды.append(f"{для}: разметка не закрыта")
    if беды:
        отказ("сначала поправь content.json: " + "; ".join(беды))


def собрать() -> str:
    if not ШАБЛОН.exists():
        отказ(f"нет шаблона {ШАБЛОН.name}")
    if not ДАННЫЕ.exists():
        отказ(f"нет данных {ДАННЫЕ.name}")

    d = json.loads(ДАННЫЕ.read_text())
    проверить_данные(d)

    шаблон = ШАБЛОН.read_text()
    if not МЕТКА_ОБОЛОЧКИ.search(шаблон):
        отказ("в шаблоне нет метки /*ОБОЛОЧКА*/…/*КОНЕЦ_ОБОЛОЧКИ*/")
    if not МЕТКА.search(шаблон):
        отказ("в шаблоне нет места для содержимого (метка /*СОДЕРЖИМОЕ*/…/*КОНЕЦ*/)")
    if шаблон.count(МЕТКА_APP_TOKEN) != 1:
        отказ("в шаблоне должно быть ровно одно место для app_token")

    снимок = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    # </script> внутри данных закрыл бы наш собственный тег раньше времени.
    снимок = снимок.replace("</", "<\\/")
    страница = МЕТКА.sub(lambda _: "/*СОДЕРЖИМОЕ*/" + снимок + "/*КОНЕЦ*/", шаблон, count=1)
    оболочка = json.loads(ОБОЛОЧКА.read_text(encoding="utf-8"))
    беды_оболочки = [к for к, з in (оболочка.get("строки") or {}).items()
                     if not str(з.get("ru") or "").strip() or not str(з.get("en") or "").strip()]
    if беды_оболочки:
        отказ("в shell.json нет перевода у строк: " + ", ".join(sorted(беды_оболочки)[:8]))
    слепок_оболочки = json.dumps(оболочка, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    страница = МЕТКА_ОБОЛОЧКИ.sub(
        lambda _: "/*ОБОЛОЧКА*/" + слепок_оболочки + "/*КОНЕЦ_ОБОЛОЧКИ*/", страница, count=1)
    страница = страница.replace(МЕТКА_APP_TOKEN, '/*APP_TOKEN*/"{{app_token}}"', 1)
    страница = вставить(страница, "/*XTL_CONSTRUCTOR_CSS*/",
                       (ЗДЕСЬ / "constructor.css").read_text(encoding="utf-8"))
    страница = вставить(страница, "/*XTL_CONSTRUCTOR_SCRIPT*/", конструктор_скрипт())
    страница = вставить(страница, "/*XTL_FONTS*/",
                       (ЗДЕСЬ.parent / "assets" / "extella-fonts.css").read_text(encoding="utf-8"))
    медиа = {}
    for имя, файл, тип in [("DESKTOP", "desktop.jpg", "jpeg"), ("CHAT", "chat-poster.png", "png")]:
        данные = base64.b64encode((ЗДЕСЬ / "assets" / файл).read_bytes()).decode("ascii")
        медиа[имя] = f"data:image/{тип};base64,{данные}"
    страница = вставить(страница, "/*XTL_MEDIA*/{}", json.dumps(медиа, separators=(",", ":")))

    if len(страница.encode()) > ЛИМИТ_HTML:
        отказ("страница больше 3 МБ — лимит одиночного HTML. Собери zip-бандл")
    return страница


if __name__ == "__main__":
    готово = собрать()
    if "--check" in sys.argv:
        если_есть = ВЫХОД.read_text() if ВЫХОД.exists() else ""
        if если_есть == готово:
            print("index.html совпадает с шаблоном и content.json")
        else:
            отказ("index.html отстал от источников — запусти build.py без --check")
    else:
        ВЫХОД.write_text(готово)
        d = json.loads(ДАННЫЕ.read_text())
        print(f"Собрал index.html: {len(готово.encode())} байт, "
              f"разделов {len(d['разделы'])}, содержимое {d['версия_содержимого']}")
