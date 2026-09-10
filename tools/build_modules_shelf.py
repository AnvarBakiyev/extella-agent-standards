#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Каталог способностей: страница магазина, которая рассказывает и передаёт.

ЗАЧЕМ. Первая версия полки была справочником: карточки с идентификаторами и «желательно:
pdftoppm». Анвар 06.09.2026: «худшее приложение, которое я видел» — непонятно, для чего,
что показывает и что даёт. Решение: это не рабочее окно, а витрина с одним действием. Имя и форму 06.09.2026 Анвар выбрал
из замысла «Каталог способностей» (04.09): наборы по работе, плитка с «на чём сделано, где
исполняется, сколько стоит», метка «проверено живьём» — теперь она берётся из поля `verified`
паспорта, а не пишется руками.
Она отвечает на три вопроса за пять секунд (что это, что можно, что сделать первым):
сценарии словами бизнеса, узлы плитками с честным статусом «есть / в работе / нужен»,
три шага и одна кнопка «Скопировать задание для ИИ». Кнопка не зовёт платформу: она
кладёт в буфер задание для создателя с Claude Code, в которое уже вшиты репозиторий,
глава и список узлов с границами из паспортов. Витрина собирается из реестра, поэтому
задание всегда свежее.

Сценарии — содержимое продукта, не выводятся из реестра: лежат в `scenarios.json` рядом с
витриной (образец создаётся при первой сборке, дальше правится словами).

    python3 tools/build_modules_shelf.py apps/moduli
    python3 tools/build_modules_shelf.py apps/moduli --реестр путь.json --приложения ~/extella-plugins/apps
    python3 tools/build_modules_shelf.py --selftest

Дальше: python3 tools/deploy_page_product.py apps/moduli.

