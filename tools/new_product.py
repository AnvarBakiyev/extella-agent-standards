#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Каркас нового продукта Extella: генератор (№28 бэклога) + манифест зависимостей (№29).

ЗАЧЕМ. Неделя 03–04.08 показала: беды продуктов растут не из бизнес-логики, а из того,
что каждый продукт сам решал одни и те же вопросы — какой агент, какой скоуп, какое
устройство, как падать, как ставиться. Девятый продукт, начатый с пустого файла,
повторит все грабли восьми предыдущих. Каркас отвечает на эти вопросы С РОЖДЕНИЯ:
канонная обвязка платформы, выбор агента человеком, закрепление за устройством,
честные ошибки, паспорт, манифест зависимостей, панель по канону дизайна и смоук.

Канонные модули (platform_client, agent_onboarding) НЕ хранятся в шаблоне — они
копируются ЖИВЫМИ из канона при генерации. Урок 03.08: пак с собственными копиями
превратился в машину отката (29 из 30 копий устарели). Шаблон, несущий копию, рано
или поздно раздаёт старьё; шаблон, читающий канон, — никогда.

Запуск:
  python3 tools/new_product.py <slug> "<Название>" "<кому-в-дательном>" <порт> [каталог]
  python3 tools/new_product.py --selftest        # сгенерировать пробный и прогнать гейты

Пример:
  python3 tools/new_product.py docflow "Документооборот" "документообороту" 8797

Коды выхода: 0 — сгенерировано (или самопроверка прошла), 1 — отказ с причиной.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CANON_APP = Path.home() / "Documents/Extella/extella-recruiting-agent/app"
STANDARDS = Path(__file__).resolve().parents[1]

# ── Шаблоны ────────────────────────────────────────────────────────────────────
# Плейсхолдеры: __SLUG__, __NAME_RU__, __DAT_RU__, __PORT__. Никаких f-строк:
# в шаблонах живут фигурные скобки кода и CSS.

SERVER_PY = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""__NAME_RU__ — локальная панель Extella (127.0.0.1:__PORT__).

