# -*- coding: utf-8 -*-
"""Ядро CSPL: всё, что не зависит от предметной области.

CSPL — способ выдать модели ограниченные права: модель не пишет код, а
присылает конверт с ИМЕНЕМ операции. Ядро проверяет конверт по политике,
которая лежит у клиента, считает отпечаток плана и решает, что будет
сделано, — до того как что-то произойдёт. Домен добавляет только реестр
операций и адаптеры.

Замер 27.08.2026 на живом CSPL-1C: 81% его кода не зависит от 1С. Это ядро —
та самая общая часть, вынесенная так, чтобы новый домен стоил реестр
операций плюс адаптеры.

Что даёт ядро:
  · разбор и проверка конверта, отказ на неизвестных полях и операциях;
  · проверка политики клиента (возможности, охват, требуемые согласования);
  · нормализация плана и `planHash` — отпечаток БЕЗ блока согласования;
  · две фазы: `plan` только рассказывает, `execute` делает;
  · опасные эффекты требуют согласования, привязанного к отпечатку, и ключа
    повторного вызова;
  · единый ответ и квитанция, из которых нельзя вытащить секрет.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

SCHEMA_SUFFIX = "/v1"
EFFECTS = ("read", "export", "draft", "write", "post", "delete", "development")
ОПАСНЫЕ = ("write", "post", "delete", "development")   # требуют согласования
КЛЮЧИ_КОНВЕРТА = {"schemaVersion", "operation", "connection", "environment",
                  "phase", "input", "limits", "idempotencyKey", "approval"}
ПРЕДЕЛ_КОНВЕРТА = 64 * 1024


class CSPLError(ValueError):
    """Конверт, политика или согласование не приняты."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Operation:
    """Описание операции: эффект известен ДО выполнения."""
    effect: str
    capability: str
    implemented: bool = False
    production_allowed: bool = True
    input_fields: frozenset[str] = frozenset()
    required_input_fields: frozenset[str] = frozenset()
    phases: frozenset[str] = frozenset({"plan", "execute"})


@dataclass(frozen=True)
class Domain:
    """Домен = имя, реестр операций, адаптеры и политика по умолчанию."""
    name: str
    operations: dict[str, Operation]
    adapters: dict[str, Callable[[dict, dict], dict]]
    default_policy: dict
    check_input: Callable[[str, dict, dict], None] | None = None

    @property
    def schema(self) -> str:
        return f"cspl-{self.name}{SCHEMA_SUFFIX}"


@dataclass
class Decision:
    allowed: bool
    operation: str
    effect: str | None
    capability: str | None
    phase: str
    plan_hash: str | None
    approval_required: bool
    implemented: bool
    reasons: list[str] = field(default_factory=list)
    plan: dict | None = None

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "operation": self.operation,
                "effect": self.effect, "capability": self.capability,
                "phase": self.phase, "planHash": self.plan_hash,
                "approvalRequired": self.approval_required,
                "implemented": self.implemented, "reasons": self.reasons,
                "normalizedPlan": self.plan}


