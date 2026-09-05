#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Полка «Модули»: страничный продукт магазина, собранный из реестра паспортов.

ЗАЧЕМ. Библиотека модулей и приложения из них существуют как механизм, но человек, который
открывает Extella, их не видит: в магазине нет места, где модули перечислены, а глава для
создателя написана для машины (решение Анвара 05.09.2026: сделать видимым без доработки
платформы). Полка — обычная страница магазина без агента и без прав: что такое модуль,
какие модули есть с границами и требованиями из паспортов, какие приложения из них собраны,
как попросить своё. Собирается из реестра, поэтому не отстаёт от паспортов.

    python3 tools/build_modules_shelf.py apps/moduli                    # index.html, listing.json, icon.png
    python3 tools/build_modules_shelf.py apps/moduli --реестр путь.json --приложения ~/extella-plugins/apps
    python3 tools/build_modules_shelf.py --selftest

Дальше: python3 tools/deploy_page_product.py apps/moduli — предрелиз, публикация кнопкой человека.

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
ПРИЛОЖЕНИЯ = pathlib.Path.home() / "extella-plugins" / "apps"
РЕПОЗИТОРИЙ = "https://github.com/AnvarBakiyev/extella-agent-standards"

СТИЛЬ = """
:root{--bg:#0A0A0A;--s1:#141414;--s2:#181818;--ink:#F5F3EE;--silver:#8C8C8C;--accent:#D4944A;
  --petrol:#5FA8A0;--line:rgba(243,238,229,.09);--sans:Nunito,-apple-system,sans-serif}
:root[data-lm="1"]{--bg:#FAF9F5;--s1:#FFFFFF;--s2:#F5F3EC;--ink:#0A0A0A;--accent:#C57E33;
  --petrol:#2F6B66;--line:#D7E0DC}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:400 15px/1.6 var(--sans);padding:24px 24px 48px}
button,input,select,textarea{font-family:inherit}
a{color:var(--petrol)}
.лист{max-width:960px;margin:0 auto}
header{display:flex;align-items:flex-start;gap:16px;margin-bottom:24px}
h1{font:600 26px/1.25 'Source Serif 4',Georgia,serif;flex:1}
h2{font:600 20px/1.3 'Source Serif 4',Georgia,serif;margin:32px 0 12px}
h3{font:600 15px/1.3 'Source Serif 4',Georgia,serif;color:var(--petrol);margin-bottom:8px}
p{margin-bottom:12px}
.btn{font-size:15px;font-weight:600;color:var(--bg);background:var(--accent);border:0;border-radius:999px;padding:12px 24px;cursor:pointer}
.btn.gold{color:#FFFFFF}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.btn.sm{font-size:13px;padding:8px 16px}
.card{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}
.карты{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.карта{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
.карта b{display:block;font:600 15px/1.3 'Source Serif 4',Georgia,serif;margin-bottom:8px}
.карта p{font-size:13px;margin-bottom:8px}
.метка{font:11px/1.6 'JetBrains Mono',ui-monospace,Menlo,monospace;color:var(--silver)}
.границы{font-size:13px;color:var(--silver);padding-left:16px}
.границы li{margin-bottom:4px}
.нужно{font-size:13px;color:var(--petrol)}
.тихо{font:11px/1.6 'JetBrains Mono',ui-monospace,Menlo,monospace;color:var(--silver);margin-top:24px}
.статус{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:999px;padding:4px 8px;color:var(--silver)}
#xtl_help{display:none;position:fixed;inset:0;z-index:9996;background:rgba(12,14,18,.55);overflow:auto;padding:32px 16px}
#xtl_help>div{max-width:720px;margin:0 auto;background:var(--s1);color:var(--ink);border-radius:12px;padding:24px}
"""

