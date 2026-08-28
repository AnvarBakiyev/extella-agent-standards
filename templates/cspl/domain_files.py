# -*- coding: utf-8 -*-
"""Домен «файлы» для CSPL: чтение, выгрузка и запись под политикой клиента.

Показывает цену нового домена: реестр операций, адаптеры и политика по
умолчанию. Всё остальное — фазы, отпечаток плана, согласования, квитанции —
берётся из ядра и не пишется заново.

Главное правило домена: работа идёт ТОЛЬКО внутри корней, разрешённых
политикой. Путь проверяется после развёртывания, поэтому «..» и ссылка наружу
не проходят — это первое, что пробуют, когда дают машине доступ к диску.
"""
from __future__ import annotations

import pathlib
import shutil

from core import CSPLError, Domain, Operation

OPERATIONS = {
    "fs.list":      Operation("read", "fs.read", True,
                              input_fields=frozenset({"path"})),
    "fs.stat":      Operation("read", "fs.read", True,
                              input_fields=frozenset({"path"}),
                              required_input_fields=frozenset({"path"})),
    "fs.read_text": Operation("read", "fs.read", True,
                              input_fields=frozenset({"path", "maxBytes"}),
                              required_input_fields=frozenset({"path"})),
    "fs.export":    Operation("export", "fs.export", True,
                              input_fields=frozenset({"path", "to"}),
                              required_input_fields=frozenset({"path", "to"})),
    "fs.write_text": Operation("write", "fs.write", True,
                               input_fields=frozenset({"path", "text"}),
                               required_input_fields=frozenset({"path", "text"})),
    "fs.delete":    Operation("delete", "fs.delete", False),   # объявлена, но не делается
}

DEFAULT_POLICY = {
    "schemaVersion": "cspl-files-policy/v1",
    "profile": "reader",
    "capabilities": {"fs.read": True, "fs.export": True,
                     "fs.write": False, "fs.delete": False},
    "scope": {"environments": ["test", "development", "copy", "production"],
              "allowedRoots": [],          # пусто = ничего не разрешено
              "maxBytes": 1_000_000,
              "maxFiles": 200},
    "approval": {"read": "none", "export": "none",
                 "write": "always", "delete": "disabled"},
}


def _корни(policy: dict) -> list[pathlib.Path]:
    корни = policy.get("scope", {}).get("allowedRoots") or []
    return [pathlib.Path(к).expanduser().resolve() for к in корни]


def _внутри(путь: str, policy: dict) -> pathlib.Path:
    """Развернуть путь и убедиться, что он в разрешённом корне."""
    цель = pathlib.Path(путь).expanduser()
    try:
        цель = цель.resolve()
    except OSError as беда:
        raise CSPLError("SCOPE_DENIED", f"Путь не разбирается: {беда}") from беда
    корни = _корни(policy)
    if not корни:
        raise CSPLError("SCOPE_DENIED", "Политика не называет ни одного разрешённого корня")
    for корень in корни:
        if цель == корень or корень in цель.parents:
            return цель
    raise CSPLError("SCOPE_DENIED", "Путь вне разрешённых корней")


def _проверить_вход(operation: str, вход: dict, policy: dict) -> None:
    """Домен уточняет правила: пути проверяются ещё на этапе плана."""
    if "path" in вход:
        _внутри(вход["path"], policy)
    if "to" in вход:
        _внутри(вход["to"], policy)


def _список(plan: dict, policy: dict) -> dict:
    корень = _внутри(plan["input"].get("path") or str(_корни(policy)[0]), policy)
    предел = policy["scope"].get("maxFiles", 200)
    записи = []
    for п in sorted(корень.iterdir())[:предел]:
        записи.append({"name": п.name, "isDir": п.is_dir(),
                       "bytes": п.stat().st_size if п.is_file() else None})
    return {"path": str(корень), "entries": записи, "truncated": len(записи) >= предел}


def _сведения(plan: dict, policy: dict) -> dict:
    цель = _внутри(plan["input"]["path"], policy)
    с = цель.stat()
    return {"path": str(цель), "bytes": с.st_size, "isDir": цель.is_dir(),
            "modified": int(с.st_mtime)}


def _прочитать(plan: dict, policy: dict) -> dict:
    цель = _внутри(plan["input"]["path"], policy)
    предел = min(int(plan["input"].get("maxBytes") or policy["scope"]["maxBytes"]),
                 policy["scope"]["maxBytes"])
    данные = цель.read_bytes()[:предел]
    return {"path": str(цель), "bytes": len(данные), "truncated": цель.stat().st_size > предел,
            "text": данные.decode("utf-8", errors="replace")}


def _выгрузить(plan: dict, policy: dict) -> dict:
    откуда = _внутри(plan["input"]["path"], policy)
    куда = _внутри(plan["input"]["to"], policy)
    куда.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(откуда, куда)
    return {"from": str(откуда), "to": str(куда), "bytes": куда.stat().st_size}


def _записать(plan: dict, policy: dict) -> dict:
    цель = _внутри(plan["input"]["path"], policy)
    текст = plan["input"]["text"]
    if len(текст.encode("utf-8")) > policy["scope"]["maxBytes"]:
        raise CSPLError("SCOPE_DENIED", "Текст больше разрешённого размера")
    цель.parent.mkdir(parents=True, exist_ok=True)
    цель.write_text(текст, encoding="utf-8")
    return {"path": str(цель), "bytes": цель.stat().st_size}


ADAPTERS = {"fs.list": _список, "fs.stat": _сведения, "fs.read_text": _прочитать,
            "fs.export": _выгрузить, "fs.write_text": _записать}

FILES = Domain(name="files", operations=OPERATIONS, adapters=ADAPTERS,
               default_policy=DEFAULT_POLICY, check_input=_проверить_вход)
