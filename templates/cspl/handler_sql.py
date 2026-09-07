# -*- coding: utf-8 -*-
"""Обработчик языка `cspl=sql`: исходник эксперта — запрос, а не программа.

Показывает вторую форму CSPL. Первая — протокол намерений (`one_c`, `files`,
`mail`): модель называет операцию. Вторая — ЯЗЫК: исходником эксперта служит
текст на узком языке, а обработчик решает, как его исполнить.

Зачем узкий язык. Пока агент пишет питон, ему разрешено всё, и опасное ловят
проверками. Когда агент пишет запрос на языке, где нет записи, запрещать нечего:
**опасное невозможно выразить**. Грамматика дешевле любой политики.

Свойство, ради которого это и делается: обработчик один на весь класс. Меняешь
обработчик — меняются ВСЕ эксперты этого класса, ни один из них не переписан.
Это проверяется прогоном `demo_sql.py`.
"""
from __future__ import annotations

import re
import sqlite3
import time

from core import CSPLError, plan_hash

ЧИТАЮЩИЙ = re.compile(r"^\s*(?:SELECT|WITH|ВЫБРАТЬ)\b", re.IGNORECASE)
ЗАПРЕЩЁННОЕ = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE)
НЕСКОЛЬКО = re.compile(r";\s*\S")          # два запроса в одном исходнике

DEFAULT_POLICY = {
    "schemaVersion": "cspl-sql-policy/v1",
    "profile": "analyst",
    "capabilities": {"sql.read": True},
    "scope": {
        "environments": ["test", "development", "copy", "production"],
        "allowedTables": [],        # пусто = любые таблицы базы
        "maxRows": 100,
        "timeoutSeconds": 5,
        "maskColumns": [],          # колонки, которые никогда не показываются целиком
    },
    "approval": {"read": "none"},
}


def _проверить_язык(source: str, policy: dict) -> str:
    """Грамматика: запрос обязан быть читающим и одним."""
    текст = (source or "").strip()
    if not текст:
        raise CSPLError("SCHEMA_REJECTED", "Пустой исходник")
    if not ЧИТАЮЩИЙ.match(текст):
        raise CSPLError("SCHEMA_REJECTED", "Язык sql допускает только читающий запрос")
    запрет = ЗАПРЕЩЁННОЕ.search(текст)
    if запрет:
        raise CSPLError("SCHEMA_REJECTED",
                        f"Слово {запрет.group(1).upper()} в этом языке отсутствует")
    if НЕСКОЛЬКО.search(текст.rstrip().rstrip(";")):
        raise CSPLError("SCHEMA_REJECTED", "Один эксперт — один запрос")
    разрешённые = policy["scope"].get("allowedTables") or []
    if разрешённые:
        названные = set(re.findall(r"(?:FROM|JOIN)\s+([A-Za-zА-Яа-я_][\w]*)", текст, re.I))
        чужие = названные - set(разрешённые)
        if чужие:
            raise CSPLError("SCOPE_DENIED", f"Таблицы вне политики: {sorted(чужие)}")
    return текст.rstrip().rstrip(";")


def _замаскировать(строки: list[dict], policy: dict) -> list[dict]:
    скрытые = {к.lower() for к in policy["scope"].get("maskColumns") or []}
    if not скрытые:
        return строки
    итог = []
    for строка in строки:
        копия = {}
        for имя, значение in строка.items():
            if имя.lower() in скрытые and значение is not None:
                хвост = str(значение)[-2:]
                копия[имя] = "…" + хвост
            else:
                копия[имя] = значение
        итог.append(копия)
    return итог


def run_expert(source: str, params: dict | None, database: str,
               policy: dict | None = None) -> dict:
    """Исполнить эксперта, написанного на языке sql."""
    политика = policy or DEFAULT_POLICY
    начало = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not политика["capabilities"].get("sql.read", False):
        return {"ok": False, "error": {"code": "POLICY_DENIED",
                                       "message": "Политика не даёт право sql.read"}}
    try:
        запрос = _проверить_язык(source, политика)
    except CSPLError as беда:
        return {"ok": False, "error": {"code": беда.code, "message": беда.message}}

    предел = int(политика["scope"].get("maxRows", 100))
    план = {"language": "sql", "query": запрос, "params": params or {},
            "limits": {"maxRows": предел,
                       "timeoutSeconds": политика["scope"].get("timeoutSeconds", 5)}}
    отпечаток = plan_hash(план)

    связь = sqlite3.connect(database)
    связь.row_factory = sqlite3.Row
    try:
        # Читающий режим на уровне соединения — вторая линия после грамматики.
        связь.execute("PRAGMA query_only = ON")
        курсор = связь.execute(запрос, params or {})
        сырьё = [dict(строка) for строка in курсор.fetchmany(предел + 1)]
    except sqlite3.Error as беда:
        return {"ok": False, "error": {"code": "ADAPTER_FAILED", "message": str(беда)[:160]},
                "planHash": отпечаток}
    finally:
        связь.close()

    урезано = len(сырьё) > предел
    строки = _замаскировать(сырьё[:предел], политика)
    return {"ok": True, "language": "sql", "planHash": отпечаток,
            "result": {"rows": строки, "count": len(строки), "truncated": урезано},
            "receipt": {"startedAt": начало,
                        "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "executed": True, "verified": True,
                        "policyProfile": политика.get("profile")}}