Маршруты: / — панель; /x/* — JSON API. Обвязка платформы — канонный platform_client
(копия сверяется гейтом стандартов), выбор агента — канонный agent_onboarding.
"""
import json
import os
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_onboarding                                    # noqa: E402
import platform_client                                     # noqa: E402

PORT = __PORT__
HERE = Path(__file__).resolve().parent

agent_onboarding.configure(
    product_ru="__DAT_RU__", product_en="__SLUG__", role_ru="__DAT_RU__",
    brain_ru="Агент — это мозг, который выполняет работу продукта.",
    brain_en="The agent is the brain doing the product's work.",
    binding_file=Path.home() / "extella___SLUG__" / "agent_binding.json",
)
platform_client.configure(binding_file=Path.home() / "extella___SLUG__" / "agent_binding.json",
                          product_ru="__DAT_RU__", cfg_keys=("__SLUG___agent_id",))


def agent_id_or_fail():
    try:
        return platform_client.bound_agent()
    except platform_client.PlatformError as e:
        raise agent_onboarding.AgentSetupError(str(e))


# Платформенные помощники НЕ дублируются: канонные list_agents/smoke/copy_base_qwen/
# delete_agent живут в platform_client и доказаны живьём Рекрутёром. Дубль в шаблоне
# разъехался бы с каноном в первый же месяц (адверсарный круг поймал это ещё до
# коммита: копия pf_smoke уже отставала от юриста).

# ── Обработчики панели ────────────────────────────────────────────────────────
def h_agent_screen(_):
    return {"status": "success", **agent_onboarding.build_screen(platform_client.list_agents)}


def h_agent_choose(body):
    binding = agent_onboarding.choose(str(body.get("agent_id") or ""),
                                      platform_client.list_agents, platform_client.smoke)
    return {"status": "success", "binding": binding}


def h_agent_create(_):
    binding = agent_onboarding.create(platform_client.copy_base_qwen, platform_client.smoke,
                                      platform_client.delete_agent)
    return {"status": "success", "binding": binding}


def h_agent_forget(_):
    return {"status": "success", "had_binding": agent_onboarding.forget_binding()}


def h_status(_):
    """Статус продукта: привязка и устройство. Платформу зря не дёргаем."""
    binding = agent_onboarding.load_binding() or {}
    return {"status": "success", "agent": binding.get("agent_id") or "",
            "agent_name": binding.get("agent_name") or "",
            "device": platform_client.my_device()[:8]}


def h_ping(_):
    """Пробный запуск эксперта продукта: скоуп агента + своё устройство + deferred."""
    r = platform_client.run_expert("__SLUG___ping", {}, timeout=120)
    # «running» и «failed» — не успех: недожатое не имеет права выглядеть сделанным.
    if not isinstance(r, dict) or r.get("status") in ("error", "failed", "running"):
        msg = (r.get("message") or r.get("error") or str(r)[:150]) if isinstance(r, dict) else str(r)[:150]
        return {"status": "error", "message": msg}
    return {"status": "success", "answer": r.get("answer", "")}


ROUTES = {"/x/agent_screen": h_agent_screen, "/x/agent_choose": h_agent_choose,
          "/x/agent_create": h_agent_create, "/x/agent_forget": h_agent_forget,
          "/x/status": h_status, "/x/ping": h_ping}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            page = (HERE / "index.html").read_bytes()
            return self._send(200, page, "text/html; charset=utf-8")
        self._send(404, {"error": "unknown path"})

    def do_POST(self):
        path = self.path.split("?")[0]
        ln = int(self.headers.get("Content-Length", 0) or 0)
        try:
            body = json.loads(self.rfile.read(ln).decode("utf-8")) if ln else {}
        except Exception:
            body = {}
        fn = ROUTES.get(path)
        if not fn:
            return self._send(404, {"error": "unknown route"})
        try:
            self._send(200, fn(body))
        except agent_onboarding.AgentSetupError as e:
            # отсутствие выбора — вопрос человеку, а не крах
            self._send(200, {"status": "error", "needs_agent": True, "message": str(e)[:300]})
        except platform_client.PlatformError as e:
            self._send(200, {"status": "error", "message": str(e)[:300]})
        except Exception as e:
            self._send(200, {"status": "error", "message": str(e)[:300]})


if __name__ == "__main__":
    print("__NAME_RU__ on http://127.0.0.1:%d/" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
'''

INDEX_HTML = '''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME_RU__</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root{--ink:#1F2937;--paper:#FAF9F6;--gold:#C9A227;--petrol:#0F4C5C;--divider:#E5E1D8;--muted:#6B7280}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Nunito',ui-sans-serif,sans-serif;background:var(--paper);color:var(--ink);font-size:15px;line-height:1.5}
button,input,select,textarea{font-family:inherit;font-size:inherit}
.wrap{max-width:720px;margin:0 auto;padding:24px}
h1{font-size:20px;font-weight:700;margin-bottom:4px}
.sub{font-size:13px;color:var(--muted);margin-bottom:24px}
.card{background:#fff;border:1px solid var(--divider);border-radius:12px;padding:16px;margin-bottom:16px}
.btn{display:inline-block;border:1px solid var(--petrol);background:var(--petrol);color:#fff;
     border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:600}
.btn.sec{background:#fff;color:var(--petrol)}
.pill{display:inline-block;border:1px solid var(--divider);border-radius:999px;padding:4px 12px;
      font-size:13px;margin-right:8px}
.err{color:#8A2D2D;font-size:13px;margin-top:8px;min-height:16px}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>__NAME_RU__</h1>
  <div class="sub">Каркас продукта Extella. Выбери агента — и проверь связь одной кнопкой.</div>

  <div class="card" id="agentCard">
    <div id="agentPills"><span class="pill">Агент: <b id="agentName">…</b></span>
      <span class="pill">Устройство: <span class="mono" id="devId">…</span></span></div>
    <div style="margin-top:12px">
      <button class="btn sec" onclick="chooseAgent()">Выбрать агента</button>
      <button class="btn sec" onclick="createAgent()">Создать своего</button>
    </div>
    <div class="err" id="agentError"></div>
  </div>

  <div class="card">
    <button class="btn" onclick="ping()">Проверить связь</button>
    <div class="err" id="pingOut"></div>
  </div>
</div>
<script>
// Паспорт заявляет ru+en — заявка обязана быть правдой: словарь, а не строчка в yaml.
const T={ru:{none:'не выбран',check:'проверяю…',ans:'ответ агента: ',ready:'готов',fail:'не получилось',
 pick:'Пригодные агенты:',paste:'Вставь id выбранного:'},
 en:{none:'not selected',check:'checking…',ans:'agent answered: ',ready:'ready',fail:'did not work',
 pick:'Suitable agents:',paste:'Paste the chosen id:'}};
let L=(navigator.language||'ru').startsWith('ru')?'ru':'en';
function tr(k){return T[L][k];}
async function post(p, b){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json();}
async function loadStatus(){const s=await post('/x/status',{});
 document.getElementById('agentName').textContent=s.agent_name||s.agent||tr('none');
 document.getElementById('devId').textContent=s.device||'—';}
async function chooseAgent(){const s=await post('/x/agent_screen',{});
 const list=(s.suitable||[]).map(a=>a.name+' ['+a.id+']').join('\\n');
 const id=prompt(tr('pick')+'\\n'+list+'\\n\\n'+tr('paste'));
 if(!id)return;
 const r=await post('/x/agent_choose',{agent_id:id.trim()});
 document.getElementById('agentError').textContent=r.status==='success'?(r.warning||''):(r.message||tr('fail'));
 loadStatus();}
async function createAgent(){const r=await post('/x/agent_create',{});
 document.getElementById('agentError').textContent=r.status==='success'?(r.warning||''):(r.message||tr('fail'));
 loadStatus();}
async function ping(){document.getElementById('pingOut').textContent=tr('check');
 const r=await post('/x/ping',{});
 document.getElementById('pingOut').textContent=r.status==='success'?(tr('ans')+(r.answer||tr('ready'))):(r.message||tr('fail'));}
loadStatus();
</script>
</body>
</html>
'''

PING_EXPERT = '''# expert: __SLUG___ping
# description: __NAME_RU__: пробный эксперт каркаса — отвечает «готов» без внешних вызовов. Параметры: нет.

def __SLUG___ping() -> str:
    import json
    return json.dumps({"status": "success", "answer": "готов"}, ensure_ascii=False)
'''

PASSPORT_YAML = '''# Agent Passport Extella — «__NAME_RU__» (создан каркасом new_product).
#
# Паспорт честный С РОЖДЕНИЯ: описывает то, что продукт реально умеет сейчас, —
# один пробный эксперт. Наращивая способности, дописывай их сюда ПО ФАКТУ; проверка:
#   python3 ~/Documents/Extella/extella-agent-standards/tools/check_agent_passport.py agent_passport.yaml
---
agent:
  name: "Extella | __NAME_RU__"
  platform_agent_id: "by_user"          # агента выбирает пользователь на первом экране
  binding_ui: "app/agent_onboarding.py"
  owner: "Анвар (CEO Extella)"
  business_goal: "Каркас продукта: выбор агента пользователем и пробный запуск «готов».
    Замени эту цель настоящей, когда добавишь первую бизнес-способность."
  model_profile: "qwen-3.7"
  version: "0.1.0"
  languages: ["ru", "en"]      # панель двуязычная с рождения (словарь T в index.html)
  hosting_profile: "client_server"      # локальная панель 127.0.0.1:__PORT__ + эксперты на устройстве
  data_classification: "none_yet"       # данных пока не обрабатывает — поменяй при первой способности
  immutable_bundle_id: "skeleton-__SLUG__"

capabilities:
  - name: "ping"
    version: "0.1.0"
    what: "Пробный запуск: агент отвечает «готов» — доказывает привязку, скоуп и устройство"
    inputs: "нет"
    outputs: "строка ответа агента"
    help_surface: "кнопка «Проверить связь» на панели; ошибка объясняет, что сделать"
    limits:
      - "НЕ делает никакой бизнес-работы: единственная проверка живости привязки"
      - "внешних вызовов, кроме api.extella.ai, нет; писем и записи наружу нет"
      - "недожатый запуск честно показывается ошибкой, не успехом"

permissions:
  can_send_external: false              # писем и внешней записи нет; появятся — только черновиками
  can_delete_platform_objects: false

budgets:
  max_runs_per_day: 200
  max_tokens_per_run: 4000
  max_delegation_depth: 1
  max_duration_ms: 120000
  max_llm_tokens: 4000
  max_external_actions: 0               # внешних действий у каркаса нет

operations:
  rollback: "выбор агента обратим: «забыть» на панели (/x/agent_forget) возвращает
    первый экран; эксперты перерегистрируются идемпотентно (expert/save перезаписывает),
    прежняя версия — git checkout предыдущего тега продукта + повторная установка"
'''

MANIFEST_YAML = '''# Манифест зависимостей «__NAME_RU__» (№29): всё, что продукт ждёт от машины.
#
# Урок 03.08: зависимость, не названная здесь, проверяется в момент ПАДЕНИЯ у коллеги
# («Ollama недоступен», «runtime не установлен») — днём слепой переписки. Названная —
# проверяется установщиком и диагностикой ДО первого использования.
#
# Формат проверки: kind — python|file|port; честный текст — что сделать человеку.
checks:
  - kind: python
    min_version: "3.10"
    fix_ru: "поставь Python 3.10+ (python.org или пакетный менеджер)"
  - kind: file
    path: "~/.extella/api_token.txt"
    level: warn            # без него панель честно попросит войти в Extella
    fix_ru: "открой приложение Extella и войди в аккаунт — файл появится сам"
  - kind: port
    port: __PORT__
    fix_ru: "порт занят другим процессом — закрой его или поменяй порт продукта"
'''

INSTALL_PY = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установка «__NAME_RU__» на это устройство (дев-канал; коллегам продукт раздаёт пак).

Шаги: манифест зависимостей → копия панели в ~/extella-plugins/__SLUG__/ →
регистрация экспертов → карточка. Каждый шаг говорит правду: «ok» печатается только
после проверки, провал называет причину и что делать.
"""
import io
import json
import os
import shutil
import socket
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGROOT = os.path.expanduser("~/extella-plugins/__SLUG__")


# python.org-питоны часто БЕЗ CA-сертификатов (инцидент 24.07): без этого первый же
# запрос к платформе умирает «Нет связи» при живом интернете.
def _ssl_bootstrap():
    try:
        import ssl as _ssl
        _p = _ssl.get_default_verify_paths()
        ok = (_p.cafile and os.path.isfile(_p.cafile)) or (_p.capath and os.path.isdir(_p.capath))
        if not ok:
            import certifi
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except Exception:
        pass


_ssl_bootstrap()


def check_manifest() -> bool:
    """№29: зависимости проверяются ЗДЕСЬ, а не в момент падения у коллеги."""
    import re
    raw = io.open(os.path.join(HERE, "MANIFEST.yaml"), encoding="utf-8").read()
    ok = True
    for m in re.finditer(r"- kind: (\\w+)\\n((?:    .+\\n)+)", raw):
        kind, block = m.group(1), m.group(2)

        def field(name):
            f = re.search(r"%s: [\\"']?([^\\"'\\n]+)" % name, block)
            # хвостовой комментарий — не значение: "warn   # пояснение" это warn
            return f.group(1).split("#")[0].strip() if f else ""
        fix = field("fix_ru")
        warn_only = field("level") == "warn"
        if kind == "python":
            need = tuple(int(x) for x in field("min_version").split("."))
            good = sys.version_info[:2] >= need
        elif kind == "file":
            good = os.path.exists(os.path.expanduser(field("path")))
        elif kind == "port":
            s = socket.socket()
            s.settimeout(0.4)
            try:
                good = s.connect_ex(("127.0.0.1", int(field("port")))) != 0   # свободен = хорошо
            finally:
                s.close()
        else:
            print("  ~ манифест: неизвестная проверка", kind)
            continue
        mark = "ok" if good else ("~" if warn_only else "FAIL")
        print("  %s %s%s" % (mark, kind, "" if good else " — " + fix))
        if not good and not warn_only:
            ok = False
    return ok


def main() -> int:
    print("== Манифест зависимостей ==")
    if not check_manifest():
        print("Зависимости не готовы — установка остановлена (см. строки FAIL).")
        return 1

    print("== Панель ==")
    os.makedirs(PLUGROOT, exist_ok=True)
    for rel in ("app/server.py", "app/index.html", "app/platform_client.py",
                "app/agent_onboarding.py"):
        src = os.path.join(HERE, rel)
        if not os.path.exists(src):
            # Молча пропустить модуль = мёртвая панель у коллеги при зелёной установке.
            print("  FAIL: в пакете нет обязательного файла", rel)
            return 1
        shutil.copyfile(src, os.path.join(PLUGROOT, os.path.basename(rel)))
        print("  ok", os.path.basename(rel))

    print("== Эксперты ==")
    sys.path.insert(0, os.path.join(HERE, "app"))
    import agent_onboarding                                 # noqa: E402
    import platform_client                                  # noqa: E402
    # Регистрация без X-Agent-Id — это HTTP 422 у платформы (поймано адверсарным
    # кругом): скоуп нужен всегда. Привязка есть — её агент; нет — пробный
    # платформенный (global:true делает экспертов видимыми через run_expert).
    try:
        reg_agent = platform_client.bound_agent()
    except platform_client.PlatformError:
        reg_agent = agent_onboarding.PLATFORM_TRIAL_ID
    ok = True
    for f in sorted(Path(HERE, "experts").glob("*.py")):
        src_text = f.read_text(encoding="utf-8")
        desc = ""
        for line in src_text.splitlines()[:6]:
            if line.startswith("# description:"):
                desc = line.split(":", 1)[1].strip()
        try:
            platform_client.xapi("/api/expert/save",
                                 {"name": f.stem, "code": src_text,
                                  "description": desc or f.stem, "global": True},
                                 timeout=90, agent_id=reg_agent)
            print("  ok", f.stem)
        except platform_client.PlatformError as e:
            print("  FAIL", f.stem, "—", str(e)[:120])
            ok = False
    if not ok:
        print("Эксперты не встали — панель поставлена, но запуски будут отказывать честно.")
        return 1
    print("Готово. Панель: ~/extella-plugins/__SLUG__/ (запуск: python3 server.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

SMOKE_PY = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Смоук «__NAME_RU__»: сервер поднимается, договор UI↔сервер соблюдён, гейты зелёные.

Канон: смоук гонится У КОЛЛЕГИ (или на чистой машине) — на машине автора он зелёный
всегда. Коды выхода: 0 — жив, 1 — причина названа.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = __PORT__


def main() -> int:
    proc = subprocess.Popen([sys.executable, str(HERE / "app" / "server.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.time() + 10
        alive = False
        while time.time() < deadline:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/" % PORT, timeout=2) as r:
                    alive = r.status == 200
                    break
            except Exception:
                time.sleep(0.5)
        if not alive:
            err = (proc.stderr.read() or b"").decode("utf-8", "replace")[-400:]
            print("FAIL: сервер не поднялся за 10с.", err)
            return 1
        req = urllib.request.Request("http://127.0.0.1:%d/x/status" % PORT,
                                     data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            st = json.loads(r.read().decode("utf-8"))
        if st.get("status") != "success":
            print("FAIL: /x/status ответил нечестно:", st)
            return 1
        print("ok: сервер жив, /x/status отвечает; агент:", st.get("agent") or "не выбран")
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
'''

README_MD = '''# __NAME_RU__

Продукт создан каркасом `extella-agent-standards/tools/new_product.py` (№28).

## Что уже правильно с рождения
- **Обвязка платформы** — канонный `app/platform_client.py`: токен, привязка, скоуп,
  закрепление за устройством, честные ошибки, deferred. Копия сверяется гейтом —
  не правь её на месте, правь канон в extella-recruiting-agent и раскатывай.
- **Агента выбирает пользователь** — канонный `app/agent_onboarding.py`, паспорт
  заявляет `platform_agent_id: by_user`.
- **Манифест зависимостей** (`MANIFEST.yaml`) — всё, что продукт ждёт от машины,
  проверяется установщиком ДО первого использования, а не в момент падения.
- **Панель по канону дизайна** — шкалы кеглей/радиусов/отступов, «ты», без теней.
  Проверка: `python3 ~/Documents/Extella/extella-toolbar-src/tools/check_panel_canon.py app/index.html`.
- **Честные исходы** — `running`/`failed` никогда не показываются успехом.

## Правила роста
1. Новая способность → эксперт в `experts/` + способность в `agent_passport.yaml` ПО ФАКТУ.
2. Новая зависимость машины → строка в `MANIFEST.yaml` с текстом «что сделать человеку».
3. Письма и внешняя запись — только черновиками, отправляет человек.
4. Смоук `smoke_e2e.py` гонится у коллеги, не у автора.
5. Раздача — через extella-marketplace-pack (`publish_pack.sh`), не руками.
'''


def generate(slug: str, name_ru: str, dat_ru: str, port: int, dest: Path, register: bool = True) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,30}", slug):
        raise SystemExit("slug — латиница/цифры/подчёркивание, 3–31 символ: %r" % slug)
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit("каталог %s не пуст — каркас не затирает чужое" % dest)
    for canon in ("platform_client.py", "agent_onboarding.py"):
        if not (CANON_APP / canon).exists():
            raise SystemExit("канона нет: %s — каркас без живого канона не генерирует" % (CANON_APP / canon))

    def fill(t: str) -> str:
        return (t.replace("__SLUG__", slug).replace("__NAME_RU__", name_ru)
                .replace("__DAT_RU__", dat_ru).replace("__PORT__", str(port)))

    (dest / "app").mkdir(parents=True, exist_ok=True)
    (dest / "experts").mkdir(exist_ok=True)
    (dest / "app" / "server.py").write_text(fill(SERVER_PY), encoding="utf-8")
    (dest / "app" / "index.html").write_text(fill(INDEX_HTML), encoding="utf-8")
    (dest / "experts" / (slug + "_ping.py")).write_text(fill(PING_EXPERT), encoding="utf-8")
    (dest / "agent_passport.yaml").write_text(fill(PASSPORT_YAML), encoding="utf-8")
    (dest / "MANIFEST.yaml").write_text(fill(MANIFEST_YAML), encoding="utf-8")
    (dest / "install.py").write_text(fill(INSTALL_PY), encoding="utf-8")
    (dest / "smoke_e2e.py").write_text(fill(SMOKE_PY), encoding="utf-8")
    (dest / "README.md").write_text(fill(README_MD), encoding="utf-8")
    # канонные модули — ЖИВЫМИ из канона, не из шаблона
    shutil.copy(CANON_APP / "platform_client.py", dest / "app" / "platform_client.py")
    shutil.copy(CANON_APP / "agent_onboarding.py", dest / "app" / "agent_onboarding.py")
    if register:
        # Порождённый продукт сам встаёт под гейты копий: без этого изменение канона
        # гнило бы в нём молча — тот самый класс «машина отката», третий раз не надо.
        regf = STANDARDS / "product_registry.txt"
        lines = regf.read_text(encoding="utf-8").splitlines() if regf.exists() else [
            "# Продукты, порождённые каркасом new_product.py: гейты копий читают этот список."]
        if str(dest) not in lines:
            lines.append(str(dest))
            regf.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print("Продукт записан в реестр гейтов: %s" % regf)
    print("Каркас «%s» создан: %s" % (name_ru, dest))
    print("Дальше: python3 %s/smoke_e2e.py — и первый эксперт в experts/." % dest)


def selftest() -> int:
    """Сгенерировать пробный продукт и прогнать по нему настоящие гейты."""
    import ast
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "probe_product"
    generate("probeprod", "Пробный продукт", "пробному продукту", 8917, tmp, register=False)
    bad = 0

    for py in list(tmp.rglob("*.py")):
        try:
            ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print("  ✗ синтаксис:", py.name, e)
            bad += 1
    print("  ✓ все .py разбираются" if not bad else "")

    r = subprocess.run([sys.executable, str(STANDARDS / "tools" / "check_agent_passport.py"),
                        str(tmp / "agent_passport.yaml")], capture_output=True, text=True)
    if r.returncode != 0:
        print("  ✗ паспорт каркаса не проходит гейт:\n" + (r.stdout + r.stderr)[-600:])
        bad += 1
    else:
        print("  ✓ паспорт проходит гейт стандартов")

    canon_gate = Path.home() / "Documents/Extella/extella-toolbar-src/tools/check_panel_canon.py"
    if canon_gate.exists():
        r = subprocess.run([sys.executable, str(canon_gate), str(tmp / "app" / "index.html")],
                           capture_output=True, text=True)
        if "✕" in r.stdout:
            print("  ✗ панель каркаса вне канона дизайна:\n" + r.stdout[-600:])
            bad += 1
        else:
            print("  ✓ панель проходит канон дизайна")

    contract = STANDARDS / "tools" / "check_ui_api_contract.py"
    r = subprocess.run([sys.executable, str(contract), str(tmp), "1"], capture_output=True, text=True)
    if "✗" in r.stdout:
        print("  ✗ договор UI↔сервер каркаса расходится:\n" + r.stdout[-400:])
        bad += 1
    else:
        print("  ✓ договор UI↔сервер соблюдён")

    r = subprocess.run([sys.executable, str(tmp / "smoke_e2e.py")], capture_output=True, text=True)
    if r.returncode != 0:
        print("  ✗ смоук:", (r.stdout + r.stderr)[-400:])
        bad += 1
    else:
        print("  ✓ смоук: " + r.stdout.strip())

    shutil.rmtree(tmp.parent, ignore_errors=True)
    if bad:
        print("\nКАРКАС НЕИСПРАВЕН: %d" % bad)
        return 1
    print("\nКаркас порождает продукт, проходящий все гейты с рождения.")
    return 0


def main(argv) -> int:
    if "--selftest" in argv:
        return selftest()
    if len(argv) < 4:
        print(__doc__)
        return 1
    slug, name_ru, dat_ru, port = argv[0], argv[1], argv[2], int(argv[3])
    dest = Path(argv[4]).expanduser() if len(argv) > 4 else Path.home() / "Documents" / ("extella-" + slug)
    generate(slug, name_ru, dat_ru, port, dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