СЛОВА = {
    "ru": {
        "title": "Модули Extella", "help": "? Как это работает",
        "what_h": "Что такое модуль",
        "what": [
            "Модуль — это готовый узел, из которого собираются приложения для сотрудников: распознавание документов, учёт, коннекторы, отправка. У модуля нет своего экрана, только способности с описанными границами.",
            "У каждого модуля есть паспорт: что делает, чего не делает, что ему нужно на компьютере. Всё, что ниже, взято из паспортов, а не написано отдельно.",
            "Приложение собирается из модулей под задачу компании: окно с кнопками, за которыми работают модули на компьютере сотрудника. Файлы остаются у него.",
        ],
        "modules_h": "Модули в библиотеке", "apps_h": "Приложения, собранные из модулей",
        "limits": "Чего не делает", "needs": "Что нужно на компьютере", "experts": "Способности",
        "no_passport": "паспорт не проходит проверку", "apps_none": "Пока ни одного.",
        "modules_none": "Пока ни одного модуля с паспортом.",
        "how_h": "Как получить своё приложение",
        "how": [
            "Напиши агенту Extella в чате, что должно делать приложение и для кого: «Нужно приложение для бухгалтера: очередь входящих счетов, распознавание, реквизиты, отправка в 1С». Агент назовёт модули, которые есть, и то, чего в библиотеке пока нет.",
            "Сборку делает создатель приложения с ИИ по открытой главе в репозитории стандартов. Готовое приложение появляется плиткой в магазине, как те, что перечислены выше.",
        ],
        "repo": "Глава для создателя: ",
        "state": {"опубликовано": "в магазине", "предрелиз": "предрелиз", "собрано": "собрано"},
    },
    "en": {
        "title": "Extella modules", "help": "? How it works",
        "what_h": "What a module is",
        "what": [
            "A module is a ready-made building block for employee apps: document recognition, ledgers, connectors, sending. A module has no screen of its own, only capabilities with stated limits.",
            "Every module has a passport: what it does, what it does not do, what it needs on the computer. Everything below comes from the passports, not from separate copy.",
            "An app is assembled from modules for a company task: a window with buttons, behind which the modules run on the employee's computer. The files stay there.",
        ],
        "modules_h": "Modules in the library", "apps_h": "Apps assembled from modules",
        "limits": "What it does not do", "needs": "What it needs on the computer", "experts": "Capabilities",
        "no_passport": "the passport fails the check", "apps_none": "None yet.",
        "modules_none": "No module with a passport yet.",
        "how_h": "How to get your own app",
        "how": [
            "Tell the Extella agent in the chat what the app should do and for whom: «An app for the accountant: an incoming invoice queue, recognition, fields, posting to 1C». The agent names the modules that exist and what the library still lacks.",
            "The assembly is done by an app creator with AI following the open chapter in the standards repository. The finished app appears as a tile in the store, like the ones listed above.",
        ],
        "repo": "Chapter for the creator: ",
        "state": {"опубликовано": "in the store", "предрелиз": "prerelease", "собрано": "built"},
    },
}

ПОМОЩЬ = {
    "ru": {"title": "Как устроена полка модулей", "sub": "Что здесь показано и откуда это взято",
           "steps": ["Каждый модуль лежит в библиотеке с паспортом: границы, требования, способности",
                     "Полка собирается из реестра паспортов, руками здесь ничего не пишется",
                     "Приложения ниже собраны из этих модулей и стоят в магазине"],
           "sure": ["Всё, что написано про модуль, взято из его паспорта", "Границы модуля — это границы приложения, собранного из него"],
           "nope": ["Полка не ставит модули и не собирает приложения: это только карта", "Модуль без паспорта здесь не показан, даже если он существует",
                    "Требования к компьютеру перечислены, но не проверены на этой машине"],
           "who": ["Владелец библиотеки: добавляет модули и приложения", "Автор модуля: отвечает за паспорт и границы"]},
    "en": {"title": "How the modules shelf works", "sub": "What is shown here and where it comes from",
           "steps": ["Every module lives in the library with a passport: limits, requirements, capabilities",
                     "The shelf is built from the passport registry, nothing here is written by hand",
                     "The apps below are assembled from these modules and are in the store"],
           "sure": ["Everything said about a module comes from its passport", "The limits of a module are the limits of an app built from it"],
           "nope": ["The shelf does not install modules or build apps: it is only a map", "A module without a passport is not shown, even if it exists",
                    "Computer requirements are listed, not checked on this machine"],
           "who": ["The library owner: adds modules and apps", "The module author: owns the passport and the limits"]},
}


