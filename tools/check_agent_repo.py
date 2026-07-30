#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт на входе: годится ли репозиторий коллеги к установке агентом.

ЗАЧЕМ. Задача Анвара 30.07: коллеги делают агентов по стандартам, кладут в свой GitHub и
САМИ ставят их в Плагины по ссылке — без нас в середине. Чтобы это не превратилось в
свалку через месяц, ссылка проверяется ДО установки, а не после.

«По стандартам» перестаёт быть просьбой и становится условием: нет паспорта — нет
установки. Причём отказ обязан называть, чего именно не хватает, иначе коллега будет
гадать, а гадать он придёт к нам — то есть мы снова окажемся в середине.

МАНИФЕСТ — ЭТО ПАСПОРТ АГЕНТА, а не новый формат. `agent_passport.yaml` в корне
репозитория. Причина простая: два формата неизбежно разъедутся, и мы это сегодня видели
трижды. Паспорт уже описывает всё нужное — имя, цель словами клиента, модель, способности,
границы, откат — и уже проверяется гейтом `check_agent_passport.py`.

Как пользоваться:
  python3 check_agent_repo.py https://github.com/<owner>/<repo>
  python3 check_agent_repo.py --json https://github.com/<owner>/<repo>
  python3 check_agent_repo.py --selftest

