#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Английское ведёт в английское, русское — в русское (H121).

ЗАЧЕМ. Замер 29.09.2026: публичный репозиторий открывался русским README, хотя
рядом лежало полное английское зеркало `en/` — 173 перевода, которые гейт держал в
согласии с оригиналом. Ни одна дорожка туда не вела: даже английский промпт и
английский текст приложения отправляли агента в русские `AGENT_START.md`,
`rules/…`, `SYMPTOMS.md`, а все 127 английских правил ссылались на русское
оглавление. Английский README лежал в `en/` со ссылками на код, битыми
относительно этой папки. Перевод, который никто не читает, — затраты без пользы.

ЧТО ПРОВЕРЯЕТСЯ:
  1. главная `README.md` — английская, `README.ru.md` — русская;
  2. английские копии промпта (`en/PROMPT_FOR_EXTERNAL_AGENT.md` и английский
     блок «Copy» в приложении) ведут только в `main/en/…`;
  3. русские копии в `main/en/…` не ведут;
  4. ни один английский документ (`README.md`, `en/**/*.md`) не шлёт читателя в
     русский документ, у которого есть английское зеркало, — ни raw-ссылкой, ни
     относительной ссылкой из главной.

КАКОГО РОДА ЭТА ПРОВЕРКА. Проверка исходников: ссылки разбираются в файлах, сеть
не трогается. Существует ли зеркало — решает наличие файла `en/<путь>`.

    python3 tools/check_english_route.py
    python3 tools/check_english_route.py --selftest

Коды выхода: 0 — языки не перепутаны, 1 — перепутаны.

ПРИЁМКА 29.09.2026: прогон по репозиторию после перестановки главной зелёный, пять
посевов пойманы, ложных тревог нет. До перестановки те же места считал разбор
english_routes: 139 английских ссылок вели в русские документы.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

КОРЕНЬ = pathlib.Path(__file__).resolve().parents[1]
БАЗА = "raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/"
RAW = re.compile(re.escape(БАЗА) + r"([A-Za-z0-9_./\-]+)")
ОТНОСИТЕЛЬНАЯ = re.compile(r"\]\(([^)\s#:]+\.md)(#[^)]*)?\)")
КИРИЛЛИЦА = re.compile(r"[А-Яа-яЁё]")


def путь_из(сырой: str) -> str:
    return сырой.rstrip(".,;:")


def есть_зеркало(корень: pathlib.Path, путь: str) -> bool:
    return not путь.startswith("en/") and (корень / "en" / путь).exists()


def блоки_приложения(корень: pathlib.Path) -> tuple[str, str]:
    """Копируемый промпт в приложении: русский и английский блоки."""
    д = json.loads((корень / "store_app" / "content.json").read_text(encoding="utf-8"))
    ру, ан = [], []
    for р in д.get("разделы", []):
        if 'class="copy"' in str(р.get("тело", "")) and "connect_mcp" in str(р.get("тело", "")):
            ру.append(str(р.get("тело", "")))
            ан.append(str(р.get("тело_en", "")))
    return "\n".join(ру), "\n".join(ан)


def разбор(корень: pathlib.Path) -> list[str]:
    беды = []

    главная = (корень / "README.md").read_text(encoding="utf-8")
    заголовок = next((с for с in главная.splitlines() if с.startswith("# ")), "")
    if КИРИЛЛИЦА.search(заголовок):
        беды.append("главная README.md снова русская — GitHub показывает её первой")
    ру_главная = корень / "README.ru.md"
    if not ру_главная.exists():
        беды.append("нет README.ru.md — русскому читателю некуда переключиться")
    elif not КИРИЛЛИЦА.search(ру_главная.read_text(encoding="utf-8")[:2000]):
        беды.append("README.ru.md не русский")

    ру_приложение, ан_приложение = блоки_приложения(корень)
    ан_копии = {"en/PROMPT_FOR_EXTERNAL_AGENT.md":
                (корень / "en" / "PROMPT_FOR_EXTERNAL_AGENT.md").read_text(encoding="utf-8"),
                "английский блок приложения": ан_приложение}
    ру_копии = {"PROMPT_FOR_EXTERNAL_AGENT.md":
                (корень / "PROMPT_FOR_EXTERNAL_AGENT.md").read_text(encoding="utf-8"),
                "русский блок приложения": ру_приложение}

    for имя, текст in ан_копии.items():
        for m in RAW.finditer(текст):
            п = путь_из(m.group(1))
            if есть_зеркало(корень, п):
                беды.append(f"{имя}: английский промпт ведёт в русский {п} — есть en/{п}")
    for имя, текст in ру_копии.items():
        for m in RAW.finditer(текст):
            п = путь_из(m.group(1))
            if п.startswith("en/"):
                беды.append(f"{имя}: русский промпт ведёт в английский {п}")

    английские = [корень / "README.md"] + sorted((корень / "en").rglob("*.md"))
    for f in английские:
        текст = f.read_text(encoding="utf-8")
        имя = f.relative_to(корень).as_posix()
        for m in RAW.finditer(текст):
            п = путь_из(m.group(1))
            if есть_зеркало(корень, п):
                беды.append(f"{имя}: ссылка в русский {п} — есть en/{п}")
        if f.name == "README.md" and f.parent == корень:
            for m in ОТНОСИТЕЛЬНАЯ.finditer(текст):
                п = m.group(1)
                if п in ("README.ru.md", "README.md"):
                    continue
                if есть_зеркало(корень, п):
                    беды.append(f"README.md: относительная ссылка в русский {п} — есть en/{п}")
    return беды


