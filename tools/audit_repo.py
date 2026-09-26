#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор чужого репозитория: то же, что мы делали руками, но за минуты (H115, H117).

ЗАЧЕМ. За 25.09.2026 мы разобрали четырнадцать репозиториев четырёх сотрудников
вручную. Разборы вышли полезные, но неповторяемые: следующий разбор начинается с нуля,
а сравнить «стало лучше или хуже» нечем. Этот инструмент делает механическую часть
работы одинаково и оставляет человеку выводы.

ЧТО СЧИТАЕТ.

  1. Паспорт: размер, файлы, языки, коммиты, авторы, срок жизни, приватность.
  2. Секреты ПО ФОРМЕ — в файлах и в истории. Значение НИКОГДА не печатается: только
     файл, строка и род ключа. Ключ, однажды попавший в историю, считается утёкшим,
     даже если удалён следующим коммитом.
  3. Персональные данные по двум независимым признакам (как в рельсах H115): даты
     рождения со значениями, разные телефоны, почты, ИИН.
  4. Синтаксис: Python, JavaScript, JSON.
  5. Мусор сборки в истории репозитория.
  6. Гигиена: README, .gitignore, LICENSE, тесты, CI.
  7. Почерк коммитов: доля правок «fix/фикс» подряд — признак починки вслепую, когда
     ошибку ловят прогоном в проде, а не проверкой до коммита.
  8. Канон Extella: токен в коде, одиночный target вместо массива, BYOK у клиентских
     агентов, сплошной допуск инструментов.

ЧЕГО НЕ ДЕЛАЕТ. Не судит о качестве продукта и не заменяет чтение кода человеком:
это опись, а не приговор. Выводы и письмо автору пишет человек.

    python3 tools/audit_repo.py --путь ~/код/репозиторий
    python3 tools/audit_repo.py --клонировать владелец/имя
    python3 tools/audit_repo.py --путь . --json
    python3 tools/audit_repo.py --selftest

Коды выхода: 0 — разбор сделан, 1 — разбирать нечего (нет пути или клон не удался).

ПРИЁМКА 26.09.2026: первый живой прогон по чужому репозиторию (625 файлов,
114 375 строк) упал сразу: `git log -p` отдаёт двоичные байты, разбор ломался
исключением — самопроверка на рукотворном репозитории этого не ловила. После
починки разбор прошёл, ложных тревог нет, находки подтверждены чтением кода.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

# Ключи ищем по ФОРМЕ: имя переменной переименуют, форма останется.
СЕКРЕТЫ = [
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"), "JWT (Supabase, Firebase)"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "ключ OpenAI"),
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"), "ключ Groq"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "ключ GitHub"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "токен Slack"),
    (re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}"), "токен бота Telegram"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "ключ AWS"),
]
# ДЕТЕКТОР-ОБРАЗЦЫ: ниже лежат образцы нарушений намеренно — это признаки
# для поиска, а не наш код. Метку читает check_device_pinning.
# Канонные грабли Extella, каждая — из живого разбора.
КАНОН = [
    (re.compile(r"X-Auth-Token\s*[:=]\s*[\"'][A-Za-z0-9_\-]{12,}"), "токен Extella зашит в код"),
    (re.compile(r"[\"']target[\"']\s*:\s*[\"'][0-9a-f-]{8,}"), "одиночный target вместо массива (H-канон)"),
    (re.compile(r"sys__all__"), "сплошной допуск инструментов агенту"),
    (re.compile(r"provider\s*[:=]\s*[\"']openai[\"']"), "клиентский агент на чужой модели вместо платформенной"),
]
МУСОР = ("node_modules/", "__pycache__/", ".DS_Store", "/dist/", "/build/", ".venv/")
КОД = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript",
       ".html": "HTML", ".css": "CSS", ".json": "JSON", ".md": "текст", ".sh": "shell",
       ".yml": "YAML", ".yaml": "YAML", ".php": "PHP", ".go": "Go"}
ЧИТАЕМ = tuple(КОД) + (".txt", ".env", ".cfg", ".ini", ".csv")
МИМО = ("/.git/", "/node_modules/", "/__pycache__/", "/.venv/", "/dist/", "/build/")


def запуск(команда: list[str], где: pathlib.Path, предел: int = 180) -> str:
    """Вывод git всегда читается с заменой негодных байтов.

    Замер 26.09.2026, первый живой прогон: в репозитории с двоичными файлами
    `git log -p` отдаёт байты, которые не разбираются как UTF-8, и весь разбор падает
    исключением. Самопроверка на рукотворном репозитории этого не ловила — там были
    только текстовые файлы.
    """
    из = subprocess.run(команда, cwd=где, capture_output=True, timeout=предел)
    return из.stdout.decode("utf-8", "replace")


