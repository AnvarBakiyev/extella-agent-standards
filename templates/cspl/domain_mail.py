# -*- coding: utf-8 -*-
"""Домен «почта» для CSPL: агент готовит письма, отправляет человек.

Второй домен на том же ядре — им проверяется, что цена расширения
действительно в реестре операций и адаптерах, а не в переписывании каркаса.

Канон Extella: письма и любая внешняя запись — только черновики, отправляет
человек. Здесь это не пожелание в инструкции агента, а устройство домена:
`mail.send` объявлена, но политикой по умолчанию ЗАПРЕЩЕНА (`disabled`), и
включить её может только клиент у себя, своей политикой. Модель не может
попросить себе это право — политика в промпт не входит.
"""
from __future__ import annotations

import email.utils
import json
import pathlib
import re
import time

from core import CSPLError, Domain, Operation

АДРЕС = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

OPERATIONS = {
    "mail.list_drafts": Operation("read", "mail.read", True),
    "mail.get_draft":   Operation("read", "mail.read", True,
                                  input_fields=frozenset({"id"}),
                                  required_input_fields=frozenset({"id"})),
    "mail.draft":       Operation("draft", "mail.draft", True,
                                  input_fields=frozenset({"to", "subject", "body", "replyTo"}),
                                  required_input_fields=frozenset({"to", "subject", "body"})),
    "mail.export":      Operation("export", "mail.export", True,
                                  input_fields=frozenset({"id", "to"}),
                                  required_input_fields=frozenset({"id", "to"})),
    # Отправка объявлена, чтобы отказ был честным и понятным, а не «нет такой
    # операции». Реализации адаптера здесь нет намеренно.
    "mail.send":        Operation("post", "mail.send", False),
}

DEFAULT_POLICY = {
    "schemaVersion": "cspl-mail-policy/v1",
    "profile": "negotiator",
    "capabilities": {"mail.read": True, "mail.draft": True,
                     "mail.export": True, "mail.send": False},
    "scope": {"environments": ["test", "development", "copy", "production"],
              "draftsDir": "",              # пусто = домен работать не будет
              "allowedRecipients": [],      # пусто = кому угодно из проверенных адресов
              "maxBodyChars": 20_000,
              "maxDrafts": 500},
    "approval": {"read": "none", "draft": "none",
                 "export": "always", "post": "disabled"},
}


def _папка(policy: dict) -> pathlib.Path:
    путь = (policy.get("scope") or {}).get("draftsDir") or ""
    if not путь:
        raise CSPLError("SCOPE_DENIED", "Политика не называет папку черновиков")
    п = pathlib.Path(путь).expanduser().resolve()
    п.mkdir(parents=True, exist_ok=True)
    return п


def _проверить_вход(operation: str, вход: dict, policy: dict) -> None:
    охват = policy.get("scope") or {}
    if "to" in вход and operation != "mail.export":
        адреса = вход["to"] if isinstance(вход["to"], list) else [вход["to"]]
        разрешённые = охват.get("allowedRecipients") or []
        for адрес in адреса:
            if not isinstance(адрес, str) or not АДРЕС.fullmatch(адрес):
                raise CSPLError("SCHEMA_REJECTED", f"Непохоже на адрес: {адрес!r}")
            if разрешённые and адрес not in разрешённые:
                raise CSPLError("SCOPE_DENIED", f"Адресат вне списка политики: {адрес}")
    if "body" in вход and len(вход["body"]) > охват.get("maxBodyChars", 20_000):
        raise CSPLError("SCOPE_DENIED", "Письмо длиннее разрешённого политикой")
    if "id" in вход and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(вход["id"])):
        raise CSPLError("SCHEMA_REJECTED", "Недопустимый идентификатор черновика")


def _список(plan: dict, policy: dict) -> dict:
    папка = _папка(policy)
    черновики = []
    for ф in sorted(папка.glob("*.json"))[: policy["scope"].get("maxDrafts", 500)]:
        данные = json.loads(ф.read_text(encoding="utf-8"))
        черновики.append({"id": ф.stem, "to": данные.get("to"),
                          "subject": данные.get("subject"),
                          "createdAt": данные.get("createdAt")})
    return {"drafts": черновики, "count": len(черновики)}


def _взять(plan: dict, policy: dict) -> dict:
    ф = _папка(policy) / f"{plan['input']['id']}.json"
    if not ф.exists():
        raise CSPLError("NOT_FOUND", "Черновик не найден")
    return {"draft": json.loads(ф.read_text(encoding="utf-8"))}


def _черновик(plan: dict, policy: dict) -> dict:
    вход = plan["input"]
    адреса = вход["to"] if isinstance(вход["to"], list) else [вход["to"]]
    ид = f"d{int(time.time()*1000):x}"
    письмо = {"id": ид, "to": адреса, "subject": вход["subject"], "body": вход["body"],
              "replyTo": вход.get("replyTo"), "createdAt": email.utils.formatdate(usegmt=True),
              "status": "draft"}
    (_папка(policy) / f"{ид}.json").write_text(
        json.dumps(письмо, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"id": ид, "status": "draft",
            "note": "Письмо сохранено черновиком. Отправляет человек."}


def _выгрузить(plan: dict, policy: dict) -> dict:
    ф = _папка(policy) / f"{plan['input']['id']}.json"
    if not ф.exists():
        raise CSPLError("NOT_FOUND", "Черновик не найден")
    письмо = json.loads(ф.read_text(encoding="utf-8"))
    куда = pathlib.Path(plan["input"]["to"]).expanduser().resolve()
    if _папка(policy) not in куда.parents and куда.parent != _папка(policy):
        raise CSPLError("SCOPE_DENIED", "Выгрузка только внутрь папки черновиков")
    куда.write_text(
        f"Кому: {', '.join(письмо['to'])}\nТема: {письмо['subject']}\n\n{письмо['body']}\n",
        encoding="utf-8")
    return {"id": письмо["id"], "file": str(куда), "bytes": куда.stat().st_size}


ADAPTERS = {"mail.list_drafts": _список, "mail.get_draft": _взять,
            "mail.draft": _черновик, "mail.export": _выгрузить}

MAIL = Domain(name="mail", operations=OPERATIONS, adapters=ADAPTERS,
              default_policy=DEFAULT_POLICY, check_input=_проверить_вход)