def прогон() -> int:
    беды = разбор(КОРЕНЬ)
    for б in беды[:40]:
        print("  ✗ " + б)
    if len(беды) > 40:
        print(f"  … и ещё {len(беды) - 40}")
    if беды:
        print(f"\nНЕ УСПЕХ (H121): английское ведёт в русское — {len(беды)} мест.")
        return 1
    print("ПРОВЕРКА ИСХОДНИКОВ пройдена (H121): главная английская, английские копии "
          "промпта и все английские документы ведут в английское, русские — в русское.")
    return 0


def selftest() -> int:
    import shutil
    import tempfile
    провалы = []
    print("Самопроверка check_english_route:")
    if разбор(КОРЕНЬ):
        провалы.append("живой репозиторий объявлен перепутанным — ложная тревога")
    else:
        print("  ✓ на живом репозитории тревоги нет")

    def посев(правка) -> list[str]:
        with tempfile.TemporaryDirectory() as вр:
            к = pathlib.Path(вр)
            for имя in ("README.md", "README.ru.md", "PROMPT_FOR_EXTERNAL_AGENT.md"):
                shutil.copy(КОРЕНЬ / имя, к / имя)
            shutil.copytree(КОРЕНЬ / "en", к / "en")
            (к / "store_app").mkdir()
            shutil.copy(КОРЕНЬ / "store_app" / "content.json", к / "store_app" / "content.json")
            правка(к)
            return разбор(к)

    def русская_главная(к):
        (к / "README.md").write_text("# Разработка на Extella\n", encoding="utf-8")

    def англ_промпт_в_русское(к):
        ф = к / "en" / "PROMPT_FOR_EXTERNAL_AGENT.md"
        ф.write_text(ф.read_text(encoding="utf-8").replace("/main/en/AGENT_START.md",
                                                           "/main/AGENT_START.md"), encoding="utf-8")

    def русский_промпт_в_английское(к):
        ф = к / "PROMPT_FOR_EXTERNAL_AGENT.md"
        ф.write_text(ф.read_text(encoding="utf-8").replace("/main/AGENT_START.md",
                                                           "/main/en/AGENT_START.md"), encoding="utf-8")

    def правило_в_русское_оглавление(к):
        ф = к / "en" / "rules" / "H106.md"
        ф.write_text(ф.read_text(encoding="utf-8").replace("/main/en/rules/INDEX.md",
                                                           "/main/rules/INDEX.md"), encoding="utf-8")

    def главная_относительно_в_русское(к):
        ф = к / "README.md"
        ф.write_text(ф.read_text(encoding="utf-8").replace("](en/AGENT_START.md)",
                                                           "](AGENT_START.md)", 1), encoding="utf-8")

    for имя, правка in (("русская главная", русская_главная),
                        ("английский промпт в русское", англ_промпт_в_русское),
                        ("русский промпт в английское", русский_промпт_в_английское),
                        ("английское правило в русское оглавление", правило_в_русское_оглавление),
                        ("главная относительной ссылкой в русское", главная_относительно_в_русское)):
        if not посев(правка):
            провалы.append(f"посев «{имя}» не пойман")
    if not any("не пойман" in п for п in провалы):
        print("  ✓ посевы ловятся (5 шт.)")

    if провалы:
        for п in провалы:
            print("  ✗ " + п)
        print("ИТОГ САМОПРОВЕРКИ: провалы есть")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    # H118: узкая консоль Windows (cp1252) роняет печать по-русски на первом символе.
    for _поток in (sys.stdout, sys.stderr):
        try:
            _поток.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(selftest() if "--selftest" in sys.argv else прогон())