Коды выхода: 0 — собрано, 1 — отказ с названной причиной, 2 — реестр не прочитан.
"""
import html
import json
import os
import pathlib
import subprocess
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ  # noqa: E402

ВИДЖЕТ = СЮДА.parent / "templates" / "help_widget.js"
БРОНЗА = СЮДА / "bronze_icon.py"
РЕЕСТР = pathlib.Path.home() / "extella_wizard" / "registry" / "capabilities_declared.json"
ЖИВОЙ_КЭШ = pathlib.Path.home() / "extella_wizard" / "registry" / "capability_registry_cache.json"
ПРИЛОЖЕНИЯ = pathlib.Path.home() / "extella-plugins" / "apps"
ЭКСПЕРТЫ_СТАНДАРТОВ = СЮДА.parent / "experts"
РЕПОЗИТОРИЙ = "https://github.com/AnvarBakiyev/extella-agent-standards"

# Статус узла. Порядок важен: паспорт сильнее «где-то есть».
ЕСТЬ, В_РАБОТЕ, НУЖЕН = "есть", "в работе", "нужен"

СЦЕНАРИИ_ОБРАЗЕЦ = [
    {"id": "invoices",
     "title": {"ru": "Входящие счета", "en": "Incoming invoices"},
     "who": {"ru": "бухгалтеру", "en": "for the accountant"},
     "story": {"ru": "Счета приходят сканами и PDF. Приложение складывает их в очередь, читает, достаёт номер, сумму и поставщика, бухгалтер проверяет и передаёт в 1С.",
               "en": "Invoices arrive as scans and PDFs. The app queues them, reads them, extracts number, amount and supplier; the accountant checks and passes them to 1C."},
     "nodes": [{"id": "toolkit_ocr_read", "ru": "распознавание скана", "en": "scan recognition"},
               {"id": "toolkit_invoice_fields", "ru": "реквизиты из текста", "en": "fields from text"},
               {"id": "toolkit_queue", "ru": "очередь и история", "en": "queue and history"},
               {"id": "wz_1c_call", "ru": "передача в 1С", "en": "hand-over to 1C"}]},
    {"id": "leads",
     "title": {"ru": "Заявки из WhatsApp и почты", "en": "Requests from WhatsApp and email"},
     "who": {"ru": "менеджеру", "en": "for the manager"},
     "story": {"ru": "Заявки приходят в мессенджер и на почту. Приложение собирает их в один список, заводит контрагента и сделку, готовит ответ черновиком, отправляет человек.",
               "en": "Requests arrive in the messenger and by email. The app gathers them into one list, creates the counterparty and the deal, drafts a reply; a person sends it."},
     "nodes": [{"id": "wz_connector_whatsapp", "ru": "WhatsApp", "en": "WhatsApp"},
               {"id": "wz_connector_email", "ru": "почта", "en": "email"},
               {"id": "crm_backend", "ru": "контрагенты и сделки", "en": "counterparties and deals"},
               {"id": "local_model_ask", "ru": "ответ черновиком", "en": "draft reply"}]},
    {"id": "contracts",
     "title": {"ru": "Договоры на проверку", "en": "Contracts for review"},
     "who": {"ru": "юристу", "en": "for the lawyer"},
     "story": {"ru": "Договор загружается файлом или сканом. Приложение читает его на компьютере юриста, находит риски и готовит протокол разногласий. Наружу текст не уходит.",
               "en": "A contract is uploaded as a file or a scan. The app reads it on the lawyer's computer, finds risks and drafts a protocol of disagreements. The text stays inside."},
     "nodes": [{"id": "toolkit_contract_read", "ru": "чтение договора локальной моделью", "en": "contract reading by a local model",
                "exists": True},   # эксперт есть на платформе с 26.08, паспорта нет
               {"id": "toolkit_ocr_read", "ru": "распознавание скана", "en": "scan recognition"},
               {"id": "doc_to_pdf", "ru": "документ в PDF", "en": "document to PDF"},
               {"id": "contract_protocol", "ru": "протокол разногласий", "en": "protocol of disagreements"}]},
]

СЛОВА = {
    "ru": {
        "brand": "Extella", "title": "Каталог способностей",
        "lead": "Умения для агента и узлы для приложений сотрудников — одна библиотека. У каждой способности паспорт: что делает, чего не делает, где исполняется. Приложение под твою задачу собирается из них одной кнопкой ниже.",
        "help": "? Как это работает",
        "scen_h": "Готовые наборы по работе", "scen_lead": "С чего обычно начинают. Под каждым набором видно, какие способности уже есть, какие в работе, каких нет.",
        "take": "Взять за основу задания",
        "st_now": "собирается сегодня", "st_part": "частично: есть {n} из {m} узлов", "st_later": "после следующих узлов",
        "nodes_h": "Все способности", "nodes_lead": "Только то, у чего есть паспорт. На плитке: на чём сделано, где исполняется, сколько стоит и когда проверено живьём.",
        "made": "на чём", "where_local": "на вашем компьютере", "where_server": "на сервере", "free": "бесплатно",
        "verified": "проверено живьём {at}", "not_verified": "паспорт есть, живьём не проверено",
        "more": "Границы и требования", "less": "Свернуть", "needs": "Нужно на компьютере", "limits": "Чего не делает",
        "st_have": "есть", "st_work": "в работе", "st_need": "нужен", "nodes_none": "Способностей с паспортом пока нет.",
        "how_h": "Как получить своё приложение",
        "steps": [
            {"t": "Опиши задачу словами", "d": "Кому, что должно делать, откуда приходят данные и куда уходят. Поле ниже уже содержит подсказку."},
            {"t": "Скопируй задание и передай ИИ-создателю", "d": "Claude Code или Codex с репозиторием стандартов. В задании уже есть глава, узлы и их границы."},
            {"t": "Получи плитку в магазине", "d": "ИИ собирает приложение по главе, называет узлы, которых не хватает, и выкладывает предрелиз. Публикацию подтверждаешь ты."},
        ],
        "task_label": "Задача для приложения", "task_hint": "Например: приложение для бухгалтера. Счета приходят на почту сканами. Нужна очередь, распознавание, реквизиты, проверка человеком, передача в 1С.",
        "copy": "Скопировать задание для ИИ", "copied": "Скопировано. Вставь в Claude Code или Codex",
        "copy_fail": "Буфер здесь недоступен. Выдели текст задания ниже и скопируй вручную",
        "prompt_label": "Задание целиком", "apps_h": "Уже собрано", "apps_lead": "Приложения, собранные из узлов по этой же схеме, с честным статусом.",
        "apps_none": "Пока ни одного. Первое соберут по твоему заданию.",
        "app_state": {"опубликовано": "в магазине", "предрелиз": "предрелиз", "собрано": "собрано", "снято": "снято с витрины"},
        "foot": "Витрина собрана из реестра паспортов",
    },
    "en": {
        "brand": "Extella", "title": "Capability catalog",
        "lead": "Skills for the agent and nodes for employee apps are one library. Every capability has a passport: what it does, what it does not, where it runs. An app for your task is assembled from them with one button below.",
        "help": "? How it works",
        "scen_h": "Ready sets by job", "scen_lead": "Where people usually start. Under each set you see which capabilities exist, which are in progress, which are missing.",
        "take": "Use as the task",
        "st_now": "assembles today", "st_part": "partly: {n} of {m} nodes exist", "st_later": "after the next nodes",
        "nodes_h": "All capabilities", "nodes_lead": "Only what has a passport. On the tile: what it is made of, where it runs, what it costs and when it was verified live.",
        "made": "made of", "where_local": "on your computer", "where_server": "on the server", "free": "free",
        "verified": "verified live {at}", "not_verified": "passport exists, not verified live",
        "more": "Limits and requirements", "less": "Collapse", "needs": "Needed on the computer", "limits": "What it does not do",
        "st_have": "exists", "st_work": "in progress", "st_need": "needed", "nodes_none": "No capability with a passport yet.",
        "how_h": "How to get your own app",
        "steps": [
            {"t": "Describe the task in words", "d": "For whom, what it must do, where the data comes from and where it goes. The field below already has a hint."},
            {"t": "Copy the task and hand it to the AI creator", "d": "Claude Code or Codex with the standards repository. The task already carries the chapter, the nodes and their limits."},
            {"t": "Get a tile in the store", "d": "The AI assembles the app by the chapter, names missing nodes and ships a prerelease. You confirm the publication."},
        ],
        "task_label": "Task for the app", "task_hint": "For example: an app for the accountant. Invoices arrive by email as scans. Needed: a queue, recognition, fields, a human check, hand-over to 1C.",
        "copy": "Copy the task for the AI", "copied": "Copied. Paste it into Claude Code or Codex",
        "copy_fail": "The clipboard is unavailable here. Select the task text below and copy it by hand",
        "prompt_label": "The whole task", "apps_h": "Already assembled", "apps_lead": "Apps assembled from nodes by the same scheme, with an honest status.",
        "apps_none": "None yet. The first one will be assembled from your task.",
        "app_state": {"опубликовано": "in the store", "предрелиз": "prerelease", "собрано": "built", "снято": "withdrawn"},
        "foot": "The showcase is built from the passport registry",
    },
}

ПОМОЩЬ = {
    "ru": {"title": "Как устроена эта витрина", "sub": "Что здесь показано, откуда взято и что делает кнопка",
           "steps": ["Сценарии — примеры того, что собирается из узлов; статус под каждым считается по паспортам",
                     "Узлы — модули библиотеки; всё про них взято из паспортов, руками здесь не пишется",
                     "Кнопка кладёт в буфер задание для ИИ-создателя: репозиторий, глава, узлы, твоя задача"],
           "sure": ["Кнопка ничего не запускает и никуда не отправляет: только буфер обмена", "Всё, что сказано про узел, взято из его паспорта"],
           "nope": ["Витрина не собирает приложение сама: сборку делает ИИ-создатель по заданию", "Узел без паспорта показан как «в работе», его границы неизвестны",
                    "Требования к компьютеру перечислены, но на этой машине не проверены"],
           "who": ["Владелец библиотеки: добавляет узлы и сценарии", "Автор узла: отвечает за паспорт и границы"]},
    "en": {"title": "How this showcase works", "sub": "What is shown, where it comes from and what the button does",
           "steps": ["Scenarios are examples of what assembles from nodes; the status under each is computed from passports",
                     "Nodes are library modules; everything about them comes from passports, nothing is written by hand",
                     "The button puts a task for the AI creator into the clipboard: repository, chapter, nodes, your task"],
           "sure": ["The button runs nothing and sends nothing: clipboard only", "Everything said about a node comes from its passport"],
           "nope": ["The showcase does not assemble the app itself: the AI creator does, from the task", "A node without a passport is shown as «in progress», its limits are unknown",
                    "Computer requirements are listed, not checked on this machine"],
           "who": ["The library owner: adds nodes and scenarios", "The node author: owns the passport and the limits"]},
}

СТИЛЬ = """
:root{--bg:#0A0A0A;--s1:#141414;--s2:#181818;--ink:#F5F3EE;--silver:#8C8C8C;--accent:#D4944A;
  --petrol:#5FA8A0;--line:rgba(243,238,229,.09);--sans:Nunito,-apple-system,sans-serif;--serif:'Source Serif 4',Georgia,serif;
  --mono:'JetBrains Mono',ui-monospace,Menlo,monospace}
