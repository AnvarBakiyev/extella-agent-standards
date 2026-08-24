#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Показать человеку его приложение — и доказать, что оно откроется у других.

Ставится сразу после закрытой выкладки: агент не рассказывает, что «всё готово»,
а показывает картинку. Требование H66 (первый показ рано и по предложению машины)
плюс H62–H63 (проверка открытия и прокликивания на чужой машине).

    python3 tools/show.py <listing_id>

Что делает: просит стенд открыть приложение как посторонний покупатель на живом
os.extella.ai, забирает вердикт и снимок экрана, кладёт снимок рядом и говорит
обычными словами, что увидит человек.

Стенд задаётся переменными EXTELLA_BENCH_URL и EXTELLA_BENCH_KEY либо файлом
~/.extella_bench.json вида {"url": "...", "key": "..."}. Стенда нет — скрипт не
падает: печатает адрес приложения и как завести стенд (СТЕНД_РЕЦЕПТ.md).

Коды выхода: 0 — показывать можно, 1 — у постороннего не открывается, 2 — не
удалось проверить (стенд не настроен или не ответил).
"""
import base64
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

НАСТРОЙКИ = pathlib.Path.home() / ".extella_bench.json"
СНИМКИ = pathlib.Path("dist")


def стенд() -> tuple[str, str]:
    адрес = os.environ.get("EXTELLA_BENCH_URL", "")
    ключ = os.environ.get("EXTELLA_BENCH_KEY", "")
    if not адрес and НАСТРОЙКИ.exists():
        данные = json.loads(НАСТРОЙКИ.read_text(encoding="utf-8"))
        адрес, ключ = данные.get("url", ""), данные.get("key", "")
    return адрес.rstrip("/"), ключ


def спросить_стенд(адрес: str, ключ: str, лид: str) -> dict:
    запрос = urllib.request.Request(
        f"{адрес}/priemka?lid={лид}", headers={"X-Bench-Key": ключ})
    with urllib.request.urlopen(запрос, timeout=600) as ответ:
        return json.loads(ответ.read())


def сохранить_снимок(вердикт: dict, лид: str) -> pathlib.Path | None:
    данные = вердикт.get("скриншот")
    if not данные or "," not in данные:
        return None
    СНИМКИ.mkdir(exist_ok=True)
    путь = СНИМКИ / f"{лид}.png"
    путь.write_bytes(base64.b64decode(данные.split(",", 1)[1]))
    return путь


def сказать_словами(вердикт: dict, снимок: pathlib.Path | None, лид: str) -> int:
    цвет = вердикт.get("цвет")
    print()
    if цвет == "зелёный":
        print("Открывается. Вот что увидит человек на своём компьютере:")
    elif цвет == "красный":
        print("У постороннего НЕ открывается — показывать пока нечего:")
        for беда in вердикт.get("жёсткие", []):
            print("  ·", беда)
    elif цвет == "жёлтый":
        print("Открывается, но с оговоркой:")
        for беда in вердикт.get("мягкие", []):
            print("  ·", беда)
    else:
        print("Проверить не удалось:", "; ".join(вердикт.get("мягкие", [])) or "нет ответа")

    for строка in вердикт.get("проклик", []) or []:
        print("  · кнопки:", строка)

    if снимок:
        print(f"\nСнимок: {снимок}")
        if sys.platform == "darwin":
            subprocess.run(["open", str(снимок)], check=False)
    print(f"Адрес приложения: https://os.extella.ai/app-page/{лид}/")
    return 1 if вердикт.get("блок") else 0


def без_стенда(лид: str) -> int:
    print("\nПриложение выложено закрытой версией. Открыть можно здесь:")
    print(f"  https://os.extella.ai/app-page/{лид}/")
    print("\nПроверить, что оно откроется и у ДРУГИХ, пока нечем: тестовый стенд не")
    print("настроен. Как завести — СТЕНД_РЕЦЕПТ.md (одна команда), после этого показ")
    print("будет сразу с доказательством: снимок того, что видит посторонний.")
    return 2


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    лид = sys.argv[1].strip()
    адрес, ключ = стенд()
    if not адрес or not ключ:
        return без_стенда(лид)
    print(f"Открываю приложение на чистом стенде как посторонний покупатель…")
    try:
        вердикт = спросить_стенд(адрес, ключ, лид)
    except urllib.error.HTTPError as e:
        print(f"Стенд отказал: HTTP {e.code}. Проверь адрес и ключ стенда.")
        return 2
    except Exception as e:                                 # noqa: BLE001
        print(f"Стенд не ответил: {str(e)[:160]}")
        return 2
    if вердикт.get("ошибка"):
        print("Стенд не смог:", вердикт["ошибка"])
        return 2
    return сказать_словами(вердикт, сохранить_снимок(вердикт, лид), лид)


if __name__ == "__main__":
    sys.exit(main())