def _э(т) -> str:
    return html.escape(str(т))


def _в_скрипт(объект) -> str:
    return json.dumps(объект, ensure_ascii=False).replace("</", "<\\/")


def модули_из_реестра(реестр: dict) -> list:
    return [а for а in (реестр.get("automations") or []) if str(а.get("kind") or "") == "module"]


def приложения_из_каталога(корень: pathlib.Path) -> list:
    итог = []
    if not корень.is_dir():
        return итог
    for папка in sorted(корень.iterdir()):
        план = папка / "app.json"
        if not план.is_file():
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


def _границы(лимиты: list, язык: str) -> list:
    """Строка паспорта «RU: … EN: …» → половина на нужном языке."""
    вышло = []
    for л in лимиты or []:
        т = str(л)
        if "EN:" in т and "RU:" in т:
            ру, ен = т.split("EN:", 1)
            ру = ру.replace("RU:", "", 1).strip()
            вышло.append(ру if язык == "ru" else ен.strip())
        else:
            вышло.append(т)
    return вышло


def страница(модули: list, приложения: list) -> str:
    if not ВИДЖЕТ.exists():
        raise Отказ(f"нет канонического виджета {ВИДЖЕТ}")
    данные = {"modules": [], "apps": приложения}
    for м in модули:
        данные["modules"].append({
            "id": м.get("automation_id"), "name": м.get("name") or {}, "goal": м.get("business_goal") or "",
            "ok": bool(м.get("passport_ok")), "needs": м.get("needs") or [],
            "experts": [{"name": и, "what": (м.get("experts_what") or {}).get(и) or ""} for и in (м.get("experts") or [])],
            "limits": {"ru": _границы(м.get("limits"), "ru"), "en": _границы(м.get("limits"), "en")},
        })
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
function рисовать(){
  var С = СЛОВА[WLANG]; document.documentElement.lang = WLANG;
  el('title').textContent = С.title; el('help_btn').textContent = С.help;
  el('what').innerHTML = '<h2>' + э(С.what_h) + '</h2>' + С.what.map(function(p){ return '<p>' + э(p) + '</p>'; }).join('');
  var м = ДАННЫЕ.modules.map(function(m){
    var лимиты = (m.limits[WLANG] || []).map(function(l){ return '<li>' + э(l) + '</li>'; }).join('');
    var эксперты = m.experts.map(function(x){ return '<p><span class="метка">' + э(x.name) + '</span><br>' + э(x.what) + '</p>'; }).join('');
    return '<div class="карта"><b>' + э(t(m.name)) + '</b>' + (m.ok ? '' : '<span class="статус">' + э(С.no_passport) + '</span>') +
      '<p>' + э(m.goal) + '</p><h3>' + э(С.experts) + '</h3>' + эксперты +
      '<h3>' + э(С.limits) + '</h3><ul class="границы">' + лимиты + '</ul>' +
      (m.needs.length ? '<h3>' + э(С.needs) + '</h3><p class="нужно">' + э(m.needs.join(' · ')) + '</p>' : '') +
      '<div class="метка">' + э(m.id) + '</div></div>';
  }).join('');
  el('modules').innerHTML = '<h2>' + э(С.modules_h) + '</h2>' + (м ? '<div class="карты">' + м + '</div>' : '<p>' + э(С.modules_none) + '</p>');
  var а = ДАННЫЕ.apps.map(function(a){
    var ссылка = a.listing_id ? '<a href="/app-page/' + э(a.listing_id) + '/">' + э(t(a.name)) + '</a>' : э(t(a.name));
    return '<div class="карта"><b>' + ссылка + '</b><span class="статус">' + э(С.state[a.state] || a.state) + (a.version ? ' · ' + э(a.version) : '') + '</span>' +
      '<p>' + э(t(a.description)) + '</p><div class="метка">' + э(a.modules.join(', ')) + '</div></div>';
  }).join('');
  el('apps').innerHTML = '<h2>' + э(С.apps_h) + '</h2>' + (а ? '<div class="карты">' + а + '</div>' : '<p>' + э(С.apps_none) + '</p>');
  el('how').innerHTML = '<h2>' + э(С.how_h) + '</h2>' + С.how.map(function(p){ return '<p>' + э(p) + '</p>'; }).join('') +
    '<p class="тихо">' + э(С.repo) + '<a href="' + РЕПО + '/blob/main/APP_FROM_MODULES.md">APP_FROM_MODULES.md</a></p>';
}
document.addEventListener('DOMContentLoaded', function(){
  рисовать();
  el('help_btn').addEventListener('click', function(){ openHelp('app'); });
  helpFirstTime('app');
});
"""
    return (
        '<!DOCTYPE html><html lang="ru" data-lm="0"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_э(СЛОВА["ru"]["title"])}</title><style>{СТИЛЬ}</style></head><body>'
        f'<div class="лист"><header><h1 id="title">{_э(СЛОВА["ru"]["title"])}</h1>'
        '<button type="button" class="btn ghost sm" id="help_btn" data-help-key="app">? Как это работает</button></header>'
        '<section id="what"></section><section id="modules"></section><section id="apps"></section><section id="how"></section>'
        '<div class="тихо">Extella · полка собрана из реестра паспортов</div></div>'
        '<div id="xtl_help"><div><div id="xtl_help_body"></div></div></div>'
        f'<script>\nvar ДАННЫЕ = {_в_скрипт(данные)};\nvar СЛОВА = {_в_скрипт(СЛОВА)};\nvar РЕПО = {_в_скрипт(РЕПОЗИТОРИЙ)};\n'
        f'{ВИДЖЕТ.read_text(encoding="utf-8")}\nHELP = {_в_скрипт(help_)};\n{сценарий}</script></body></html>'
    )


def иконка(куда: pathlib.Path) -> str:
    if куда.exists():
        return "уже есть"
    for глиф in ("layers", "shapes"):
        try:
            р = subprocess.run([sys.executable, str(БРОНЗА), глиф, str(куда)], capture_output=True, text=True, timeout=120)
            if р.returncode == 0 and куда.exists():
                return глиф
        except Exception:
            pass
    raise Отказ("иконка не собралась: python3 tools/bronze_icon.py --список")


def собрать(папка: pathlib.Path, реестр: dict, каталог: pathlib.Path) -> dict:
    модули = модули_из_реестра(реестр)
    приложения = приложения_из_каталога(каталог)
    папка.mkdir(parents=True, exist_ok=True)
    (папка / "index.html").write_text(страница(модули, приложения), encoding="utf-8")
    старый = {}
    if (папка / "listing.json").exists():
        try:
            старый = json.loads((папка / "listing.json").read_text(encoding="utf-8"))
        except ValueError:
            старый = {}
    листинг = {
        "name": "Модули Extella",
        "описание": "Карта библиотеки модулей: из каких готовых узлов собираются приложения для сотрудников, "
                    "что каждый модуль делает и чего не делает, что ему нужно на компьютере, и какие приложения из "
                    "модулей уже стоят в магазине. Собирается из паспортов модулей.",
        "теги": ["инструмент", "каталог", "модули", "библиотека"], "иконка": "icon.png",
        "версия": старый.get("версия") or "0.1.0", "цена": 0, "права": [],
        "состояние": старый.get("состояние") or "собрано",
        "модулей": len(модули), "приложений": len(приложения),
    }
    for к in ("listing_id", "version_id"):
        if старый.get(к):
            листинг[к] = старый[к]
    (папка / "listing.json").write_text(json.dumps(листинг, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"модулей": len(модули), "приложений": len(приложения), "иконка": иконка(папка / "icon.png")}


def selftest() -> int:
    import tempfile
    ошибки = []
    реестр = {"automations": [
        {"automation_id": "toolkit_probe", "kind": "module", "name": {"ru": "Модуль «проба»", "en": "Probe module"},
         "business_goal": "проверка полки", "passport_ok": True, "needs": ["command: tesseract (желательно)"],
         "experts": ["toolkit_probe"], "experts_what": {"toolkit_probe": "читает пробу"},
         "limits": ["RU: наружу не пишет. EN: sends nothing out.", "<img src=x onerror=alert(1)>"]},
        {"automation_id": "app_x", "kind": "automation", "name": {"ru": "Не модуль", "en": "Not a module"}, "passport_ok": True},
    ]}
    with tempfile.TemporaryDirectory() as tmp:
        корень = pathlib.Path(tmp)
        (корень / "apps" / "probe_app").mkdir(parents=True)
        (корень / "apps" / "probe_app" / "app.json").write_text(json.dumps(
            {"slug": "probe_app", "name": {"ru": "Проба", "en": "Probe"}, "description": {"ru": "о", "en": "o"}, "modules": ["toolkit_probe"]}))
        (корень / "apps" / "probe_app" / "listing.json").write_text(json.dumps({"состояние": "опубликовано", "listing_id": "lst_1", "версия": "0.1.3"}))
        итог = собрать(корень / "shelf", реестр, корень / "apps")
        с = (корень / "shelf" / "index.html").read_text()
        if итог["модулей"] == 1 and итог["приложений"] == 1:
            print("  ✓ на полку попал модуль (kind: module) и приложение из каталога; автоматизация — нет")
        else:
            ошибки.append(f"счёт неверен: {итог}")
        # Ссылку на плитку рисует сценарий: в странице лежат данные приложения и адресная схема.
        for кусок, беда in (("xtl_help", "нет «? Как это работает»"), ('"listing_id": "lst_1"', "нет данных приложения для ссылки"),
                            ('"/app-page/', "сценарий не строит ссылку на плитку"),
                            ("nope", "нет блока «чего не обещаем»"), ("font-family:inherit", "кнопки наберутся Arial")):
            if кусок not in с:
                ошибки.append(беда)
        if "<img" in с.split("<script>")[0] or с.count("</script>") != 1:
            ошибки.append("содержимое паспорта попадает в страницу как разметка")
        for запретное in ("app-agent/run", "api.extella.ai", "X-Auth-Token"):
            if запретное in с:
                ошибки.append(f"полка без агента не должна содержать «{запретное}»")
        if not ошибки:
            print("  ✓ помощь, ссылка на приложение, экранирование, без вызовов платформы")
        import check_brand_copy
        ош, _ = check_brand_copy.check_text("полка", с, strict=True)
        if ош:
            ошибки.append("бренд: " + "; ".join(str(о) for о in ош[:3]))
        else:
            print("  ✓ палитра и слова полки проходят гейт бренда строго")
        import check_app_scopes, io, contextlib
        буфер = io.StringIO()
        with contextlib.redirect_stdout(буфер):
            код = check_app_scopes.проверить(корень / "shelf")
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
        итог = собрать(pathlib.Path(пути[0]).expanduser(), json.loads(реестр_путь.read_text(encoding="utf-8")), каталог)
    except Отказ as о:
        print(f"ОТКАЗ: {о}")
        return 1
    print(f"  ✓ полка собрана: модулей {итог['модулей']}, приложений {итог['приложений']}, иконка — {итог['иконка']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
