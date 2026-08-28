# -*- coding: utf-8 -*-
"""Показ свойства класса: меняется ОБРАБОТЧИК — меняются все эксперты сразу."""
from __future__ import annotations
import copy, sqlite3, tempfile, pathlib
from handler_sql import run_expert, DEFAULT_POLICY

# Три «эксперта». Исходник каждого — запрос, а не программа.
ЭКСПЕРТЫ = {
    "должники":      "SELECT name, phone, amount FROM clients WHERE amount > 0 ORDER BY amount DESC",
    "все_клиенты":   "SELECT name, phone FROM clients",
    "сумма_долга":   "SELECT SUM(amount) AS итого FROM clients",
    "опасный":       "UPDATE clients SET amount = 0",
}

with tempfile.TemporaryDirectory() as врем:
    база = str(pathlib.Path(врем) / "клиенты.db")
    с = sqlite3.connect(база)
    с.execute("CREATE TABLE clients (name TEXT, phone TEXT, amount REAL)")
    с.executemany("INSERT INTO clients VALUES (?,?,?)", [
        ("ТОО Астра", "+7 701 111 2233", 1250000),
        ("ИП Ким",    "+7 707 222 3344", 340000),
        ("ТОО Байт",  "+7 747 333 4455", 90000),
        ("ТОО Ноль",  "+7 700 444 5566", 0)])
    с.commit(); с.close()

    def прогон(заголовок, политика):
        print(f"\n=== {заголовок} ===")
        for имя, исходник in ЭКСПЕРТЫ.items():
            о = run_expert(исходник, {}, база, политика)
            if not о.get("ok"):
                print(f"  {имя:14} ОТКАЗ {о['error']['code']}: {о['error']['message'][:52]}")
                continue
            р = о["result"]
            первая = р["rows"][0] if р["rows"] else {}
            print(f"  {имя:14} строк {р['count']}{' (урезано)' if р['truncated'] else ''}"
                  f"  первая: {первая}")

    базовая = copy.deepcopy(DEFAULT_POLICY)
    прогон("обработчик как есть", базовая)

    # ЕДИНСТВЕННОЕ изменение: правим обработчик через его политику класса.
    новая = copy.deepcopy(DEFAULT_POLICY)
    новая["scope"]["maxRows"] = 2
    новая["scope"]["maskColumns"] = ["phone"]
    прогон("тот же класс после правки обработчика (лимит 2, телефон скрыт)", новая)

    print("\nНи один эксперт не переписан — изменился только обработчик класса.")