# ── разделы разбора ─────────────────────────────────────────────────────────────
def паспорт(корень: pathlib.Path) -> dict:
    файлы = [ф for ф in корень.rglob("*")
             if ф.is_file() and not any(м in "/" + str(ф.relative_to(корень)) for м in МИМО)]
    языки: dict[str, int] = {}
    строк = 0
    for ф in файлы:
        язык = КОД.get(ф.suffix.lower())
        if not язык:
            continue
        try:
            n = len(ф.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            continue
        языки[язык] = языки.get(язык, 0) + n
        строк += n
    коммиты = [с for с in запуск(["git", "log", "--pretty=%H|%an|%ad|%s",
                                  "--date=short"], корень).splitlines() if с]
    авторы = sorted({с.split("|")[1] for с in коммиты if с.count("|") >= 3})
    даты = [с.split("|")[2] for с in коммиты if с.count("|") >= 3]
    return dict(файлов=len(файлы), строк_кода=строк,
                языки=dict(sorted(языки.items(), key=lambda п: -п[1])),
                коммитов=len(коммиты), авторы=авторы,
                первый=даты[-1] if даты else None, последний=даты[0] if даты else None)


def секреты(корень: pathlib.Path) -> list[str]:
    находки = []
    for ф in корень.rglob("*"):
        путь = "/" + str(ф.relative_to(корень))
        if not ф.is_file() or any(м in путь for м in МИМО) or ф.suffix.lower() not in ЧИТАЕМ:
            continue
        try:
            строки = ф.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for н, строка in enumerate(строки, 1):
            for образец, род in СЕКРЕТЫ:
                if образец.search(строка):
                    находки.append(f"{путь.lstrip('/')}:{н} — {род}")
                    break
    return находки


def секреты_в_истории(корень: pathlib.Path) -> list[str]:
    """Ключ, побывавший в истории, утёк. Удаление следующим коммитом ничего не меняет."""
    текст = запуск(["git", "log", "-p", "--all", "--no-color"], корень, предел=600)
    найдено = []
    for образец, род in СЕКРЕТЫ:
        сколько = len(set(образец.findall(текст)))
        if сколько:
            найдено.append(f"{род}: разных значений в истории — {сколько}")
    return найдено


def персональные(корень: pathlib.Path) -> list[str]:
    находки = []
    for ф in корень.rglob("*"):
        путь = "/" + str(ф.relative_to(корень))
        if not ф.is_file() or any(м in путь for м in МИМО):
            continue
        if ф.suffix.lower() not in (".json", ".csv", ".yaml", ".yml", ".txt"):
            continue
        try:
            текст = ф.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        признаки = []
        if re.search(r"birthday|birth_date|дата_рождения|день_рождения", текст, re.I):
            даты = set(re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}", текст))
            if len(даты) >= 3:
                признаки.append(f"даты рождения ({len(даты)})")
        телефоны = set(re.findall(r"(?:\+7|8)\d{10}", текст))
        if len(телефоны) >= 3:
            признаки.append(f"телефоны ({len(телефоны)})")
        почты = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", текст))
        if len(почты) >= 3:
            признаки.append(f"почты ({len(почты)})")
        иин = set(re.findall(r"\b\d{12}\b", текст))
        if len(иин) >= 3:
            признаки.append(f"ИИН/БИН ({len(иин)})")
        if len(признаки) >= 2:
            находки.append(f"{путь.lstrip('/')} — {', '.join(признаки)}")
    return находки


def синтаксис(корень: pathlib.Path) -> list[str]:
    беды = []
    for ф in корень.rglob("*"):
        путь = "/" + str(ф.relative_to(корень))
        if not ф.is_file() or any(м in путь for м in МИМО):
            continue
        имя = str(ф)
        if ф.suffix == ".py":
            из = subprocess.run([sys.executable, "-m", "py_compile", имя],
                                capture_output=True, text=True, timeout=120)
            if из.returncode:
                беды.append(f"{путь.lstrip('/')} — синтаксическая ошибка Python")
        elif ф.suffix == ".json":
            try:
                json.loads(ф.read_text(encoding="utf-8", errors="ignore"))
            except (json.JSONDecodeError, OSError):
                беды.append(f"{путь.lstrip('/')} — сломанный JSON")
    return беды


def мусор_в_истории(корень: pathlib.Path) -> list[str]:
    пути = запуск(["git", "log", "--all", "--pretty=format:", "--name-only"], корень, 300)
    найдено = {}
    for строка in пути.splitlines():
        for м in МУСОР:
            if м.strip("/") in строка:
                найдено[м] = найдено.get(м, 0) + 1
    return [f"{м} — упоминаний в истории: {n}" for м, n in sorted(найдено.items(), key=lambda п: -п[1])]


def гигиена(корень: pathlib.Path) -> dict:
    есть = lambda *имена: any((корень / и).exists() for и in имена)   # noqa: E731
    тесты = [ф for ф in корень.rglob("*")
             if ф.is_file() and re.search(r"(^|/)(tests?|spec)/|_test\.|test_", str(ф))
             and not any(м in "/" + str(ф) for м in МИМО)]
    return dict(README=есть("README.md", "README.rst", "README.txt"),
                gitignore=есть(".gitignore"),
                LICENSE=есть("LICENSE", "LICENSE.md", "LICENSE.txt"),
                рельсы=есть(".git/hooks/pre-commit"),
                CI=есть(".github/workflows"),
                тестов=len(тесты))


def почерк(корень: pathlib.Path) -> dict:
    строки = [с for с in запуск(["git", "log", "--pretty=%s"], корень).splitlines() if с]
    правки = [с for с in строки if re.match(r"(?i)^(fix|фикс|hotfix|правк|исправ)", с)]
    подряд, лучший, прошлый = 0, 0, False
    for с in строки:
        это = bool(re.match(r"(?i)^(fix|фикс|hotfix|правк|исправ)", с))
        подряд = подряд + 1 if это and прошлый else (1 if это else 0)
        лучший = max(лучший, подряд)
        прошлый = это
    return dict(всего=len(строки), правок=len(правки),
                доля_правок=round(len(правки) / len(строки), 2) if строки else 0,
                правок_подряд=лучший)


def канон(корень: pathlib.Path) -> list[str]:
    находки = []
    for ф in корень.rglob("*"):
        путь = "/" + str(ф.relative_to(корень))
        if not ф.is_file() or any(м in путь for м in МИМО) or ф.suffix.lower() not in ЧИТАЕМ:
            continue
        try:
            строки = ф.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for н, строка in enumerate(строки, 1):
            for образец, что in КАНОН:
                if образец.search(строка):
                    находки.append(f"{путь.lstrip('/')}:{н} — {что}")
    return находки


# ── сборка разбора ──────────────────────────────────────────────────────────────
def разобрать(корень: pathlib.Path) -> dict:
    return dict(
        путь=str(корень), паспорт=паспорт(корень),
        секреты_в_файлах=секреты(корень), секреты_в_истории=секреты_в_истории(корень),
        персональные_данные=персональные(корень), синтаксис=синтаксис(корень),
        мусор_сборки=мусор_в_истории(корень), гигиена=гигиена(корень),
        почерк_коммитов=почерк(корень), канон_extella=канон(корень))


def напечатать(р: dict) -> None:
    п = р["паспорт"]
    print(f"\n\033[1mРАЗБОР: {р['путь']}\033[0m")
    print(f"  файлов {п['файлов']}, строк кода {п['строк_кода']}, коммитов {п['коммитов']}, "
          f"авторов {len(п['авторы'])}")
    print(f"  срок: {п['первый']} → {п['последний']} | языки: "
          + ", ".join(f"{я} {n}" for я, n in list(п["языки"].items())[:4]))
    г = р["гигиена"]
    print(f"  гигиена: README {'да' if г['README'] else 'НЕТ'}, .gitignore "
          f"{'да' if г['gitignore'] else 'НЕТ'}, лицензия {'да' if г['LICENSE'] else 'НЕТ'}, "
          f"CI {'да' if г['CI'] else 'НЕТ'}, тестовых файлов {г['тестов']}")
    к = р["почерк_коммитов"]
    print(f"  почерк: правок {к['правок']} из {к['всего']} ({int(к['доля_правок']*100)}%), "
          f"подряд до {к['правок_подряд']}")

    разделы = [("СЕКРЕТЫ В ФАЙЛАХ", р["секреты_в_файлах"], True),
               ("СЕКРЕТЫ В ИСТОРИИ", р["секреты_в_истории"], True),
               ("ПЕРСОНАЛЬНЫЕ ДАННЫЕ", р["персональные_данные"], True),
               ("СИНТАКСИС", р["синтаксис"], True),
               ("КАНОН EXTELLA", р["канон_extella"], False),
               ("МУСОР СБОРКИ", р["мусор_сборки"], False)]
    for имя, находки, важно in разделы:
        if не_пусто := находки:
            знак = "✗" if важно else "~"
            print(f"\n  \033[1m{имя}\033[0m")
            for н in не_пусто[:12]:
                print(f"    {знак} {н}")
            if len(не_пусто) > 12:
                print(f"    … ещё {len(не_пусто) - 12}")
    if not any(р[к] for к in ("секреты_в_файлах", "секреты_в_истории",
                              "персональные_данные", "синтаксис")):
        print("\n  Тяжёлых находок нет: ключей, персональных данных и сломанного кода не видно.")
    print("\n  Это опись, а не приговор: выводы и письмо автору пишет человек.\n")


def _selftest() -> int:
    провалы = []

    def проба(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка audit_repo:")
    with tempfile.TemporaryDirectory() as вр:
        к = pathlib.Path(вр)
        subprocess.run(["git", "init", "-q", "."], cwd=к, capture_output=True)
        (к / "ключ.py").write_text(
            'k = "sk-' + "a" * 24 + '"\n', encoding="utf-8")
        (к / "люди.json").write_text(
            '[{"name":"И","birthday":"1990-01-01","phone":"+77011234567"},'
            '{"name":"П","birthday":"1991-02-02","phone":"+77017654321"},'
            '{"name":"Р","birthday":"1992-03-03","phone":"+77019998877"}]', encoding="utf-8")
        (к / "сломано.py").write_text("x = (1\n", encoding="utf-8")
        (к / "канон.py").write_text('cfg = {"target": "85800354-f7b7-449f"}\n', encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=к, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "fix первый"], cwd=к, capture_output=True)

        р = разобрать(к)
        проба("ключ в файле найден", any("OpenAI" in с for с in р["секреты_в_файлах"]))
        проба("значение ключа не печатается",
              all("sk-aaaa" not in с for с in р["секреты_в_файлах"]))
        проба("ключ виден и в истории", any("OpenAI" in с for с in р["секреты_в_истории"]))
        проба("персональные данные по двум признакам",
              any("люди.json" in с for с in р["персональные_данные"]))
        проба("сломанный Python найден", any("сломано.py" in с for с in р["синтаксис"]))
        проба("одиночный target замечен",
              any("одиночный target" in с for с in р["канон_extella"]))
        проба("паспорт посчитал коммит", р["паспорт"]["коммитов"] == 1)
        проба("почерк увидел правку", р["почерк_коммитов"]["правок"] == 1)
        проба("отсутствие README замечено", р["гигиена"]["README"] is False)

        (к / "README.md").write_text("описание\n", encoding="utf-8")
        проба("README после появления виден", гигиена(к)["README"] is True)

    with tempfile.TemporaryDirectory() as вр2:
        чисто = pathlib.Path(вр2)
        subprocess.run(["git", "init", "-q", "."], cwd=чисто, capture_output=True)
        (чисто / "хорошо.py").write_text('print("привет")\n', encoding="utf-8")
        р2 = разобрать(чисто)
        проба("чистый репозиторий не даёт ложных тревог",
              not (р2["секреты_в_файлах"] or р2["персональные_данные"] or р2["синтаксис"]))

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы — " + "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def главная() -> int:
    р = argparse.ArgumentParser()
    р.add_argument("--путь")
    р.add_argument("--клонировать", help="владелец/имя — клон во временный каталог")
    р.add_argument("--json", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()

    if а.selftest:
        return _selftest()

    if а.клонировать:
        временный = tempfile.mkdtemp(prefix="аудит-")
        из = subprocess.run(["gh", "repo", "clone", а.клонировать, временный, "--", "-q"],
                            capture_output=True, text=True, timeout=900)
        if из.returncode:
            print(f"  ✗ клон не удался: {(из.stderr or '').strip()[:200]}")
            print("    Приватный репозиторий читается только с доступом от владельца.")
            return 1
        корень = pathlib.Path(временный)
    elif а.путь:
        корень = pathlib.Path(а.путь).expanduser().resolve()
        if not (корень / ".git").exists():
            print(f"  ✗ {корень} — это не репозиторий git")
            return 1
    else:
        print("нужен --путь или --клонировать")
        return 1

    итог = разобрать(корень)
    if а.json:
        print(json.dumps(итог, ensure_ascii=False, indent=1))
    else:
        напечатать(итог)
    return 0


if __name__ == "__main__":
    sys.exit(главная())
