# -*- coding: utf-8 -*-
"""Самопроверка языка sql: грамматика, политика класса и устойчивость отпечатка."""
from __future__ import annotations
import copy, sqlite3, tempfile, pathlib
from handler_sql import run_expert, DEFAULT_POLICY

ошибки: list[str] = []

def проба(имя, о, ждём_ok, ждём_код=None, ещё=None):
    ok, код = о.get("ok"), (о.get("error") or {}).get("code")
    хорошо = (ok == ждём_ok) and (ждём_код is None or код == ждём_код)
    if хорошо and ещё: хорошо = ещё(о)
    if not хорошо: ошибки.append(f"{имя}: ok={ok} код={код}")
    print(f"  {'✓' if хорошо else '✗'} {имя:44} ok={str(ok):5} {код or ''}")
    return о

with tempfile.TemporaryDirectory() as врем:
    база = str(pathlib.Path(врем) / "б.db")
    с = sqlite3.connect(база)
    с.execute("CREATE TABLE clients (name TEXT, phone TEXT, amount REAL)")
    с.execute("CREATE TABLE secrets (token TEXT)")
    с.executemany("INSERT INTO clients VALUES (?,?,?)",
                  [("А","+7 700 111 2233",10),("Б","+7 700 222 3344",20),("В","+7 700 333 4455",30)])
    с.execute("INSERT INTO secrets VALUES ('очень-секретно')")
    с.commit(); с.close()
    П = copy.deepcopy(DEFAULT_POLICY)

    print("── грамматика: опасное невыразимо ──")
    проба("чтение", run_expert("SELECT name FROM clients", {}, база, П), True)
    проба("UPDATE",  run_expert("UPDATE clients SET amount=0", {}, база, П), False, "SCHEMA_REJECTED")
    проба("DROP в конце",
          run_expert("SELECT 1 FROM clients; DROP TABLE clients", {}, база, П), False, "SCHEMA_REJECTED")
    проба("PRAGMA", run_expert("SELECT 1 FROM clients WHERE 1=1 -- PRAGMA x", {}, база, П),
          False, "SCHEMA_REJECTED")
    проба("пустой исходник", run_expert("", {}, база, П), False, "SCHEMA_REJECTED")

    print("── политика класса ──")
    узкая = copy.deepcopy(П); узкая["scope"]["allowedTables"] = ["clients"]
    проба("своя таблица", run_expert("SELECT name FROM clients", {}, база, узкая), True)
    проба("чужая таблица", run_expert("SELECT token FROM secrets", {}, база, узкая),
          False, "SCOPE_DENIED")
    предел = copy.deepcopy(П); предел["scope"]["maxRows"] = 2
    проба("предел строк", run_expert("SELECT name FROM clients", {}, база, предел), True,
          ещё=lambda о: о["result"]["count"] == 2 and о["result"]["truncated"])
    маска = copy.deepcopy(П); маска["scope"]["maskColumns"] = ["phone"]
    проба("маскирование колонки", run_expert("SELECT phone FROM clients", {}, база, маска), True,
          ещё=lambda о: о["result"]["rows"][0]["phone"].startswith("…"))
    без = copy.deepcopy(П); без["capabilities"]["sql.read"] = False
    проба("право отозвано", run_expert("SELECT 1 FROM clients", {}, база, без), False, "POLICY_DENIED")

    print("── отпечаток плана ──")
    а = run_expert("SELECT name FROM clients", {}, база, П)
    б = run_expert("SELECT name FROM clients", {}, база, П)
    в = run_expert("SELECT phone FROM clients", {}, база, П)
    одинаковые = а["planHash"] == б["planHash"]
    разные = а["planHash"] != в["planHash"]
    print(f"  {'✓' if одинаковые else '✗'} одинаковый запрос — одинаковый отпечаток")
    print(f"  {'✓' if разные else '✗'} другой запрос — другой отпечаток")
    if not (одинаковые and разные): ошибки.append("отпечаток плана ведёт себя неверно")

print()
print("САМОПРОВЕРКА SQL:", "провалена — " + "; ".join(ошибки) if ошибки else "пройдена")
raise SystemExit(1 if ошибки else 0)