Коды выхода: 0 — можно ставить, 1 — отказ (причина названа), 2 — ссылка не разобрана.
"""
import json
import os
import re
import subprocess
import sys

MANIFEST = "agent_passport.yaml"
# Ветки по порядку: у большинства main, у части master.
BRANCHES = ("main", "master")
RAW = "https://raw.githubusercontent.com/%s/%s/%s/" + MANIFEST


def parse_repo(url):
    """owner/repo из любой формы ссылки. Возвращает None, если это не GitHub-репозиторий."""
    u = (url or "").strip().rstrip("/")
    u = re.sub(r"\.git$", "", u)
    m = re.search(r"github\.com[:/]+([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", u)
    return (m.group(1), m.group(2)) if m else None


def fetch(url, timeout=25):
    r = subprocess.run(["curl", "-s", "-w", "\\n%{http_code}", "--max-time", str(timeout), url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return (code.strip(), body)


def gh_token():
    """Ключ GitHub для приватных репозиториев: переменная среды или gh CLI. Пусто — не ошибка."""
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if t:
        return t
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def api(url, token, raw=False, timeout=25):
    """GitHub API одним вызовом. Возвращает (код, тело)."""
    hdr = ["-H", "Accept: application/vnd.github.raw" if raw else "Accept: application/vnd.github+json",
           "-H", "User-Agent: extella-agent-gate"]
    if token:
        hdr += ["-H", "Authorization: token %s" % token]
    r = subprocess.run(["curl", "-s", "-w", "\n%{http_code}", "--max-time", str(timeout)] + hdr + [url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return code.strip(), body


def find_manifest(owner, repo):
    """Возвращает (ветка, текст, причина). Причина заполняется, только если файла нет.

    ПРИВАТНЫЕ РЕПОЗИТОРИИ: raw.githubusercontent отдаёт 404 и на приватный, и на
    несуществующий — раньше человек с приватным репозиторием получал «нет паспорта» и шёл
    искать файл, который у него есть. Теперь при промахе спрашиваем API: репозитория нет,
    доступа нет или паспорта нет — три разных ответа.
    """
    for br in BRANCHES:
        code, body = fetch(RAW % (owner, repo, br))
        if code == "200" and body.strip():
            return br, body, None

    token = gh_token()
    code, body = api("https://api.github.com/repos/%s/%s" % (owner, repo), token)
    if code in ("401", "403"):
        return None, None, ("GitHub не принял ключ доступа: он истёк или не даёт прав на этот "
                            "репозиторий. Обнови ключ (gh auth login) и повтори")
    if code == "404":
        if token:
            return None, None, ("репозиторий не найден: либо в ссылке опечатка, либо он приватный "
                                "и твой ключ GitHub не даёт к нему доступа")
        return None, None, ("репозиторий не найден. Если он приватный — нужен ключ доступа GitHub "
                            "(gh auth login или GITHUB_TOKEN); если публичный — проверь ссылку")
    if code != "200":
        return None, None, "GitHub ответил кодом %s — попробуй ещё раз чуть позже" % code

    try:
        meta = json.loads(body) or {}
    except Exception:
        meta = {}
    br = meta.get("default_branch") or "main"
    code, body = api("https://api.github.com/repos/%s/%s/contents/%s?ref=%s"
                     % (owner, repo, MANIFEST, br), token, raw=True)
    if code == "200" and body.strip():
        return br, body, None
    return None, None, None


def verdict(url):
    """Список причин отказа. Пустой список — можно ставить."""
    pair = parse_repo(url)
    if not pair:
        return ["это не ссылка на репозиторий GitHub — нужна ссылка вида "
                "https://github.com/<владелец>/<репозиторий>"], None
    owner, repo = pair
    branch, text, why = find_manifest(owner, repo)
    if why:
        return [why], None
    if not text:
        return ["в репозитории нет файла `%s` в корне. Это паспорт агента: без него "
                "витрина не знает, что ставит, и на какую полку класть. Возьми шаблон в "
                "extella-agent-standards/templates/%s" % (MANIFEST, MANIFEST)], None
    try:
        import yaml
    except ImportError:
        return ["нужен PyYAML, чтобы прочитать паспорт"], None
    try:
        doc = yaml.safe_load(text) or {}
    except Exception as exc:
        return ["паспорт не разбирается как YAML: %s" % str(exc)[:90]], None

    problems = []
    # Проверяем ТЕМ ЖЕ гейтом, что и свои паспорта: иначе у чужих будет другая планка.
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    try:
        import check_agent_passport as gate
        issues = gate.check_passport(doc) if hasattr(gate, "check_passport") else []
        for i in issues:
            if str(i.get("severity")) == "error":
                problems.append(i.get("message_ru") or i.get("code"))
    except Exception as exc:
        problems.append("не удалось прогнать гейт паспорта: %s" % str(exc)[:90])

    return problems, {"owner": owner, "repo": repo, "branch": branch,
                      "name": (doc.get("agent") or {}).get("name") or repo,
                      "goal": (doc.get("agent") or {}).get("business_goal") or ""}


def selftest():
    print("Самопроверка гейта репозитория:")
    ok = True

    def case(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond

    case("ссылка https разбирается",
         parse_repo("https://github.com/AnvarBakiyev/extella-1c-agent") == ("AnvarBakiyev", "extella-1c-agent"))
    case("ссылка с .git разбирается",
         parse_repo("https://github.com/a/b.git") == ("a", "b"))
    case("ссылка ssh разбирается", parse_repo("git@github.com:a/b.git") == ("a", "b"))
    case("чужой хост отвергнут", parse_repo("https://gitlab.com/a/b") is None)
    case("мусор отвергнут", parse_repo("просто текст") is None)
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("-")]
    if not args:
        print("Как пользоваться: python3 check_agent_repo.py https://github.com/<owner>/<repo>")
        return 2
    problems, info = verdict(args[0])
    if as_json:
        print(json.dumps({"ok": not problems, "problems": problems, "agent": info},
                         ensure_ascii=False))
        return 1 if problems else 0
    if problems:
        print("НЕЛЬЗЯ СТАВИТЬ:")
        for p in problems:
            print("  ✗ " + str(p))
        return 1
    print("МОЖНО СТАВИТЬ: %s" % info["name"])
    if info["goal"]:
        print("  что делает: %s" % info["goal"][:110])
    print("  источник: %s/%s, ветка %s" % (info["owner"], info["repo"], info["branch"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
