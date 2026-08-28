# -*- coding: utf-8 -*-
"""Обработчик полных языков: `cspl=c`, `cspl=go`, `cspl=rust`.

Второе семейство языков CSPL, и оно устроено ИНАЧЕ, чем узкие.

  · Узкий язык (`sql`, `slide`) безопасен грамматикой: опасное нельзя выразить.
    Такому языку можно доверить код, написанный моделью.
  · Полный язык (C, Go, Rust) грамматикой не ограничивает ничего. Он берётся
    ради скорости и доступа к железу, а безопасность даёт не язык, а то, что
    код ДОВЕРЕННЫЙ: его написал или проверил человек. Модель может подобрать
    такой эксперт из готовых, но не сочинять его на ходу без проверки.

Что всё-таки даёт CSPL полному языку: политика решает, какие языки вообще
разрешены на этом устройстве; исполнение идёт с пределом времени и объёма
ответа; результат снабжается отпечатком плана и квитанцией.

Общий договор, который делает несовместимые языки совместимыми: программа
читает JSON из стандартного ввода и пишет JSON в стандартный вывод. Больше
ничего от языка не требуется — поэтому в одном конвейере уживаются те, кто
друг друга вызвать не может.

Договор допускает ЛЮБОЙ правильный JSON, в том числе с пробелами после
двоеточий. Наивный поиск подстроки вида `"total":` на этом ломается молча и
возвращает нули вместо чисел (поймано на первом же прогоне конвейера
28.08.2026: звено на Rust отдало 0.00 при верных данных на входе). Правило:
в языке со стандартным разбором JSON пользоваться им, а без него — искать
ключ и пропускать пробелы, а не полагаться на точное написание.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from core import CSPLError, plan_hash

ЯЗЫКИ = {
    "c":    {"file": "main.c",  "compiler": "cc",
             "build": lambda исх, вых: ["cc", "-O2", "-o", str(вых), str(исх)]},
    "go":   {"file": "main.go", "compiler": "go",
             "build": lambda исх, вых: ["go", "build", "-o", str(вых), str(исх)]},
    "rust": {"file": "main.rs", "compiler": "rustc",
             "build": lambda исх, вых: ["rustc", "-O", "-o", str(вых), str(исх)]},
}

DEFAULT_POLICY = {
    "schemaVersion": "cspl-native-policy/v1",
    "profile": "compute",
    "capabilities": {"native.run": True},
    "scope": {"environments": ["test", "development", "copy", "production"],
              "allowedLanguages": ["c"],          # по умолчанию только C
              "buildTimeoutSeconds": 60,
              "runTimeoutSeconds": 10,
              "maxOutputBytes": 1_000_000},
    "approval": {"development": "none"},
}


def доступные(policy: dict | None = None) -> dict[str, bool]:
    """Какие языки реально можно исполнить здесь и сейчас."""
    разрешённые = (policy or DEFAULT_POLICY)["scope"].get("allowedLanguages", [])
    return {имя: bool(shutil.which(данные["compiler"])) and имя in разрешённые
            for имя, данные in ЯЗЫКИ.items()}


def run_expert(language: str, source: str, payload: dict | None = None,
               policy: dict | None = None) -> dict:
    """Собрать и выполнить эксперта на полном языке. Вход и выход — JSON."""
    политика = policy or DEFAULT_POLICY
    охват = политика["scope"]
    начало = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not политика["capabilities"].get("native.run", False):
        return {"ok": False, "error": {"code": "POLICY_DENIED",
                                       "message": "Политика не даёт право native.run"}}
    if language not in ЯЗЫКИ:
        return {"ok": False, "error": {"code": "SCHEMA_REJECTED",
                                       "message": f"Язык {language} не поддерживается обработчиком"}}
    if language not in охват.get("allowedLanguages", []):
        return {"ok": False, "error": {"code": "POLICY_DENIED",
                                       "message": f"Язык {language} не разрешён политикой устройства"}}
    рецепт = ЯЗЫКИ[language]
    if not shutil.which(рецепт["compiler"]):
        return {"ok": False,
                "error": {"code": "TOOLCHAIN_MISSING",
                          "message": f"На устройстве нет {рецепт['compiler']} — "
                                     f"эксперт на {language} здесь не исполнить"}}

    вход = json.dumps(payload or {}, ensure_ascii=False)
    план = {"language": language, "sourceSha": plan_hash({"src": source}),
            "inputSha": plan_hash({"in": вход}),
            "limits": {"build": охват.get("buildTimeoutSeconds", 60),
                       "run": охват.get("runTimeoutSeconds", 10)}}
    отпечаток = plan_hash(план)

    with tempfile.TemporaryDirectory() as врем:
        каталог = Path(врем)
        исходник = каталог / рецепт["file"]
        исходник.write_text(source, encoding="utf-8")
        двоичный = каталог / "prog"
        собран = time.time()
        try:
            сборка = subprocess.run(рецепт["build"](исходник, двоичный),
                                    capture_output=True, text=True, cwd=каталог,
                                    timeout=охват.get("buildTimeoutSeconds", 60),
                                    env={**os.environ, "GOFLAGS": "-mod=mod",
                                         "GOCACHE": str(каталог / ".gocache")})
        except subprocess.TimeoutExpired:
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "BUILD_TIMEOUT", "message": "Сборка не уложилась в предел"}}
        if сборка.returncode != 0:
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "BUILD_FAILED",
                              "message": (сборка.stderr or сборка.stdout)[:400]}}
        сборка_сек = round(time.time() - собран, 2)

        пуск = time.time()
        try:
            прогон = subprocess.run([str(двоичный)], input=вход, capture_output=True,
                                    text=True, cwd=каталог,
                                    timeout=охват.get("runTimeoutSeconds", 10))
        except subprocess.TimeoutExpired:
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "RUN_TIMEOUT", "message": "Программа не уложилась в предел"}}
        if прогон.returncode != 0:
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "RUN_FAILED", "message": (прогон.stderr or "")[:400]}}
        вывод = прогон.stdout or ""
        if len(вывод.encode("utf-8")) > охват.get("maxOutputBytes", 1_000_000):
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "OUTPUT_TOO_LARGE", "message": "Ответ больше разрешённого"}}
        try:
            данные = json.loads(вывод or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "planHash": отпечаток,
                    "error": {"code": "CONTRACT_BROKEN",
                              "message": "Программа обязана писать JSON в стандартный вывод"}}

    return {"ok": True, "language": language, "planHash": отпечаток, "result": данные,
            "receipt": {"startedAt": начало,
                        "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "executed": True, "verified": True,
                        "buildSeconds": сборка_сек,
                        "runSeconds": round(time.time() - пуск, 3),
                        "policyProfile": политика.get("profile")}}
