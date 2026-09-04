#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Окно приложения из плана экранов в пяти формах.

ЗАЧЕМ. Приложение из модулей (04.09.2026) не имеет своего интерфейса: модуль отдаёт только
экспертов. Окно приходится собирать, и до этого дня рендерера пяти форм для окна не было:
`в_отчёт.py` рисует статичную страницу-файл, а окно должно звать экспертов живьём и
показывать их ответ. Здесь один рендерер на обе задачи: экран со статичным содержимым и
экран с кнопкой, которая запускает эксперта модуля на компьютере покупателя и рисует
результат в одной из пяти форм. Второй рендерер под каждое приложение — это снова N×M.

Что окно умеет и чего не умеет — написано в самом окне кнопкой «? Как это работает»:
без блока «чего не обещаем» план не принимается (§3.20).

План — JSON, образец даёт `--пример`. Ключи английские (контракт машин), человеческий
текст в двух языках (§3.26). Экран: одна форма, либо `static` (готовое содержимое), либо
`action` (кнопка, эксперт, поля ввода и `map` — как ответ эксперта ложится в форму).

    python3 tools/окно_из_форм.py --план apps/priemka_schetov/app.json --в apps/priemka_schetov/index.html
    python3 tools/окно_из_форм.py --пример
    python3 tools/окно_из_форм.py --selftest

