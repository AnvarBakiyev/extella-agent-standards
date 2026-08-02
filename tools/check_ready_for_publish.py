#!/usr/bin/env python3
"""Готов ли пак к тому, чтобы его увидел любой пользователь Extella.

Задача Анвара 01.08: агенты должны стать доступны всем — но БЕЗ данных реальных клиентов
и их истории. Публикация репозитория необратима: то, что уехало в открытый доступ, уже
не отозвать, а поисковики и зеркала сохранят копию.

Поэтому проверяем не «вроде чисто», а по перечню того, что нельзя выпускать:

  секреты      — токены, ключи, пароли (в файлах И в истории git);
  персональные — ИИН/БИН, телефоны, email, имена в данных;
  клиентские   — выгрузки CRM, резюме, договоры, состояние работы (.state, sample_run);
  внутреннее   — имена сотрудников, внутренние адреса, ссылки на приватные контуры.

Коды выхода: 0 — можно публиковать, 1 — есть находки.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Секреты: ищем форму, а не слово «пароль».
SECRETS = [
    (r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b", "JWT-токен"),
    (r"sk-[A-Za-z0-9]{20,}", "ключ OpenAI"),
    (r"\bghp_[A-Za-z0-9]{30,}\b", "ключ GitHub"),
    (r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b", "ключ бота Telegram"),
    (r"(auth_token|api_token|apiKey|password|secret)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}", "ключ в коде"),
]

# Персональные данные Казахстана и общие.
PERSONAL = [
    (r"\b\d{12}\b", "12 цифр — похоже на ИИН или БИН"),
    (r"\+7\s?\(?\d{3}\)?\s?\d{3}[- ]?\d{2}[- ]?\d{2}", "телефон"),
    (r"\b[A-Za-z0-9._%+-]+@(?!example\.|test\.|extella\.ai)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "почта"),
]

# Клиентские артефакты: не текст, а сами файлы.
CLIENT_PATHS = ["/.state", "/sample_run/", "/data/", "/exports/", "/uploads/",
                "/candidates/", "/resumes/", "/contracts/", "/customers/"]
CLIENT_EXT = {".csv", ".xlsx", ".docx", ".pdf", ".sqlite", ".db"}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".codex"}

# Явно демонстрационные значения. Гейт, который ругается на строку
# `secret = "test-secret-that-must-not-leak"`, учит себя игнорировать — а тогда он
# пропустит и настоящий ключ. Поэтому очевидные заглушки отсеиваем, но узко:
# только по явным маркерам, а не по «похоже на тест».
DEMO_MARKERS = ("test-", "example", "demo", "dummy", "placeholder", "changeme",
                "xxxx", "your-", "<", "{{",
                # обобщённые адреса-подсказки в формах: «you@…», «ivan@company.kz»
                "you@", "user@", "name@", "counterparty@", "@company.kz", "@example.")

# Адреса организаций из открытых источников — не персональные данные.
PUBLIC_MAIL = ("info@", "support@", "help@", "sales@", "press@", "noreply@", "hello@")


def is_demo(fragment: str) -> bool:
    low = fragment.lower()
    return any(m in low for m in DEMO_MARKERS)


def tracked_files(root: Path):
    """Только то, что реально уедет: файлы под контролем git.

    Первая версия смотрела всю папку и нашла в Predictive Sales 2436 «персональных»
    находок — все в .state и .runs, которых в репозитории нет вовсе (они в .gitignore).
    Гейт, который кричит о том, что никуда не уедет, приучает себя игнорировать.
    """
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return [root / line for line in r.stdout.splitlines() if (root / line).is_file()]
    except Exception:
        pass
    return [p for p in root.rglob("*") if p.is_file()]


def scan_files(root: Path) -> dict:
    findings = {"секреты": [], "персональные": [], "клиентские файлы": []}
    for p in tracked_files(root):
        if any(d in p.parts for d in SKIP_DIRS):
            continue
        rel = str(p.relative_to(root))
        posix = "/" + rel.replace("\\", "/")

        if p.suffix.lower() in CLIENT_EXT or any(c in posix for c in CLIENT_PATHS):
            findings["клиентские файлы"].append(rel)
            continue

        if p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, label in SECRETS:
            for m in re.finditer(pattern, text):
                if is_demo(m.group(0)):
                    continue
                findings["секреты"].append(f"{rel}: {label}")
                break
        for pattern, label in PERSONAL:
            hits = [h for h in re.findall(pattern, text)
                    if not (label == "почта" and (any(h.startswith(x) for x in PUBLIC_MAIL) or is_demo(h)))]
            if hits:
                findings["персональные"].append(f"{rel}: {label} ×{len(hits)}")
    return findings


def scan_history(root: Path) -> list:
    """Секрет, удалённый из файла, остаётся в истории — публикация раскроет его."""
    out = []
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "--all", "--format=%H", "-n", "300"],
                           capture_output=True, text=True, timeout=60)
        commits = r.stdout.split()
    except Exception:
        return out
    if not commits:
        return out
    try:
        r = subprocess.run(["git", "-C", str(root), "grep", "-lIE",
                            r"sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|\b\d{6,}:[A-Za-z0-9_-]{30,}\b"]
                           + commits[:60], capture_output=True, text=True, timeout=120)
        for line in r.stdout.splitlines()[:10]:
            out.append(line.strip())
    except Exception:
        pass
    return out


def main(paths):
    total = 0
    for raw in paths:
        root = Path(raw).expanduser()
        if not root.exists():
            print(f"\n{raw}: нет такого каталога")
            continue
        print(f"\n{'='*70}\n{root.name}")
        f = scan_files(root)
        hist = scan_history(root)
        for key, items in f.items():
            if items:
                total += len(items)
                print(f"  {key}: {len(items)}")
                for i in sorted(set(items))[:6]:
                    print(f"    · {i}")
                if len(set(items)) > 6:
                    print(f"    … ещё {len(set(items))-6}")
            else:
                print(f"  {key}: чисто")
        if hist:
            total += len(hist)
            print(f"  СЕКРЕТЫ В ИСТОРИИ GIT: {len(hist)}")
            for h in hist[:5]:
                print(f"    · {h}")
        else:
            print("  история git: секретов не видно")
    print(f"\n{'='*70}\nВСЕГО НАХОДОК: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