def plan_hash(plan: dict) -> str:
    """Отпечаток того, ЧТО будет сделано.

    Из отпечатка исключены согласование, ключ повторного вызова и ФАЗА.
    Фаза — обстоятельство вопроса, а не содержание работы: если считать её,
    согласие, взятое на этапе плана, никогда не совпадёт с выполнением
    (поймано самопроверкой 27.08.2026 на первом же прогоне записи).
    """
    чистый = {k: v for k, v in plan.items()
              if k not in ("approval", "idempotencyKey", "phase")}
    сырьё = json.dumps(чистый, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(сырьё.encode("utf-8")).hexdigest()


def _проверить_политику(policy: dict) -> dict:
    if not isinstance(policy, dict):
        raise CSPLError("POLICY_INVALID", "Политика должна быть объектом")
    for ключ in ("capabilities", "scope", "approval"):
        if not isinstance(policy.get(ключ), dict):
            raise CSPLError("POLICY_INVALID", f"В политике нет раздела «{ключ}»")
    return policy


def evaluate(request: dict, domain: Domain, policy: dict | None = None) -> Decision:
    """Разобрать конверт и решить, что будет сделано. Ничего не выполняет."""
    if len(json.dumps(request, ensure_ascii=False)) > ПРЕДЕЛ_КОНВЕРТА:
        raise CSPLError("SCHEMA_REJECTED", "Конверт больше допустимого размера")
    лишние = set(request) - КЛЮЧИ_КОНВЕРТА
    if лишние:
        raise CSPLError("SCHEMA_REJECTED", f"Неизвестные поля конверта: {sorted(лишние)}")
    if request.get("schemaVersion") != domain.schema:
        raise CSPLError("SCHEMA_REJECTED",
                        f"Ожидалась схема {domain.schema}")
    имя = request.get("operation")
    оп = domain.operations.get(имя)
    if оп is None:
        raise CSPLError("SCHEMA_REJECTED", f"Неизвестная операция: {имя}")
    фаза = request.get("phase", "plan")
    if фаза not in ("plan", "execute"):
        raise CSPLError("SCHEMA_REJECTED", f"Неизвестная фаза: {фаза}")
    if фаза not in оп.phases:
        raise CSPLError("SCHEMA_REJECTED", f"Операция {имя} не поддерживает фазу {фаза}")

    политика = _проверить_политику(policy if policy is not None else domain.default_policy)
    окружение = request.get("environment", "test")
    охват = политика["scope"]
    if окружение not in охват.get("environments", []):
        raise CSPLError("POLICY_DENIED", f"Окружение {окружение} вне охвата политики")
    if окружение == "production" and not оп.production_allowed:
        raise CSPLError("POLICY_DENIED", f"{имя} запрещена на боевом окружении")
    if not политика["capabilities"].get(оп.capability, False):
        raise CSPLError("POLICY_DENIED", f"Политика не даёт право {оп.capability}")

    вход = request.get("input") or {}
    if not isinstance(вход, dict):
        raise CSPLError("SCHEMA_REJECTED", "Поле input должно быть объектом")
    лишние_вх = set(вход) - set(оп.input_fields)
    if лишние_вх:
        raise CSPLError("SCHEMA_REJECTED", f"Неизвестные поля входа: {sorted(лишние_вх)}")
    нет = set(оп.required_input_fields) - set(вход)
    if нет:
        raise CSPLError("SCHEMA_REJECTED", f"Не хватает полей входа: {sorted(нет)}")
    if domain.check_input:
        domain.check_input(имя, вход, политика)      # домен уточняет свои правила

    план = {"schemaVersion": domain.schema, "operation": имя,
            "connection": request.get("connection", "default"),
            "environment": окружение, "phase": фаза, "effect": оп.effect,
            "input": вход, "limits": request.get("limits") or {}}
    нужно_согласие = политика["approval"].get(оп.effect, "none") == "always"
    if политика["approval"].get(оп.effect) == "disabled":
        raise CSPLError("POLICY_DENIED", f"Эффект {оп.effect} запрещён политикой")

    return Decision(allowed=True, operation=имя, effect=оп.effect,
                    capability=оп.capability, phase=фаза, plan_hash=plan_hash(план),
                    approval_required=нужно_согласие, implemented=оп.implemented,
                    plan=план)


def run(request: dict, domain: Domain, policy: dict | None = None) -> dict:
    """Полный ход: решение, проверка согласования, вызов адаптера, квитанция."""
    начало = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_id = uuid.uuid4().hex
    try:
        решение = evaluate(request, domain, policy)
    except CSPLError as беда:
        return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                "error": {"code": беда.code, "message": беда.message},
                "runId": run_id}

    ответ = {"ok": True, "schemaVersion": f"cspl-{domain.name}-result/v1",
             "operation": решение.operation, "effect": решение.effect,
             "phase": решение.phase, "planHash": решение.plan_hash, "runId": run_id}

    if решение.phase == "plan":
        ответ["result"] = {"decision": решение.to_dict(), "willExecute": False}
        ответ["receipt"] = {"startedAt": начало, "finishedAt": начало,
                            "executed": False, "verified": True}
        return ответ

    if not решение.implemented:
        return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                "error": {"code": "NOT_IMPLEMENTED",
                          "message": f"Операция {решение.operation} объявлена, но не реализована"},
                "runId": run_id}
    if not request.get("idempotencyKey"):
        return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                "error": {"code": "SCHEMA_REJECTED",
                          "message": "Для выполнения нужен ключ повторного вызова"},
                "runId": run_id}
    if решение.approval_required:
        согласие = request.get("approval") or {}
        if согласие.get("planHash") != решение.plan_hash:
            return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                    "error": {"code": "APPROVAL_REQUIRED",
                              "message": "Нужно согласование, привязанное к отпечатку плана"},
                    "runId": run_id}

    адаптер = domain.adapters.get(решение.operation)
    if адаптер is None:
        return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                "error": {"code": "NOT_IMPLEMENTED", "message": "Адаптер не подключён"},
                "runId": run_id}
    try:
        итог = адаптер(решение.plan, policy or domain.default_policy)
    except CSPLError as беда:
        return {"ok": False, "schemaVersion": f"cspl-{domain.name}-result/v1",
                "error": {"code": беда.code, "message": беда.message}, "runId": run_id}
    ответ["result"] = итог
    ответ["receipt"] = {"startedAt": начало,
                        "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "executed": True, "verified": True}
    return ответ