:root[data-lm="1"]{--bg:#FAF9F5;--s1:#FFFFFF;--s2:#F5F3EC;--ink:#0A0A0A;--accent:#C57E33;--petrol:#2F6B66;--line:#D7E0DC}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:400 15px/1.6 var(--sans)}
button,input,select,textarea{font-family:inherit}
a{color:var(--petrol)}
.лист{max-width:1040px;margin:0 auto;padding:32px 24px 64px}
.метка{font:400 11px/1.6 var(--mono);color:var(--petrol);letter-spacing:.02em}
.шапка{display:flex;align-items:flex-start;gap:24px;margin-bottom:48px}
.шапка>div{flex:1}
h1{font:400 26px/1.25 var(--serif);margin:8px 0 12px;max-width:720px}
.лид{font-size:15px;color:var(--silver);max-width:640px}
h2{font:400 20px/1.3 var(--serif);margin:48px 0 8px}
.подлид{font-size:13px;color:var(--silver);margin-bottom:16px;max-width:640px}
.сетка{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.карта{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:8px}
.карта h3{font:400 20px/1.3 var(--serif)}
.карта .кому{font-size:13px;color:var(--silver)}
.карта p{font-size:13px}
.пилюля{display:inline-block;font-size:11px;font-weight:500;border:1px solid var(--line);border-radius:999px;padding:4px 8px;color:var(--silver)}
.пилюля.есть{color:var(--petrol);border-color:var(--petrol)}
.узлы{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.узел{font-size:11px;border-radius:8px;padding:4px 8px;background:var(--s2);color:var(--silver)}
.узел.есть{color:var(--ink);background:var(--s2);border:1px solid var(--petrol)}
.узел.нужен{opacity:.7}
.btn{font-size:15px;font-weight:600;color:#FFFFFF;background:var(--accent);border:0;border-radius:999px;padding:12px 24px;cursor:pointer}
.btn.gold{color:#FFFFFF}
.btn[disabled]{opacity:.6;cursor:default}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500}
.btn.sm{font-size:13px;padding:8px 16px}
.плитка{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
.плитка b{display:block;font:400 15px/1.3 var(--serif);margin-bottom:4px}
.плитка p{font-size:13px;margin-bottom:8px}
.плитка details{font-size:13px}
.плитка summary{cursor:pointer;color:var(--petrol);list-style:none}
.плитка summary::-webkit-details-marker{display:none}
.плитка ul{padding-left:16px;color:var(--silver);margin:8px 0}
.плитка li{margin-bottom:4px}
.шаги{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-bottom:24px}
.шаг{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
.шаг i{display:block;font:400 26px/1 var(--serif);color:var(--petrol);font-style:normal;margin-bottom:8px}
.шаг b{display:block;font-weight:600;margin-bottom:4px}
.шаг p{font-size:13px;color:var(--silver)}
.форма{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:24px}
label{display:block;font-size:13px;color:var(--silver);margin-bottom:4px}
textarea{width:100%;min-height:96px;font-size:15px;line-height:1.5;color:var(--ink);background:var(--s2);border:1px solid var(--line);border-radius:8px;padding:12px;resize:vertical}
textarea:focus{outline:none;border-color:var(--accent)}
.действие{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin:16px 0}
.статус{font-size:13px;color:var(--silver)}
.задание{font:400 11px/1.6 var(--mono);color:var(--silver);background:var(--s2);border:1px solid var(--line);border-radius:8px;padding:12px;white-space:pre-wrap;word-break:break-word;max-height:240px;overflow:auto}
.подвал{font:400 11px/1.6 var(--mono);color:var(--silver);margin-top:48px}
#xtl_help{display:none;position:fixed;inset:0;z-index:9996;background:rgba(12,14,18,.55);overflow:auto;padding:32px 16px}
#xtl_help>div{max-width:720px;margin:0 auto;background:var(--s1);color:var(--ink);border-radius:12px;padding:24px}
.card{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
"""


def _э(т) -> str:
    return html.escape(str(т))


def _в_скрипт(объект) -> str:
    return json.dumps(объект, ensure_ascii=False).replace("</", "<\\/")


def _границы(лимиты, язык: str) -> list:
    вышло = []
    for л in лимиты or []:
        т = str(л)
        if "EN:" in т and "RU:" in т:
            ру, ен = т.split("EN:", 1)
            вышло.append(ру.replace("RU:", "", 1).strip() if язык == "ru" else ен.strip())
        else:
            вышло.append(т)
    return вышло


def известные_способности(живой_кэш: pathlib.Path, эксперты_папка: pathlib.Path) -> set:
    """Что существует без паспорта: живой реестр и готовые эксперты стандартов."""
    ид = set()
    try:
        for и in json.loads(живой_кэш.read_text(encoding="utf-8")).get("capabilities") or []:
            if и.get("capability_id"):
                ид.add(str(и["capability_id"]))
    except Exception:
        pass
    if эксперты_папка.is_dir():
        ид.update(п.stem for п in эксперты_папка.glob("*.py"))
    return ид


def узлы_из_реестра(реестр: dict) -> list:
    узлы = []
    for м in реестр.get("automations") or []:
        if str(м.get("kind") or "") != "module":
            continue
        узлы.append({"id": м.get("automation_id"), "name": м.get("name") or {}, "goal": м.get("business_goal") or "",
                     "ok": bool(м.get("passport_ok")), "needs": м.get("needs") or [],
                     "verified": м.get("verified") or None, "hosting": м.get("hosting_profile") or "local",
                     "made": [н.split(":", 1)[1].split("(")[0].strip() for н in (м.get("needs") or [])
                              if н.startswith(("command:", "module:"))],
                     "experts": [{"name": и, "what": (м.get("experts_what") or {}).get(и) or ""} for и in (м.get("experts") or [])],
                     "limits": {"ru": _границы(м.get("limits"), "ru"), "en": _границы(м.get("limits"), "en")}})
    return узлы


def статус_узла(ид: str, узлы: list, известные: set, объявлен: bool = False) -> str:
    """есть — паспорт прошёл гейт; в работе — существует без паспорта (живой реестр, эксперты
    стандартов или поле exists в сценарии, когда узел новее кэша); нужен — нигде нет."""
    if any(у["id"] == ид and у["ok"] for у in узлы):
        return ЕСТЬ
    if объявлен or ид in известные or any(у["id"] == ид for у in узлы) or any(э["name"] == ид for у in узлы for э in у["experts"]):
        return В_РАБОТЕ
    return НУЖЕН


def сценарии_со_статусом(сценарии: list, узлы: list, известные: set) -> list:
    итог = []
    for с in сценарии:
        узлы_сц = [dict(у, status=статус_узла(у["id"], узлы, известные, bool(у.get("exists")))) for у in с.get("nodes") or []]
        есть = sum(1 for у in узлы_сц if у["status"] == ЕСТЬ)
        итог.append(dict(с, nodes=узлы_сц, have=есть, total=len(узлы_сц)))
    return итог


def приложения_из_каталога(корень: pathlib.Path, витрина: pathlib.Path) -> list:
    итог = []
    if not корень.is_dir():
        return итог
    for папка in sorted(корень.iterdir()):
        план = папка / "app.json"
        if not план.is_file() or папка.resolve() == витрина.resolve():
            continue
        try:
            п = json.loads(план.read_text(encoding="utf-8"))
            л = json.loads((папка / "listing.json").read_text(encoding="utf-8")) if (папка / "listing.json").is_file() else {}
        except ValueError:
            continue
        if not п.get("modules"):
            continue
        итог.append({"slug": п.get("slug"), "name": п.get("name") or {}, "description": п.get("description") or {},
                     "modules": п.get("modules") or [], "state": л.get("состояние") or "собрано",
                     "listing_id": л.get("listing_id") or "", "version": л.get("версия") or п.get("version") or ""})
    return итог


def задание(узлы: list, язык: str) -> str:
    """Текст, который уходит ИИ-создателю. Ключевое: узлы и их границы уже внутри."""
    if язык == "ru":
        строки = ["Собери приложение из модулей Extella.", "",
                  "Подготовка: git clone " + РЕПОЗИТОРИЙ + " и прочитай APP_FROM_MODULES.md целиком. Стадия — build. "
                  "Реестр паспортов: python3 tools/build_capability_registry.py --roots-file config_registry_roots.txt "
                  "-o ~/extella_wizard/registry/capabilities_declared.json", "",
                  "Задача от человека: {{ЗАДАЧА}}", "",
                  "Узлы библиотеки на сегодня (из паспортов):"]
        for у in узлы:
            строки.append(f"- {у['name'].get('ru') or у['id']} ({у['id']}): {у['goal']}")
            for г in у["limits"]["ru"][:4]:
                строки.append(f"  · не делает: {г}")
            if у["needs"]:
                строки.append("  · нужно на компьютере: " + "; ".join(у["needs"]))
        строки += ["", "Правила: разложи задачу на потребности и по каждой спроси реестр (wz_capability_find). "
                       "Чего в библиотеке нет — назови словами в плане и в блоке «чего не обещаем» окна, не выдумывай. "
                       "Собери каталог приложения (build_app_from_modules.py), проведи эксперты агенту "
                       "(provision_modules.py), прогони гейт (check_app_from_modules.py --stage build) и покажи план "
                       "человеку до выкладки. Публикацию подтверждает человек."]
    else:
        строки = ["Assemble an app from Extella modules.", "",
                  "Setup: git clone " + РЕПОЗИТОРИЙ + " and read APP_FROM_MODULES.md in full. Stage: build. "
                  "Passport registry: python3 tools/build_capability_registry.py --roots-file config_registry_roots.txt "
                  "-o ~/extella_wizard/registry/capabilities_declared.json", "",
                  "Task from the person: {{ЗАДАЧА}}", "",
                  "Library nodes as of today (from passports):"]
        for у in узлы:
            строки.append(f"- {у['name'].get('en') or у['id']} ({у['id']}): {у['goal']}")
            for г in у["limits"]["en"][:4]:
                строки.append(f"  · does not: {г}")
            if у["needs"]:
                строки.append("  · needed on the computer: " + "; ".join(у["needs"]))
        строки += ["", "Rules: split the task into needs and ask the registry for each (wz_capability_find). "
                       "Name what the library lacks in the plan and in the window's «what we do not promise» block; never invent. "
                       "Build the app folder (build_app_from_modules.py), provision experts to the agent (provision_modules.py), "
                       "run the gate (check_app_from_modules.py --stage build) and show the plan to the person before shipping. "
                       "The person confirms the publication."]
    return "\n".join(строки)


def страница(узлы: list, сценарии: list, приложения: list) -> str:
    if not ВИДЖЕТ.exists():
        raise Отказ(f"нет канонического виджета {ВИДЖЕТ}")
    данные = {"nodes": узлы, "scenarios": сценарии, "apps": приложения,
              "prompt": {"ru": задание(узлы, "ru"), "en": задание(узлы, "en")}}
    help_ = {"app": {я: {"icon": "", "title": ПОМОЩЬ[я]["title"], "sub": ПОМОЩЬ[я]["sub"], "steps": ПОМОЩЬ[я]["steps"],
                         "sure": ПОМОЩЬ[я]["sure"], "nope": ПОМОЩЬ[я]["nope"],
                         "who": {"title": {"ru": "Кто отвечает", "en": "Who is responsible"}[я], "items": ПОМОЩЬ[я]["who"]},
                         "extra": ""} for я in ("ru", "en")}}
    сценарий = r"""
var WLANG = 'ru';
function el(id){ return document.getElementById(id); }
function э(v){ return String(v == null ? '' : v).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function t(v){ if (v && typeof v === 'object') { return v[WLANG] || v.ru || v.en || ''; } return v == null ? '' : String(v); }
document.documentElement.setAttribute('data-lm', (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? '1' : '0');
window.addEventListener('message', function(e){
  var d = e && e.data; if (!d || typeof d !== 'object') return;
  if (d.type === 'etb_theme') { document.documentElement.setAttribute('data-lm', (d.theme === 'light' || d.light === true) ? '1' : '0'); }
  if (d.type === 'etb_init') { var l = String(d.lang || d.language || '').slice(0, 2); if (l === 'en' || l === 'ru') { WLANG = l; рисовать(); } }
});
function статус_слово(s){ var С = СЛОВА[WLANG]; return s === 'есть' ? С.st_have : (s === 'в работе' ? С.st_work : С.st_need); }
function класс(s){ return s === 'есть' ? 'есть' : (s === 'нужен' ? 'нужен' : 'работа'); }
function задание_текст(){
  var задача = (el('task').value || '').trim() || (WLANG === 'ru' ? '[впиши задачу: кому, что делает, откуда данные, куда уходят]' : '[describe the task: for whom, what it does, where data comes from and goes]');
  return ДАННЫЕ.prompt[WLANG].replace('{{ЗАДАЧА}}', задача);
}
function обновить_задание(){ el('prompt').textContent = задание_текст(); }
function взять(id){
  var с = ДАННЫЕ.scenarios.filter(function(x){ return x.id === id; })[0]; if (!с) return;
  el('task').value = t(с.title) + ' — ' + t(с.who) + '. ' + t(с.story);
  обновить_задание();
  el('how').scrollIntoView({behavior: 'smooth', block: 'start'});
}
function скопировать(){
  var кнопка = el('copy'), статус = el('copy_status'), текст = задание_текст();
  кнопка.disabled = true;
  // Окно магазина живёт в песочнице без общего происхождения: clipboard API там отказывает.
  // Запасной путь — выделить текст задания и execCommand('copy'); если и он не сработал,
  // текст остаётся выделенным, и человек копирует сам. Пустого экрана нет ни в одном исходе.
  var выделить = function(){ var r = document.createRange(); r.selectNodeContents(el('prompt')); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); };
  var готово = function(ок){ статус.textContent = ок ? СЛОВА[WLANG].copied : СЛОВА[WLANG].copy_fail; кнопка.disabled = false; };
  var запасной = function(){ выделить(); var ок = false; try { ок = document.execCommand('copy'); } catch (e) { ок = false; } готово(ок); };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(текст).then(function(){ готово(true); }, запасной); }
    else { запасной(); }
  } catch (e) { запасной(); }
}
function рисовать(){
  var С = СЛОВА[WLANG]; document.documentElement.lang = WLANG;
  el('brand').textContent = С.brand; el('title').textContent = С.title; el('lead').textContent = С.lead; el('help_btn').textContent = С.help;
  el('scen_h').textContent = С.scen_h; el('scen_lead').textContent = С.scen_lead;
  el('scenarios').innerHTML = ДАННЫЕ.scenarios.map(function(с){
    var пилюля = с.have === с.total ? С.st_now : (с.have > 0 ? С.st_part.replace('{n}', с.have).replace('{m}', с.total) : С.st_later);
    var узлы = с.nodes.map(function(у){ return '<span class="узел ' + класс(у.status) + '" title="' + э(статус_слово(у.status)) + '">' + э(t(у)) + ' · ' + э(статус_слово(у.status)) + '</span>'; }).join('');
    var кому = t(с.who); кому = кому.charAt(0).toUpperCase() + кому.slice(1);
    return '<div class="карта"><span class="пилюля' + (с.have === с.total ? ' есть' : '') + '">' + э(пилюля) + '</span><h3>' + э(кому) + '</h3>' +
      '<span class="кому">' + э(t(с.title)) + '</span><p>' + э(t(с.story)) + '</p><div class="узлы">' + узлы + '</div>' +
      '<div><button type="button" class="btn ghost sm" onclick="взять(\'' + э(с.id) + '\')">' + э(С.take) + '</button></div></div>';
  }).join('');
  el('nodes_h').textContent = С.nodes_h; el('nodes_lead').textContent = С.nodes_lead;
  el('nodes').innerHTML = ДАННЫЕ.nodes.length ? ДАННЫЕ.nodes.map(function(у){
    var лимиты = (у.limits[WLANG] || []).map(function(l){ return '<li>' + э(l) + '</li>'; }).join('');
    var где = у.hosting === 'local' ? С.where_local : С.where_server;
    var состав = (у.made && у.made.length ? С.made + ': ' + у.made.join(', ') + ' · ' : '') + где + ' · ' + С.free;
    var проверка = у.verified && у.verified.at ? '<span class="пилюля есть" title="' + э(у.verified.where || '') + '">' + э(С.verified.replace('{at}', String(у.verified.at).split('-').reverse().join('.'))) + '</span>'
                                              : '<span class="пилюля">' + э(С.not_verified) + '</span>';
    return '<div class="плитка">' + проверка + '<b>' + э(t(у.name)) + '</b><p>' + э(у.goal) + '</p><p class="метка">' + э(состав) + '</p>' +
      '<details><summary>' + э(С.more) + '</summary><ul>' + лимиты + '</ul>' +
      (у.needs.length ? '<p><span class="метка">' + э(С.needs) + '</span><br>' + э(у.needs.join(' · ')) + '</p>' : '') + '</details></div>';
  }).join('') : '<p class="подлид">' + э(С.nodes_none) + '</p>';
  el('how_h').textContent = С.how_h;
  el('steps').innerHTML = С.steps.map(function(ш, i){ return '<div class="шаг"><i>' + (i + 1) + '</i><b>' + э(ш.t) + '</b><p>' + э(ш.d) + '</p></div>'; }).join('');
  el('task_label').textContent = С.task_label; el('task').placeholder = С.task_hint;
  el('copy').textContent = С.copy; el('prompt_label').textContent = С.prompt_label;
  el('apps_h').textContent = С.apps_h; el('apps_lead').textContent = С.apps_lead;
  el('apps').innerHTML = ДАННЫЕ.apps.length ? ДАННЫЕ.apps.map(function(a){
    var имя = a.listing_id && a.state === 'опубликовано' ? '<a href="/app-page/' + э(a.listing_id) + '/">' + э(t(a.name)) + '</a>' : э(t(a.name));
    return '<div class="плитка"><span class="пилюля">' + э(С.app_state[a.state] || a.state) + (a.version ? ' · ' + э(a.version) : '') + '</span><b>' + имя + '</b><p>' + э(t(a.description)) + '</p></div>';
  }).join('') : '<p class="подлид">' + э(С.apps_none) + '</p>';
  el('foot').textContent = С.brand + ' · ' + С.foot;
  обновить_задание();
}
document.addEventListener('DOMContentLoaded', function(){
  рисовать();
  el('task').addEventListener('input', обновить_задание);
  el('copy').addEventListener('click', скопировать);
  el('help_btn').addEventListener('click', function(){ openHelp('app'); });
  helpFirstTime('app');
});
"""
    return (
        '<!DOCTYPE html><html lang="ru" data-lm="0"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_э(СЛОВА["ru"]["title"])}</title><style>{СТИЛЬ}</style></head><body><div class="лист">'
        '<div class="шапка"><div><p class="метка" id="brand">Extella</p><h1 id="title"></h1><p class="лид" id="lead"></p></div>'
        '<button type="button" class="btn ghost sm" id="help_btn" data-help-key="app">? Как это работает</button></div>'
        '<h2 id="scen_h"></h2><p class="подлид" id="scen_lead"></p><div class="сетка" id="scenarios"></div>'
        '<h2 id="nodes_h"></h2><p class="подлид" id="nodes_lead"></p><div class="сетка" id="nodes"></div>'
        '<section id="how"><h2 id="how_h"></h2><div class="шаги" id="steps"></div>'
        '<div class="форма"><label for="task" id="task_label"></label><textarea id="task"></textarea>'
        '<div class="действие"><button type="button" class="btn" id="copy"></button><span class="статус" id="copy_status"></span></div>'
        '<label id="prompt_label"></label><div class="задание" id="prompt"></div></div></section>'
        '<h2 id="apps_h"></h2><p class="подлид" id="apps_lead"></p><div class="сетка" id="apps"></div>'
        '<p class="подвал" id="foot"></p></div>'
        '<div id="xtl_help"><div><div id="xtl_help_body"></div></div></div>'
        f'<script>\nvar ДАННЫЕ = {_в_скрипт(данные)};\nvar СЛОВА = {_в_скрипт(СЛОВА)};\n'
        f'{ВИДЖЕТ.read_text(encoding="utf-8")}\nHELP = {_в_скрипт(help_)};\n{сценарий}</script></body></html>'
    )


def иконка(куда: pathlib.Path) -> str:
    """Канонический генератор, а если его нет (чистая машина CI без библиотеки картинок,
    замер 10.09.2026) — запасная плитка из сборщика приложений. Отказ здесь стоил красного CI."""
    if куда.exists():
        return "уже есть"
    for глиф in ("layers", "shapes"):
        try:
            р = subprocess.run([sys.executable, str(БРОНЗА), глиф, str(куда)], capture_output=True, text=True, timeout=120)
            if р.returncode == 0 and куда.exists():
                return глиф
        except Exception:
            pass
    from build_app_from_modules import _png
    куда.write_bytes(_png())
    return "запасная плитка (bronze_icon.py не сработал)"


def собрать(папка: pathlib.Path, реестр: dict, каталог: pathlib.Path, известные: set) -> dict:
    папка.mkdir(parents=True, exist_ok=True)
    файл_сц = папка / "scenarios.json"
    if not файл_сц.exists():
        файл_сц.write_text(json.dumps(СЦЕНАРИИ_ОБРАЗЕЦ, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    сценарии_сырые = json.loads(файл_сц.read_text(encoding="utf-8"))
    узлы = узлы_из_реестра(реестр)
    сценарии = сценарии_со_статусом(сценарии_сырые, узлы, известные)
    приложения = приложения_из_каталога(каталог, папка)
    (папка / "index.html").write_text(страница(узлы, сценарии, приложения), encoding="utf-8")
    старый = {}
    if (папка / "listing.json").exists():
        try:
            старый = json.loads((папка / "listing.json").read_text(encoding="utf-8"))
        except ValueError:
            старый = {}
    листинг = {
        "name": "Каталог способностей",
        "описание": "Что умеет Extella: умения для агента и узлы для приложений сотрудников с паспортами — что делает, "
                    "чего не делает, где исполняется, когда проверено живьём. Готовые наборы по работе и одна кнопка: "
                    "скопировать задание для ИИ-создателя, который соберёт приложение под твою задачу.",
        "теги": ["инструмент", "способности", "каталог", "модули"], "иконка": "icon.png",
        "версия": старый.get("версия") or "0.1.0", "цена": 0, "права": [],
        "состояние": старый.get("состояние") or "собрано",
        "узлов": len(узлы), "сценариев": len(сценарии), "приложений": len(приложения),
    }
    for к in ("listing_id", "version_id"):
        if старый.get(к):
            листинг[к] = старый[к]
    (папка / "listing.json").write_text(json.dumps(листинг, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"узлов": len(узлы), "сценариев": len(сценарии), "приложений": len(приложения), "иконка": иконка(папка / "icon.png")}


def selftest() -> int:
    import tempfile
    ошибки = []
    реестр = {"automations": [
        {"automation_id": "toolkit_ocr_read", "kind": "module", "name": {"ru": "Распознавание текста", "en": "Text recognition"},
         "business_goal": "достать текст со скана", "passport_ok": True, "needs": ["command: tesseract (желательно)"],
         "experts": ["toolkit_ocr_read"], "experts_what": {"toolkit_ocr_read": "читает скан"},
         "verified": {"at": "2026-09-05", "where": "стенд"}, "hosting_profile": "local",
         "limits": ["RU: наружу не пишет. EN: sends nothing out.", "<img src=x onerror=alert(1)>"]},
        {"automation_id": "app_x", "kind": "automation", "name": {"ru": "Не модуль", "en": "Not a module"}, "passport_ok": True},
    ]}
    известные = {"uc_parse_invoices_acts", "wz_connector_whatsapp"}
    with tempfile.TemporaryDirectory() as tmp:
        корень = pathlib.Path(tmp)
        (корень / "apps" / "probe_app").mkdir(parents=True)
        (корень / "apps" / "probe_app" / "app.json").write_text(json.dumps(
            {"slug": "probe_app", "name": {"ru": "Проба", "en": "Probe"}, "description": {"ru": "о", "en": "o"}, "modules": ["toolkit_ocr_read"]}))
        (корень / "apps" / "probe_app" / "listing.json").write_text(json.dumps({"состояние": "опубликовано", "listing_id": "lst_1", "версия": "0.1.3"}))
        итог = собрать(корень / "apps" / "shelf", реестр, корень / "apps", известные)
        с = (корень / "apps" / "shelf" / "index.html").read_text()
        if итог["узлов"] == 1 and итог["приложений"] == 1 and итог["сценариев"] == 3:
            print("  ✓ узел с паспортом, три сценария и приложение из каталога; автоматизация — не узел")
        else:
            ошибки.append(f"счёт неверен: {итог}")
        сц = json.loads((корень / "apps" / "shelf" / "scenarios.json").read_text())
        статусы = {у["id"]: статус_узла(у["id"], узлы_из_реестра(реестр), известные) for с_ in сц for у in с_["nodes"]}
        if статусы["toolkit_ocr_read"] == ЕСТЬ and статусы["wz_connector_whatsapp"] == В_РАБОТЕ and статусы["crm_backend"] == НУЖЕН:
            print("  ✓ статус узла: паспорт — «есть», без паспорта — «в работе», неизвестный — «нужен»")
        else:
            ошибки.append(f"статусы узлов неверны: {статусы}")
        задание_ru = задание(узлы_из_реестра(реестр), "ru")
        if '"at": "2026-09-05"' not in с or '"made": ["tesseract"]' not in с:
            ошибки.append("плитка не несёт «проверено живьём» и «на чём сделано» из паспорта")
        else:
            print("  ✓ плитка: «проверено живьём» и «на чём сделано» взяты из паспорта")
        if "{{ЗАДАЧА}}" in задание_ru and "toolkit_ocr_read" in задание_ru and "APP_FROM_MODULES.md" in задание_ru and "наружу не пишет" in задание_ru:
            print("  ✓ задание для ИИ несёт репозиторий, главу, узлы и их границы")
        else:
            ошибки.append("задание для ИИ неполное")
        for кусок, беда in (("xtl_help", "нет «? Как это работает»"), ('"listing_id": "lst_1"', "нет данных приложения для ссылки"),
                            ("nope", "нет блока «чего не обещаем»"), ("font-family:inherit", "кнопки наберутся Arial"),
                            ('id="copy"', "нет кнопки копирования"), ("navigator.clipboard", "кнопка не пишет в буфер")):
            if кусок not in с:
                ошибки.append(беда)
        if с.count('class="btn"') != 1:
            ошибки.append(f"главных действий {с.count('class=\"btn\"')}, должно быть одно")
        if "<img" in с.split("<script>")[0] or с.count("</script>") != 1:
            ошибки.append("содержимое паспорта попадает в страницу как разметка")
        for запретное in ("app-agent/run", "api.extella.ai", "X-Auth-Token"):
            if запретное in с:
                ошибки.append(f"витрина без агента не должна содержать «{запретное}»")
        if not [о for о in ошибки if "витрина" in о or "разметка" in о or "кнопк" in о or "нет" in о[:4]]:
            print("  ✓ одно главное действие, помощь, буфер, экранирование, без вызовов платформы")
        import check_brand_copy
        ош, _ = check_brand_copy.check_text("витрина", с, strict=True)
        if ош:
            ошибки.append("бренд: " + "; ".join(str(о) for о in ош[:3]))
        else:
            print("  ✓ палитра и слова витрины проходят гейт бренда строго")
        import check_app_scopes, io, contextlib
        буфер = io.StringIO()
        with contextlib.redirect_stdout(буфер):
            код = check_app_scopes.проверить(корень / "apps" / "shelf")
        if код == 0:
            print("  ✓ права листинга: пусто, и код ничего не зовёт")
        else:
            ошибки.append("права: " + буфер.getvalue().strip())
    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main(аргументы) -> int:
    if "--selftest" in аргументы:
        return selftest()
    реестр_путь = pathlib.Path(os.environ.get("EXTELLA_DECLARED_REGISTRY") or РЕЕСТР)
    каталог = ПРИЛОЖЕНИЯ
    if "--реестр" in аргументы:
        реестр_путь = pathlib.Path(аргументы[аргументы.index("--реестр") + 1]).expanduser()
    if "--приложения" in аргументы:
        каталог = pathlib.Path(аргументы[аргументы.index("--приложения") + 1]).expanduser()
    пути = [а for а in аргументы if not а.startswith("--") and а not in (str(реестр_путь), str(каталог))]
    if not пути:
        print(__doc__)
        return 2
    if not реестр_путь.exists():
        print(f"ОТКАЗ: нет реестра паспортов {реестр_путь}")
        return 2
    try:
        итог = собрать(pathlib.Path(пути[0]).expanduser(), json.loads(реестр_путь.read_text(encoding="utf-8")), каталог,
                       известные_способности(ЖИВОЙ_КЭШ, ЭКСПЕРТЫ_СТАНДАРТОВ))
    except Отказ as о:
        print(f"ОТКАЗ: {о}")
        return 1
    print(f"  ✓ витрина собрана: узлов {итог['узлов']}, сценариев {итог['сценариев']}, приложений {итог['приложений']}, иконка — {итог['иконка']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