Коды выхода: 0 — окно собрано, 1 — отказ с названной причиной, 2 — план не прочитан.
"""
import argparse
import html
import json
import pathlib
import re
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ, ФОРМЫ, проверить  # noqa: E402

ВИДЖЕТ = СЮДА.parent / "templates" / "help_widget.js"
SLUG = re.compile(r"^[a-z][a-z0-9_]{2,30}$")
ВИДЫ_ВВОДА = ("text", "number")
# Что обязано быть в `map` для каждой формы. Списочные формы берут массив из ответа
# эксперта по ключу `from` и заполняют каждый пункт шаблонами вида «{поле}».
ШАБЛОН_ФОРМЫ = {
    "document": ("sections",),
    "number": ("value",),
    "list": ("rows",),
    "steps": ("steps",),
    "links": ("links",),
}

# Слова окна на двух языках. Свой переключатель языка запрещён каноном дизайна: язык
# приходит от хоста, а до его сообщения берётся язык браузера.
СЛОВА = {
    "ru": {
        "help": "? Как это работает", "run": "Запустить",
        "no_token": "Окно открыто не из магазина Extella: живые вызовы недоступны, показано только описание.",
        "no_device": "Устройство не определено: эксперт исполнится не на этом компьютере. Открой окно из приложения Extella.",
        "forbidden": "Разреши приложению запуск на устройстве в настройках покупки и повтори.",
        "failed": "Не получилось. Что ответила платформа:",
        "empty": "Ответ пустой. Перешли этот текст в чат Extella:",
        "done": "Готово",
    },
    "en": {
        "help": "? How it works", "run": "Run",
        "no_token": "This window was not opened from the Extella store: live calls are unavailable, only the description is shown.",
        "no_device": "The device is unknown: the expert will not run on this computer. Open the window from the Extella app.",
        "forbidden": "Allow the app to run on the device in the purchase settings and try again.",
        "failed": "It did not work. The platform answered:",
        "empty": "The answer is empty. Forward this text to the Extella chat:",
        "done": "Done",
    },
}

# Палитра и шрифты — ровно по правилу дизайна из AGENT_BUILD_GUIDE.md. Тёмная тема по
# умолчанию, светлая — атрибутом data-lm от хоста, как у окна ОС.
СТИЛЬ = """
:root{--bg:#0A0A0A;--s1:#141414;--s2:#181818;--ink:#F5F3EE;--silver:#8C8C8C;--accent:#D4944A;
  --petrol:#5FA8A0;--line:rgba(243,238,229,.09);--sans:Nunito,-apple-system,sans-serif}
:root[data-lm="1"]{--bg:#FAF9F5;--s1:#FFFFFF;--s2:#F5F3EC;--ink:#0A0A0A;--accent:#C57E33;
  --petrol:#2F6B66;--line:#D7E0DC}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);color:var(--ink);font:400 15px/1.6 var(--sans);padding:24px 24px 48px}
button,input,select,textarea{font-family:inherit}
.лист{max-width:960px;margin:0 auto}
header{display:flex;align-items:flex-start;gap:16px;margin-bottom:24px}
h1{font:600 26px/1.25 'Source Serif 4',Georgia,serif;flex:1}
.тихо{font:11px/1.6 'JetBrains Mono',ui-monospace,Menlo,monospace;color:var(--silver);margin-top:4px}
.btn{font-size:15px;font-weight:600;color:var(--bg);background:var(--accent);border:0;
  border-radius:999px;padding:12px 24px;cursor:pointer}
.btn.gold{color:#FFFFFF}
.btn[disabled]{opacity:.6;cursor:default}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.btn.sm{font-size:13px;padding:8px 16px}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
nav button{font-size:13px;font-weight:500;color:var(--ink);background:var(--s2);
  border:1px solid var(--line);border-radius:999px;padding:8px 16px;cursor:pointer}
nav button[aria-selected="true"]{background:var(--petrol);color:#FFFFFF;border-color:var(--petrol)}
section{display:none}
section[data-active="1"]{display:block}
h2{font:600 20px/1.3 'Source Serif 4',Georgia,serif;margin-bottom:12px}
.card{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
.ввод{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-bottom:16px}
.ввод label{display:block;font-size:13px;color:var(--silver);margin-bottom:4px}
.ввод input{width:100%;font-size:15px;color:var(--ink);background:var(--s2);border:1px solid var(--line);
  border-radius:8px;padding:8px 12px}
.ввод input:focus{outline:none;border-color:var(--accent)}
.статус{font-size:13px;color:var(--silver);margin:12px 0;white-space:pre-wrap;word-break:break-word}
.вывод{margin-top:16px}
.карты{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.карта{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px}
.карта b{display:block;font-size:15px;font-weight:600;margin-bottom:8px}
.карта dl{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px}
.карта dt{color:var(--silver)}
.карта dd{text-align:right}
.число{font:600 26px/1.2 'Source Serif 4',Georgia,serif;color:var(--accent);padding:24px;
  border:1px solid var(--accent);border-radius:12px;display:inline-block}
.шаг{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:8px}
.шаг i{color:var(--petrol);font-style:normal;font-weight:600;margin-right:8px}
.связь{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px;margin-bottom:8px}
.связь div{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:12px 16px}
.связь span{color:var(--petrol);font-size:13px;text-align:center}
.раздел{background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}
.раздел h3{font:600 15px/1.3 'Source Serif 4',Georgia,serif;color:var(--petrol);margin-bottom:8px}
.раздел p{font-size:13px;white-space:pre-wrap;word-break:break-word}
.подпись{color:var(--accent);font-size:13px;margin-bottom:8px}
#xtl_help{display:none;position:fixed;inset:0;z-index:9996;background:rgba(12,14,18,.55);overflow:auto;padding:32px 16px}
#xtl_help>div{max-width:720px;margin:0 auto;background:var(--s1);color:var(--ink);border-radius:12px;padding:24px}
"""

# Сценарий окна. Транспорт `run_expert` экрана не трогает нарочно: состояние ожидания
# показывает та функция, у которой есть кнопка, и гейт check_waiting_state узнаёт её по
# имени вызова — поэтому транспорт назван именно так.
СЦЕНАРИЙ = r"""
var APP_TOKEN = '{{app_token}}';
var DEVICE = '';
var WLANG = (navigator.language || 'ru').slice(0, 2) === 'en' ? 'en' : 'ru';
function el(id){ return document.getElementById(id); }
function э(v){ return String(v == null ? '' : v).replace(/[&<>"']/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function t(v){ if (v && typeof v === 'object' && !Array.isArray(v)) { return v[WLANG] || v.ru || v.en || ''; } return v == null ? '' : String(v); }
function слово(k){ return (СЛОВА[WLANG] || СЛОВА.ru)[k] || k; }

document.documentElement.setAttribute('data-lm',
  (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? '1' : '0');
window.addEventListener('message', function(e){
  var d = e && e.data; if (!d || typeof d !== 'object') return;
  if (d.type === 'etb_theme') {
    var светлая = d.theme === 'light' || d.light === true || d.lm === 1 || d.lm === '1';
    document.documentElement.setAttribute('data-lm', светлая ? '1' : '0');
  }
  if (d.type === 'etb_init') {
    DEVICE = String(d.device || d.target || d.device_id || (Array.isArray(d.targets) && d.targets[0]) || '');
    var lang = String(d.lang || d.language || '').slice(0, 2);
    if (lang === 'en' || lang === 'ru') { WLANG = lang; }
    перерисовать();
  }
});

function рисовать(д){
  var форма = д.form, куски = [];
  if (д.caption) { куски.push('<div class="подпись">' + э(t(д.caption)) + '</div>'); }
  if (форма === 'number') { куски.push('<div class="число">' + э(t(д.value)) + '</div>'); return куски.join(''); }
  if (форма === 'list') {
    куски.push('<div class="карты">');
    (д.rows || []).forEach(function(п){
      var поля = ''; var f = п.fields || {};
      Object.keys(f).forEach(function(к){ поля += '<dt>' + э(t(к)) + '</dt><dd>' + э(t(f[к])) + '</dd>'; });
      куски.push('<div class="карта"><b>' + э(t(п.name)) + '</b><dl>' + поля + '</dl></div>');
    });
    куски.push('</div>'); return куски.join('');
  }
  if (форма === 'steps') {
    (д.steps || []).forEach(function(п, i){
      куски.push('<div class="шаг"><i>' + (i + 1) + '</i>' + э(t(п.name)) + (п.caption ? ' — ' + э(t(п.caption)) : '') + '</div>');
    });
    return куски.join('');
  }
  if (форма === 'links') {
    (д.links || []).forEach(function(п){
      куски.push('<div class="связь"><div>' + э(t(п.from)) + '</div><span>→<br>' + э(t(п.caption || '')) + '</span><div>' + э(t(п.to)) + '</div></div>');
    });
    return куски.join('');
  }
  (д.sections || []).forEach(function(п){
    куски.push('<div class="раздел"><h3>' + э(t(п.name)) + '</h3><p>' + э(t(п.text)) + '</p></div>');
  });
  return куски.join('');
}

function значение(объект, путь){
  var v = объект;
  путь.split('.').forEach(function(к){ v = (v != null && typeof v === 'object') ? v[к] : undefined; });
  return v;
}
function подставить(шаблон, объект){
  if (шаблон && typeof шаблон === 'object' && !Array.isArray(шаблон)) { return t(шаблон); }
  return String(шаблон == null ? '' : шаблон).replace(/\{([\w.]+)\}/g, function(_, к){
    var v = значение(объект, к); return v == null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v));
  });
}
function по_карте(карта, ответ){
  var д = {form: карта.form, title: t(карта.title), caption: карта.caption ? t(карта.caption) : ''};
  if (карта.form === 'number') { д.value = подставить(карта.value, ответ); return д; }
  if (карта.form === 'document') {
    д.sections = (карта.sections || []).map(function(с){ return {name: t(с.name), text: подставить(с.text, ответ)}; });
    return д;
  }
  var ключ = {list: 'rows', steps: 'steps', links: 'links'}[карта.form];
  var описание = карта[ключ] || {};
  var массив = значение(ответ, описание.from || ключ);
  д[ключ] = (Array.isArray(массив) ? массив : []).map(function(п){
    var пункт = {};
    Object.keys(описание).forEach(function(к){
      if (к === 'from') return;
      if (к === 'fields') { пункт.fields = {}; Object.keys(описание.fields).forEach(function(имя){ пункт.fields[t(имя)] = подставить(описание.fields[имя], п); }); }
      else { пункт[к] = подставить(описание[к], п); }
    });
    return пункт;
  });
  return д;
}

function разобрать(сырой){
  var д = null;
  try { д = JSON.parse(сырой); } catch (e) { д = null; }
  var р = д && (д.result !== undefined ? д.result : д);
  if (р && typeof р === 'object' && р.result !== undefined && typeof р.result === 'string') { р = р.result; }
  if (typeof р === 'string') {
    var чинёный = р.replace(/'/g, '"').replace(/\bFalse\b/g, 'false').replace(/\bTrue\b/g, 'true').replace(/\bNone\b/g, 'null');
    try { р = JSON.parse(чинёный); } catch (e) { try { р = JSON.parse(р); } catch (e2) { р = null; } }
  }
  return р;
}

function run_expert(имя, параметры){
  var тело = {app_token: APP_TOKEN, expert_name: имя, params: параметры};
  if (DEVICE) { тело.targets = [DEVICE]; }
  return fetch('https://os.extella.ai/api/app-agent/run', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(тело)
  }).then(function(r){ return r.text().then(function(raw){ return {status: r.status, raw: raw}; }); });
}

function запустить(id){
  var экран = ЭКРАНЫ.filter(function(э_){ return э_.id === id; })[0];
  var кнопка = el('btn_' + id), статус = el('st_' + id), вывод = el('out_' + id);
  var параметры = {};
  (экран.action.inputs || []).forEach(function(в){
    var поле = el('in_' + id + '_' + в.name);
    параметры[в.name] = в.kind === 'number' ? Number(поле.value) : поле.value;
  });
  if (!APP_TOKEN || APP_TOKEN.charAt(0) === '{') { статус.textContent = слово('no_token'); return; }
  кнопка.disabled = true;
  статус.textContent = t(экран.waiting) + (DEVICE ? '' : ' ' + слово('no_device'));
  run_expert(экран.action.expert, параметры).then(function(о){
    var р = разобрать(о.raw);
    if (о.status === 403) { статус.textContent = слово('forbidden'); return; }
    if (!р || typeof р !== 'object') { статус.textContent = слово('empty') + ' ' + String(о.raw || '').slice(0, 400); return; }
    if (р.status === 'error' || р.ok === false) {
      статус.textContent = слово('failed') + ' ' + (р.message || р['почему'] || JSON.stringify(р)).slice(0, 600);
      return;
    }
    статус.textContent = слово('done');
    вывод.innerHTML = рисовать(по_карте(экран.action.map, р));
  }).catch(function(е){
    статус.textContent = слово('failed') + ' ' + String(е).slice(0, 200);
  }).finally(function(){
    кнопка.disabled = false;
  });
}

function показать(id){
  ЭКРАНЫ.forEach(function(э_){
    el('sec_' + э_.id).setAttribute('data-active', э_.id === id ? '1' : '0');
    el('tab_' + э_.id).setAttribute('aria-selected', э_.id === id ? 'true' : 'false');
  });
}

function перерисовать(){
  document.documentElement.lang = WLANG;
  el('title').textContent = t(ПЛАН.name);
  el('help_btn').textContent = слово('help');
  ЭКРАНЫ.forEach(function(э_){
    el('tab_' + э_.id).textContent = t(э_.title);
    el('h_' + э_.id).textContent = t(э_.title);
    if (э_.static) { el('out_' + э_.id).innerHTML = рисовать(э_.static); }
    if (э_.action) {
      el('btn_' + э_.id).textContent = t(э_.action.label);
      (э_.action.inputs || []).forEach(function(в){ el('lbl_' + э_.id + '_' + в.name).textContent = t(в.label); });
    }
  });
}

document.addEventListener('DOMContentLoaded', function(){
  перерисовать();
  показать(ЭКРАНЫ[0].id);
  el('help_btn').addEventListener('click', function(){ openHelp('app'); });
  helpFirstTime('app');
});
"""


def _э(т) -> str:
    return html.escape(str(т))


def _в_скрипт(объект) -> str:
    """JSON внутри <script>: «</» экранируется, иначе «</script>» в данных закроет сценарий."""
    return json.dumps(объект, ensure_ascii=False).replace("</", "<\\/")


def _двуязычно(значение, где: str) -> None:
    if not isinstance(значение, dict) or not str(значение.get("ru") or "").strip() \
            or not str(значение.get("en") or "").strip():
        raise Отказ(f"{где}: нужен текст на двух языках, объект вида {{\"ru\": …, \"en\": …}} (§3.26)")


def _по_русски(значение):
    """Двуязычный текст → русская строка, чтобы проверить содержимое словарём форм."""
    if isinstance(значение, dict) and ("ru" in значение or "en" in значение):
        return значение.get("ru") or значение.get("en")
    if isinstance(значение, dict):
        return {к: _по_русски(з) for к, з in значение.items()}
    if isinstance(значение, list):
        return [_по_русски(э) for э in значение]
    return значение


def проверить_план(план: dict) -> dict:
    """Строгая проверка плана: ошибка называет экран и поле."""
    if not isinstance(план, dict):
        raise Отказ("план должен быть объектом JSON")
    if not SLUG.match(str(план.get("slug") or "")):
        raise Отказ("slug: латиница, цифры и подчёркивание, от 3 до 31 знака, начинается с буквы")
    _двуязычно(план.get("name"), "name")
    _двуязычно(план.get("description"), "description")
    if not re.match(r"^(agent_[A-Za-z0-9_\-]{6,64}|USER_SELECTED)$", str(план.get("agent_id") or "")):
        raise Отказ("agent_id: стабильный id вида agent_… или USER_SELECTED")
    if not isinstance(план.get("modules"), list) or not план["modules"]:
        raise Отказ("modules: непустой список идентификаторов модулей из реестра")
    экраны = план.get("screens")
    if not isinstance(экраны, list) or not экраны:
        raise Отказ("screens: непустой список экранов")
    виденные = set()
    for i, э in enumerate(экраны):
        где = f"screens[{i}]"
        if not isinstance(э, dict) or not re.match(r"^[a-z][a-z0-9_]{0,30}$", str(э.get("id") or "")):
            raise Отказ(f"{где}.id: латиница, цифры и подчёркивание")
        if э["id"] in виденные:
            raise Отказ(f"{где}.id «{э['id']}» повторяется")
        виденные.add(э["id"])
        _двуязычно(э.get("title"), где + ".title")
        if э.get("form") not in ФОРМЫ:
            raise Отказ(f"{где}.form: одна из {', '.join(ФОРМЫ)}")
        if bool(э.get("static")) == bool(э.get("action")):
            raise Отказ(f"{где}: ровно одно из static (готовое содержимое) или action (кнопка)")
        if э.get("static"):
            статик = проверить(_по_русски(э["static"]))
            if статик["form"] != э["form"]:
                raise Отказ(f"{где}: форма экрана «{э['form']}» и форма содержимого «{статик['form']}» разные")
        else:
            д = э["action"]
            if not isinstance(д, dict):
                raise Отказ(f"{где}.action: объект")
            _двуязычно(д.get("label"), где + ".action.label")
            if not re.match(r"^[a-z][a-z0-9_]{2,63}$", str(д.get("expert") or "")):
                raise Отказ(f"{где}.action.expert: имя эксперта в snake_case")
            for j, в in enumerate(д.get("inputs") or []):
                if not isinstance(в, dict) or not re.match(r"^[a-z][a-z0-9_]{0,30}$", str(в.get("name") or "")):
                    raise Отказ(f"{где}.action.inputs[{j}].name: латиница и подчёркивание")
                _двуязычно(в.get("label"), f"{где}.action.inputs[{j}].label")
                if в.get("kind", "text") not in ВИДЫ_ВВОДА:
                    raise Отказ(f"{где}.action.inputs[{j}].kind: {' | '.join(ВИДЫ_ВВОДА)}")
            карта = д.get("map")
            if not isinstance(карта, dict) or карта.get("form") != э["form"]:
                raise Отказ(f"{где}.action.map: объект с form == «{э['form']}» — как ответ эксперта ложится в форму")
            _двуязычно(карта.get("title"), где + ".action.map.title")
            for поле in ШАБЛОН_ФОРМЫ[э["form"]]:
                if not карта.get(поле):
                    raise Отказ(f"{где}.action.map.{поле}: обязательно для формы «{э['form']}»")
            _двуязычно(э.get("waiting"), где + ".waiting")
    помощь = план.get("help")
    if not isinstance(помощь, dict):
        raise Отказ("help: объект с ru и en — текст кнопки «? Как это работает»")
    for язык in ("ru", "en"):
        блок = помощь.get(язык)
        if not isinstance(блок, dict):
            raise Отказ(f"help.{язык}: объект")
        for поле in ("title", "sub"):
            if not str(блок.get(поле) or "").strip():
                raise Отказ(f"help.{язык}.{поле}: непустая строка")
        for поле in ("steps", "sure", "nope", "who"):
            if not isinstance(блок.get(поле), list) or not [x for x in блок[поле] if str(x).strip()]:
                raise Отказ(f"help.{язык}.{поле}: непустой список — без честных границ (nope) окно не собирается (§3.20)")
    return план


def _help_js(план: dict) -> str:
    """Канонический виджет байт в байт из templates, а поверх — наши тексты."""
    if not ВИДЖЕТ.exists():
        raise Отказ(f"нет канонического виджета {ВИДЖЕТ} — окно без «? Как это работает» не собирается")
    help_ = {}
    for язык in ("ru", "en"):
        б = план["help"][язык]
        help_[язык] = {"icon": "", "title": б["title"], "sub": б["sub"], "steps": б["steps"],
                       "sure": б["sure"], "nope": б["nope"],
                       "who": {"title": {"ru": "Кто может раскрыть или откатить",
                                         "en": "Who can reveal the data or roll the change back"}[язык],
                               "items": б["who"]},
                       "extra": б.get("extra") or ""}
    return ВИДЖЕТ.read_text(encoding="utf-8") + "\nHELP = " + _в_скрипт({"app": help_}) + ";\n"


def страница(план: dict) -> str:
    план = проверить_план(план)
    куски = []
    навигация = "".join(
        f'<button type="button" id="tab_{_э(э["id"])}" role="tab" aria-selected="false" '
        f'onclick="показать(\'{_э(э["id"])}\')">{_э(э["title"]["ru"])}</button>'
        for э in план["screens"])
    for э in план["screens"]:
        внутри = ""
        if э.get("action"):
            поля = "".join(
                f'<div><label id="lbl_{_э(э["id"])}_{_э(в["name"])}" for="in_{_э(э["id"])}_{_э(в["name"])}">'
                f'{_э(в["label"]["ru"])}</label>'
                f'<input id="in_{_э(э["id"])}_{_э(в["name"])}" type="{"number" if в.get("kind") == "number" else "text"}" '
                f'value="{_э(в.get("default", ""))}"></div>'
                for в in (э["action"].get("inputs") or []))
            внутри = (f'<div class="ввод">{поля}</div>'
                      f'<button type="button" class="btn" id="btn_{_э(э["id"])}" '
                      f'onclick="запустить(\'{_э(э["id"])}\')">{_э(э["action"]["label"]["ru"])}</button>'
                      f'<div class="статус" id="st_{_э(э["id"])}"></div>')
        куски.append(f'<section id="sec_{_э(э["id"])}" data-active="0"><h2 id="h_{_э(э["id"])}">'
                     f'{_э(э["title"]["ru"])}</h2>{внутри}<div class="вывод" id="out_{_э(э["id"])}"></div></section>')
    экраны_js = _в_скрипт(план["screens"])
    план_js = _в_скрипт({"name": план["name"], "slug": план["slug"]})
    return (
        '<!DOCTYPE html><html lang="ru" data-lm="0"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_э(план["name"]["ru"])}</title><style>{СТИЛЬ}</style></head><body>'
        f'<div class="лист"><header><h1 id="title">{_э(план["name"]["ru"])}</h1>'
        '<button type="button" class="btn ghost sm" id="help_btn" data-help-key="app">? Как это работает</button>'
        f'</header><nav role="tablist">{навигация}</nav>{"".join(куски)}'
        f'<div class="тихо">Extella · {_э(план["slug"])}</div></div>'
        '<div id="xtl_help"><div><div id="xtl_help_body"></div></div></div>'
        f'<script>\nvar ПЛАН = {план_js};\nvar ЭКРАНЫ = {экраны_js};\nvar СЛОВА = '
        f'{_в_скрипт(СЛОВА)};\n{_help_js(план)}{СЦЕНАРИЙ}</script></body></html>'
    )


def пример_плана() -> dict:
    return {
        "slug": "probe_ocr",
        "name": {"ru": "Проба распознавания", "en": "OCR probe"},
        "description": {
            "ru": "Читает текст со скана или картинки на этом компьютере и показывает его в окне. Файл никуда не отправляется, нужен tesseract.",
            "en": "Reads text from a scan or image on this computer and shows it in the window. The file stays on the device, tesseract is required.",
        },
        "agent_id": "agent_XXXXXXXX",
        "modules": ["toolkit_ocr_read"],
        "screens": [
            {"id": "read", "title": {"ru": "Прочитать", "en": "Read"}, "form": "document",
             "waiting": {"ru": "Читаю на этом компьютере, это занимает до 20 секунд",
                         "en": "Reading on this computer, this takes up to 20 seconds"},
             "action": {"label": {"ru": "Прочитать файл", "en": "Read the file"},
                        "expert": "toolkit_ocr_read",
                        "inputs": [{"name": "path", "kind": "text", "default": "",
                                    "label": {"ru": "Путь к файлу на этом компьютере",
                                              "en": "Path to the file on this computer"}},
                                   {"name": "lang", "kind": "text", "default": "eng",
                                    "label": {"ru": "Язык распознавания", "en": "Recognition language"}}],
                        "map": {"form": "document", "title": {"ru": "Текст файла", "en": "File text"},
                                "sections": [{"name": {"ru": "Распознанный текст", "en": "Recognised text"},
                                              "text": "{text}"},
                                             {"name": {"ru": "Как прочитано", "en": "How it was read"},
                                              "text": "{read_by} · {lang} · {chars}"}]}}},
            {"id": "limits", "title": {"ru": "Границы", "en": "Limits"}, "form": "steps",
             "static": {"form": "steps", "title": {"ru": "Что модуль не делает", "en": "What the module does not do"},
                        "steps": [{"name": {"ru": "Не отправляет файл наружу", "en": "Sends nothing out"}},
                                  {"name": {"ru": "Не ставит программы без разрешения",
                                            "en": "Installs nothing without permission"}}]}},
        ],
        "help": {
            "ru": {"title": "Как работает проба распознавания", "sub": "Текст со скана без отправки файла наружу",
                   "steps": ["Ты указываешь путь к файлу", "Модуль читает его на этом компьютере", "Текст появляется в окне"],
                   "sure": ["Файл и текст остаются на устройстве"],
                   "nope": ["Не разбирает поля счёта: только текст", "Без языкового пакета отказывается, а не выдаёт мусор"],
                   "who": ["Владелец компьютера: файлы остаются у него"]},
            "en": {"title": "How the OCR probe works", "sub": "Text from a scan without sending the file out",
                   "steps": ["You give the file path", "The module reads it on this computer", "The text appears in the window"],
                   "sure": ["The file and the text stay on the device"],
                   "nope": ["Does not parse invoice fields: text only", "Without a language pack it refuses instead of producing garbage"],
                   "who": ["The computer owner: the files stay with them"]},
        },
    }


def selftest() -> int:
    ошибки = []
    try:
        с = страница(пример_плана())
    except Отказ as о:
        print(f"  ✗ пример не собрался: {о}")
        return 1
    print("  ✓ пример плана собирается в окно")
    нужно = {"xtl_help": "нет контейнера «? Как это работает»", "app-agent/run": "нет живого вызова эксперта",
             "{{app_token}}": "нет подстановки app_token", "targets = [DEVICE]": "нет закрепления за устройством",
             "font-family:inherit": "кнопки наберутся Arial", "nope": "нет блока «чего не обещаем»"}
    for кусок, беда in нужно.items():
        if кусок not in с:
            ошибки.append(беда)
    for запретное in ("api.extella.ai", "X-Auth-Token", "auth_token"):
        if запретное in с:
            ошибки.append(f"в окне есть «{запретное}» — токен ядра на странице запрещён")
    if not ошибки:
        print("  ✓ окно зовёт эксперта через app-agent/run, несёт помощь и не несёт токенов ядра")

    # Ожидание видно: гейт check_waiting_state читает страницу как чужую.
    sys.path.insert(0, str(СЮДА))
    import check_waiting_state
    беды = check_waiting_state.проверить_текст(с)
    if беды:
        ошибки.append("ожидание не видно: " + "; ".join(б for _, б in беды))
    else:
        print("  ✓ у кнопки видно ожидание: включается до вызова, снимается в finally, есть слова")

    import check_brand_copy
    ош, _ = check_brand_copy.check_text("окно", с, strict=True)
    if ош:
        ошибки.append("бренд: " + "; ".join(str(о) for о in ош[:3]))
    else:
        print("  ✓ палитра и слова окна проходят гейт бренда строго")

    зло = пример_плана()
    зло["screens"][1]["static"]["steps"][0]["name"] = {"ru": "<img src=x onerror=alert(1)>", "en": "x"}
    зло["name"]["ru"] = "<script>alert(1)</script>"
    с2 = страница(зло)
    тело = с2[с2.index("<body>"):]
    # Содержимое экрана уходит в JSON внутри <script> и рисуется через э(); в разметке
    # тега быть не должно, а «</script>» из данных не должен закрывать сценарий.
    if "<img" in тело.split("<script>")[0] or тело.count("</script>") != 1:
        ошибки.append("содержимое плана попадает в страницу как разметка")
    else:
        print("  ✓ содержимое плана экранируется")

    for сломать, код in ((lambda п: п["help"]["ru"].__setitem__("nope", []), "help без nope"),
                         (lambda п: п["screens"][0].__setitem__("form", "table"), "форма вне словаря"),
                         (lambda п: п["screens"][0]["action"].pop("map"), "кнопка без map"),
                         (lambda п: п.__setitem__("name", {"ru": "Только русский"}), "имя на одном языке")):
        п = пример_плана()
        сломать(п)
        try:
            страница(п)
            ошибки.append(f"{код} — НЕ поймано")
        except Отказ:
            print(f"  ✓ {код} — поймано")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main(аргументы) -> int:
    р = argparse.ArgumentParser(description="План экранов в пяти формах → окно приложения")
    р.add_argument("--план", help="JSON с планом")
    р.add_argument("--в", help="куда записать index.html")
    р.add_argument("--пример", action="store_true", help="напечатать образец плана")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args(аргументы)
    if а.selftest:
        return selftest()
    if а.пример:
        print(json.dumps(пример_плана(), ensure_ascii=False, indent=2))
        return 0
    if not а.план:
        р.print_help()
        return 0
    try:
        план = json.loads(pathlib.Path(а.план).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ОТКАЗ: план не прочитан: {exc}", file=sys.stderr)
        return 2
    try:
        с = страница(план)
    except Отказ as о:
        print(f"ОТКАЗ: {о}", file=sys.stderr)
        return 1
    куда = pathlib.Path(а.в or pathlib.Path(а.план).parent / "index.html")
    куда.parent.mkdir(parents=True, exist_ok=True)
    куда.write_text(с, encoding="utf-8")
    print(f"  ✓ окно собрано: {куда} ({куда.stat().st_size // 1024} КБ), экранов {len(план['screens'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
