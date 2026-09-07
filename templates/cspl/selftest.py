# -*- coding: utf-8 -*-
"""Самопроверка CSPL-ядра на домене «файлы». Гейт обязан уметь провалиться."""
from __future__ import annotations

import copy, json, pathlib, tempfile
from core import run
from domain_files import FILES, DEFAULT_POLICY

СХЕМА = FILES.schema
ошибки: list[str] = []


def конверт(operation, **поля):
    к = {"schemaVersion": СХЕМА, "operation": operation, "connection": "default",
         "environment": "test", "phase": "plan", "input": {}, "limits": {}}
    к.update(поля)
    return к


def проба(имя, ответ, ждём_ok, ждём_код=None):
    ok = ответ.get("ok")
    код = (ответ.get("error") or {}).get("code")
    хорошо = (ok == ждём_ok) and (ждём_код is None or код == ждём_код)
    if not хорошо:
        ошибки.append(f"{имя}: ok={ok} код={код}")
    print(f"  {'✓' if хорошо else '✗'} {имя:44} ok={str(ok):5} {код or ''}")
    return ответ


with tempfile.TemporaryDirectory() as врем:
    корень = pathlib.Path(врем)
    (корень / "смета.txt").write_text("Смета на август: 120 000 ₸", encoding="utf-8")
    (корень / "папка").mkdir()

    политика = copy.deepcopy(DEFAULT_POLICY)
    политика["scope"]["allowedRoots"] = [str(корень)]

    print("── чтение разрешено политикой ──")
    о = проба("план fs.list", run(конверт("fs.list", input={"path": str(корень)}), FILES, политика), True)
    print("     отпечаток плана:", о["planHash"][:26], "| выполнит:", о["result"]["willExecute"])
    о = проба("выполнить fs.list",
              run(конверт("fs.list", phase="execute", idempotencyKey="k1",
                          input={"path": str(корень)}), FILES, политика), True)
    print("     видит:", [з["name"] for з in о["result"]["entries"]])
    о = проба("выполнить fs.read_text",
              run(конверт("fs.read_text", phase="execute", idempotencyKey="k2",
                          input={"path": str(корень / "смета.txt")}), FILES, политика), True)
    print("     прочитано:", repr(о["result"]["text"]))

    print("── предохранители ──")
    проба("выход за корень (..)",
          run(конверт("fs.read_text", input={"path": str(корень / ".." / ".." / "etc" / "passwd")}),
              FILES, политика), False, "SCOPE_DENIED")
    проба("чужой путь целиком",
          run(конверт("fs.stat", input={"path": "/etc/hosts"}), FILES, политика), False, "SCOPE_DENIED")
    проба("неизвестная операция",
          run(конверт("fs.teleport"), FILES, политика), False, "SCHEMA_REJECTED")
    проба("лишнее поле входа",
          run(конверт("fs.stat", input={"path": str(корень), "sudo": True}), FILES, политика),
          False, "SCHEMA_REJECTED")
    проба("запись при политике чтения",
          run(конверт("fs.write_text", input={"path": str(корень / "н.txt"), "text": "x"}),
              FILES, политика), False, "POLICY_DENIED")
    проба("удаление запрещено политикой",
          run(конверт("fs.delete"), FILES, политика), False, "POLICY_DENIED")

    print("── запись: только через согласование ──")
    писатель = copy.deepcopy(политика)
    писатель["capabilities"]["fs.write"] = True
    цель = корень / "черновик.txt"
    план = run(конверт("fs.write_text", input={"path": str(цель), "text": "письмо клиенту"}),
               FILES, писатель)
    проба("план записи", план, True)
    print("     согласование нужно:", план["result"]["decision"]["approvalRequired"])
    проба("выполнить без согласования",
          run(конверт("fs.write_text", phase="execute", idempotencyKey="k3",
                      input={"path": str(цель), "text": "письмо клиенту"}), FILES, писатель),
          False, "APPROVAL_REQUIRED")
    о = проба("выполнить с согласованием",
              run(конверт("fs.write_text", phase="execute", idempotencyKey="k3",
                          input={"path": str(цель), "text": "письмо клиенту"},
                          approval={"planHash": план["planHash"], "approvedBy": "человек"}),
                  FILES, писатель), True)
    print("     на диске:", цель.read_text(encoding="utf-8") if цель.exists() else "НЕТ ФАЙЛА")
    if not цель.exists():
        ошибки.append("запись не состоялась")
    проба("согласование от ЧУЖОГО плана",
          run(конверт("fs.write_text", phase="execute", idempotencyKey="k4",
                      input={"path": str(цель), "text": "подмена"},
                      approval={"planHash": "sha256:" + "0"*64}), FILES, писатель),
          False, "APPROVAL_REQUIRED")

print()
print("САМОПРОВЕРКА:", "провалена — " + "; ".join(ошибки) if ошибки else "пройдена")
raise SystemExit(1 if ошибки else 0)
