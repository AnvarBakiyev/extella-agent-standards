# -*- coding: utf-8 -*-
"""Самопроверка домена «почта»: черновик можно, отправку — нельзя."""
from __future__ import annotations
import copy, tempfile
from core import run
from domain_mail import MAIL, DEFAULT_POLICY

ошибки: list[str] = []

def конверт(op, **поля):
    к = {"schemaVersion": MAIL.schema, "operation": op, "connection": "default",
         "environment": "production", "phase": "plan", "input": {}, "limits": {}}
    к.update(поля); return к

def проба(имя, ответ, ждём_ok, ждём_код=None):
    ok, код = ответ.get("ok"), (ответ.get("error") or {}).get("code")
    хорошо = (ok == ждём_ok) and (ждём_код is None or код == ждём_код)
    if not хорошо: ошибки.append(f"{имя}: ok={ok} код={код}")
    print(f"  {'✓' if хорошо else '✗'} {имя:46} ok={str(ok):5} {код or ''}")
    return ответ

with tempfile.TemporaryDirectory() as врем:
    политика = copy.deepcopy(DEFAULT_POLICY)
    политика["scope"]["draftsDir"] = врем

    print("── работа переговорщика ──")
    о = проба("черновик письма",
              run(конверт("mail.draft", phase="execute", idempotencyKey="m1",
                          input={"to": "client@example.com", "subject": "Правки к договору",
                                 "body": "Предлагаем изменить пункт 4.2 …"}), MAIL, политика), True)
    ид = о["result"]["id"]; print("     ", о["result"]["note"])
    о = проба("список черновиков",
              run(конверт("mail.list_drafts", phase="execute", idempotencyKey="m2"), MAIL, политика), True)
    print("      черновиков:", о["result"]["count"])
    проба("прочитать черновик",
          run(конверт("mail.get_draft", phase="execute", idempotencyKey="m3",
                      input={"id": ид}), MAIL, политика), True)

    print("── канон: отправляет человек ──")
    проба("отправка запрещена политикой",
          run(конверт("mail.send"), MAIL, политика), False, "POLICY_DENIED")
    смелая = copy.deepcopy(политика); смелая["capabilities"]["mail.send"] = True
    проба("даже с разрешённым правом — эффект запрещён",
          run(конверт("mail.send"), MAIL, смелая), False, "POLICY_DENIED")

    print("── предохранители домена ──")
    проба("кривой адрес",
          run(конверт("mail.draft", input={"to": "не-адрес", "subject": "т", "body": "б"}),
              MAIL, политика), False, "SCHEMA_REJECTED")
    узкая = copy.deepcopy(политика); узкая["scope"]["allowedRecipients"] = ["boss@example.com"]
    проба("адресат вне списка политики",
          run(конверт("mail.draft", input={"to": "chужой@example.com", "subject": "т", "body": "б"}),
              MAIL, узкая), False, "SCOPE_DENIED")
    проба("письмо длиннее разрешённого",
          run(конверт("mail.draft", input={"to": "a@b.cd", "subject": "т", "body": "x"*30000}),
              MAIL, политика), False, "SCOPE_DENIED")
    проба("выгрузка требует согласования",
          run(конверт("mail.export", phase="execute", idempotencyKey="m4",
                      input={"id": ид, "to": врем + "/письмо.txt"}), MAIL, политика),
          False, "APPROVAL_REQUIRED")
    план = run(конверт("mail.export", input={"id": ид, "to": врем + "/письмо.txt"}), MAIL, политика)
    о = проба("выгрузка с согласованием",
              run(конверт("mail.export", phase="execute", idempotencyKey="m4",
                          input={"id": ид, "to": врем + "/письмо.txt"},
                          approval={"planHash": план["planHash"], "approvedBy": "человек"}),
                  MAIL, политика), True)
    print("      файл:", о["result"]["file"].split("/")[-1], о["result"]["bytes"], "байт")

print()
print("САМОПРОВЕРКА ПОЧТЫ:", "провалена — " + "; ".join(ошибки) if ошибки else "пройдена")
raise SystemExit(1 if ошибки else 0)
