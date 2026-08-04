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
  python3 tools/new_product.py <slug> "<Название>" "<кому>" <порт> --serverless
                                                 # тонкая панель: без порта и процесса
  python3 tools/new_product.py --selftest        # сгенерировать пробные и прогнать гейты

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

MANIFEST_YAML_THIN = """# Манифест зависимостей «__NAME_RU__» (тонкая панель).
#
# Порта и своего процесса нет — проверять нечего. Осталось то, что действительно
# нужно: приложение Extella с живым мостом (он один на машину) и вход в аккаунт.
checks:
  - kind: file
    path: "~/.extella/api_token.txt"
    level: warn            # без него панель честно попросит войти в Extella
    fix_ru: "открой приложение Extella и войди в аккаунт — файл появится сам"
  - kind: python
    min_version: "3.10"
    fix_ru: "поставь Python 3.10+ (нужен только установщику, не панели)"
"""


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



# Диспетчер тонкого продукта. КАНОН 04.08.2026: у продукта одна таблица маршрутов,
# и мост смотрит В НЕЁ. Три переведённых продукта показали разницу: там, где таблицы
# не было (Предиктив, Таргетолог), карту маршрутов пришлось держать в оболочке и
# охранять отдельным гейтом; у Юриста таблица была — сверять оказалось нечего.
# Поэтому новый продукт рождается с таблицей и диспетчером сразу.
THIN_ROUTES_PY = '''"""Единственная таблица маршрутов продукта «__NAME_RU__».

Панель зовёт маршруты через мост, диспетчер __SLUG___call читает ЭТУ таблицу.
Добавил маршрут сюда — он сразу доступен панели; убрал — сразу пропал. Второй
карты нет и заводить её нельзя: разъехавшаяся копия — самый дорогой класс ошибок.

Каждый обработчик принимает тело запроса (dict) и возвращает dict.
"""

from __future__ import annotations

from typing import Any, Callable


def h_status(_body: dict[str, Any]) -> dict[str, Any]:
    """Честное состояние продукта: что настроено, а что нет."""
    return {"status": "success", "product": "__SLUG__", "ready": True}


def h_ping(_body: dict[str, Any]) -> dict[str, Any]:
    return {"status": "success", "answer": "готов"}


ROUTES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "/x/status": h_status,
    "/x/ping": h_ping,
}
'''

THIN_CALL_EXPERT = '''# expert: __SLUG___call
# description: __NAME_RU__: вызов маршрута продукта на ЭТОМ устройстве (мост тонкой панели). Параметры: route, body_json.

def __SLUG___call(route="", body_json="{}") -> str:
    """Один эксперт вместо всех маршрутов — и без второй карты.

    Диспетчер читает таблицу ROUTES самого продукта, поэтому панель и продукт
    не могут разойтись. Список допуска = сама таблица: наружу видно ровно то,
    что продукт объявил маршрутом.
    """
    import json
    import os
    import sys
    import traceback

    def fail(msg, **extra):
        out = {"status": "error", "message": str(msg)[:400]}
        out.update(extra)
        return json.dumps(out, ensure_ascii=False)

    def blank(v):
        return (not v) or str(v).startswith("{{")

    r = str(route or "").strip()
    if blank(r):
        return fail("нужен маршрут")
    if not r.startswith("/"):
        r = "/" + r
    try:
        body = {} if blank(body_json) else json.loads(body_json)
        if not isinstance(body, dict):
            return fail("body_json должен быть объектом")
    except Exception as e:
        return fail("тело запроса не разобралось как JSON: %s" % str(e)[:120])

    # Рабочий корень — копия с ДАННЫМИ, а не клон разработчика: поиск по списку
    # однажды выбрал чужой, и продукт отвечал из пустой базы (04.08).
    roots = ["__PRODUCT_ROOT__", os.environ.get("EXTELLA___SLUG_UPPER___ROOT", "")]
    roots = [x for x in roots if x and not x.startswith("__")]
    roots += [os.path.expanduser(p) for p in (
        "~/extella-plugins/__SLUG__",
        "~/Documents/Extella/__SLUG__",
    )]
    app_dir = ""
    for root in roots:
        for candidate in (os.path.join(root, "app"), root):
            if os.path.isfile(os.path.join(candidate, "routes.py")):
                app_dir = candidate
                break
        if app_dir:
            break
    if not app_dir:
        return fail("не нашёл файлы продукта на этом устройстве — поставь его заново")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    try:
        import routes as product
    except Exception as e:
        return fail("модуль продукта не загрузился: %s" % str(e)[:200],
                    where=traceback.format_exc(limit=2)[-300:])

    table = getattr(product, "ROUTES", None)
    if not isinstance(table, dict):
        return fail("в продукте нет таблицы маршрутов ROUTES")
    fn = table.get(r)
    if not callable(fn):
        return fail("маршрут «%s» недоступен" % r, allowed_count=len(table))

    try:
        res = fn(body)
    except Exception as e:
        return fail("маршрут «%s» упал: %s" % (r, str(e)[:200]),
                    where=traceback.format_exc(limit=2)[-300:])

    try:
        out = json.dumps({"status": "success", "result": res}, ensure_ascii=False, default=str)
    except Exception as e:
        return fail("ответ маршрута не сериализуется: %s" % str(e)[:160])

    # Ответ больше ~200 КБ платформа не доносит (замер 04.08) — сжимаем.
    if len(out) > 200000:
        import base64
        import gzip
        packed = base64.b64encode(gzip.compress(out.encode("utf-8"))).decode("ascii")
        return json.dumps({"status": "success", "gz": packed,
                           "raw_len": len(out), "packed_len": len(packed)}, ensure_ascii=False)
    return out
'''


# ── ТОНКИЙ РЕЖИМ (--serverless): панель без собственного сервера ───────────────
# Восемь продуктов = восемь локальных серверов = восемь портов, автозапусков и
# зависимостей от питона машины; практически весь бэклог 03–04.08 вырос отсюда.
# Тонкая панель не имеет ни порта, ни процесса: страница живёт в приложении
# (ui.type=html), работу делают эксперты НА устройстве через мост витрины
# (etb_run_expert). Токен странице не выдаётся вовсе.
#
# ЧЕСТНО О ДАННЫХ (поправка 04.08, поймана адверсарной проверкой). «Данные не
# покидают машину» — верно только для данных В ПОКОЕ: база, файлы и секреты
# остаются на устройстве, эксперт исполняется на нём. Но САМ ВЫЗОВ идёт через
# платформу: параметры и результат проходят api.extella.ai. У классической панели
# на localhost этого транзита нет. Для продукта, где через панель ходят чужие
# персональные данные или большие выгрузки, это осознанный размен, а не мелочь:
# решать до перевода, а не после.

THIN_HTML = '''<div class="wrap">
  <h1>__NAME_RU__</h1>
  <div class="sub" id="sub">Панель без локального сервера: работу делают эксперты на этом устройстве.</div>

  <div class="card">
    <div><span class="pill">Устройство: <span class="mono" id="devId">…</span></span>
         <span class="pill">Агент: <b id="agentName">…</b></span></div>
    <div style="margin-top:12px">
      <button class="btn sec" onclick="bindAgent()" id="bindBtn">Выбрать агента</button>
      <button class="btn" onclick="ping()" id="pingBtn">Проверить связь</button>
    </div>
    <div class="err" id="out"></div>
  </div>
</div>
<style>
:root{--ink:#1F2937;--paper:#FAF9F6;--gold:#C9A227;--petrol:#0F4C5C;--divider:#E5E1D8;--muted:#6B7280}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Nunito',ui-sans-serif,sans-serif;background:var(--paper);color:var(--ink);font-size:15px;line-height:1.5}
button,input,select,textarea{font-family:inherit;font-size:inherit}
.wrap{max-width:720px;margin:0 auto;padding:24px}
h1{font-size:20px;font-weight:700;margin-bottom:4px}
.sub{font-size:13px;color:var(--muted);margin-bottom:24px}
.card{background:#fff;border:1px solid var(--divider);border-radius:12px;padding:16px;margin-bottom:16px}
.btn{display:inline-block;border:1px solid var(--petrol);background:var(--petrol);color:#fff;border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:600}
.btn.sec{background:#fff;color:var(--petrol)}
.pill{display:inline-block;border:1px solid var(--divider);border-radius:999px;padding:4px 12px;font-size:13px;margin-right:8px}
.err{color:#8A2D2D;font-size:13px;margin-top:12px;min-height:16px}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px}
</style>
<script>
// Двуязычно с рождения — паспорт заявляет ru+en, заявка обязана быть правдой.
var T={ru:{none:'не выбран',check:'проверяю…',ans:'ответ агента: ',fail:'не получилось',
 nodev:'устройство не найдено — открой приложение Extella и войди в аккаунт',
 pick:'Вставь id агента (список — в приложении, вкладка «Агенты»):',bound:'агент привязан: '},
 en:{none:'not selected',check:'checking…',ans:'agent answered: ',fail:'did not work',
 nodev:'device not found — open the Extella app and sign in',
 pick:'Paste the agent id (see the Agents tab in the app):',bound:'agent bound: '}};
var L=(navigator.language||'ru').indexOf('ru')===0?'ru':'en';
function tr(k){return T[L][k];}
// Язык берём У ПРИЛОЖЕНИЯ: браузерная локаль показывала англоязычный интерфейс
// русскоязычному человеку (поймано на живом экране 04.08).
window.addEventListener('message',function(e){
  var d=e.data||{};
  if(d.type!=='etb_init')return;
  if(d.lang)L=(String(d.lang).indexOf('ru')===0)?'ru':'en';
  DEVICE=String(d.device||'');
  refresh();
});
function $(id){return document.getElementById(id);}

// Мост экспертов витрины: страница НИКОГДА не держит токен и не ходит в сеть сама.
var _seq=0,_waiting={};
window.addEventListener('message',function(e){
  var d=e.data||{};
  if(d.type==='etb_expert_result'&&_waiting[d.reqId]){var f=_waiting[d.reqId];delete _waiting[d.reqId];f(d);}
});
function runExpert(name,params){
  return new Promise(function(res){
    var id='r'+(++_seq);
    _waiting[id]=function(d){res(d);};
    var msg={type:'etb_run_expert',reqId:id,name:name,params:params||{}};
    // Устройство шлём ОБОИМИ полями: установленная сборка витрины читает строковое
    // target, исходники — массив targets. Проверять надо против СБОРКИ на машине,
    // а не против репозитория: первая версия слала только targets, и работа молча
    // уходила на устройство по умолчанию (поймано адверсарной проверкой 04.08).
    if(DEVICE){msg.target=DEVICE;msg.targets=[DEVICE];}
    parent.postMessage(msg,'*');
    setTimeout(function(){if(_waiting[id]){delete _waiting[id];
      res({ok:false,error:'нет ответа от моста за 120с — это не провал, задача могла уйти дальше'});}},120000);
  });
}
// Своё устройство приходит В ПРИВЕТСТВИИ от приложения (etb_init.device).
// Раньше панель спрашивала его у моста по http://127.0.0.1:8765 — то есть ради
// одной строки тянула за собой локальный сервер, ровно то, от чего тонкий режим
// уходит. Ни одного обращения к localhost в этой странице больше нет.
var DEVICE='';
function say(t){$('out').textContent=t||'';}
function unwrap(d){
  // Причина отказа обязана быть на экране: «не получилось» без причины — это день
  // слепой переписки (урок недели). Показываем, что реально ответил мост.
  if(!d||!d.ok)return {status:'error',message:(d&&d.error)||(tr('fail')+': '+JSON.stringify(d||{}).slice(0,160))};
  // Сборка витрины кладёт результат в res, исходники — в result. Читаем оба:
  // иначе каждый успешный вызов выглядел бы пустым ответом.
  var r=(d.res!==undefined&&d.res!==null)?d.res:d.result;
  if(r===undefined||r===null)return {status:'error',
    message:tr('fail')+': мост ответил без результата — '+JSON.stringify(d).slice(0,160)};
  if(typeof r==='string'){try{r=JSON.parse(r);}catch(_){return {status:'error',message:String(r).slice(0,200)};}}
  return r||{status:'error',message:tr('fail')};
}
async function refresh(){
  $('devId').textContent=DEVICE?DEVICE.slice(0,8):'—';
  // Без устройства работать нельзя: задача уйдёт в общий пул аккаунта и исполнится
  // на чужой машине. Молчать и делать вид, что всё хорошо, — худший вариант.
  $('pingBtn').disabled=!DEVICE;$('bindBtn').disabled=!DEVICE;
  if(!DEVICE){say(tr('nodev'));return;}
  var st=unwrap(await runExpert('__SLUG___state',{}));
  $('agentName').textContent=(st&&st.agent)?st.agent.slice(0,18):tr('none');
}
async function bindAgent(){
  var id=prompt(tr('pick'));if(!id)return;
  var r=unwrap(await runExpert('__SLUG___bind',{agent_id:id.trim()}));
  say(r.status==='success'?tr('bound')+r.agent:(r.message||tr('fail')));
  refresh();
}
async function ping(){
  say(tr('check'));
  var r=unwrap(await runExpert('__SLUG___ping',{}));
  // «running» и «failed» — не успех: недожатое не имеет права выглядеть сделанным.
  say(r.status==='success'?tr('ans')+(r.answer||''):(r.message||r.error||tr('fail')));
}
refresh();
</script>
'''

THIN_STATE_EXPERT = '''# expert: __SLUG___state
# description: __NAME_RU__: состояние продукта на устройстве — привязанный агент. Параметры: нет.

def __SLUG___state() -> str:
    import json, os
    p = os.path.expanduser("~/extella___SLUG__/agent_binding.json")
    agent = ""
    try:
        with open(p, encoding="utf-8") as fh:
            agent = (json.load(fh) or {}).get("agent_id", "")
    except Exception:
        agent = ""
    return json.dumps({"status": "success", "agent": agent}, ensure_ascii=False)
'''

THIN_BIND_EXPERT = '''# expert: __SLUG___bind
# description: __NAME_RU__: привязать агента к продукту на ЭТОМ устройстве. Параметры: agent_id.

def __SLUG___bind(agent_id="") -> str:
    import json, os
    a = str(agent_id or "").strip()
    if not a or a.startswith("{{"):
        return json.dumps({"status": "error", "message": "нужен agent_id"}, ensure_ascii=False)
    # Платный Claude клиентам запрещён каноном — отказ честный, а не тихая подмена.
    if a == "agent_extella_default":
        return json.dumps({"status": "error",
                           "message": "этот агент платный и клиентам не выдаётся — выберите своего"},
                          ensure_ascii=False)
    d = os.path.expanduser("~/extella___SLUG__")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "agent_binding.json"), "w", encoding="utf-8") as fh:
        json.dump({"agent_id": a}, fh, ensure_ascii=False)
    return json.dumps({"status": "success", "agent": a}, ensure_ascii=False)
'''

THIN_CARD = '''{
  "id": "__SLUG__",
  "name": "__NAME_RU__",
  "tagline": "Панель без локального сервера — работа на устройстве через экспертов",
  "description": "Тонкая панель Extella: ни порта, ни отдельного процесса. Интерфейс живёт в приложении, работу делают эксперты на этом устройстве; база и файлы остаются здесь, а сами вызовы идут через платформу.",
  "category": "work",
  "type": "custom",
  "version": "0.1.0",
  "ui": {"type": "html", "tokenless": true},
  "experts": ["__SLUG___state", "__SLUG___bind", "__SLUG___ping"]
}'''

THIN_INSTALL = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установка «__NAME_RU__» — тонкой панели (ни порта, ни процесса, ни автозапуска).

Ставит: экспертов на аккаунт + карточку с самой страницей внутрь реестра плагинов.
Обновление продукта = обновление карточки; чинить нечего — сервера нет.
"""
import io
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
REGISTRY = Path.home() / "extella-plugins" / "_registry"


def main() -> int:
    sys.path.insert(0, str(HERE / "app"))
    import agent_onboarding                                 # noqa: E402
    import platform_client                                  # noqa: E402

    print("== Эксперты ==")
    try:
        reg_agent = platform_client.bound_agent()
    except platform_client.PlatformError:
        reg_agent = agent_onboarding.PLATFORM_TRIAL_ID
    for f in sorted((HERE / "experts").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        desc = ""
        for line in src.splitlines()[:6]:
            if line.startswith("# description:"):
                desc = line.split(":", 1)[1].strip()
        try:
            platform_client.xapi("/api/expert/save",
                                 {"name": f.stem, "code": src, "description": desc or f.stem,
                                  "global": True}, timeout=90, agent_id=reg_agent)
            print("  ok", f.stem)
        except platform_client.PlatformError as e:
            print("  FAIL", f.stem, "—", str(e)[:120])
            return 1

    print("== Карточка ==")
    card = json.loads((HERE / "card.json").read_text(encoding="utf-8"))
    # Страница едет ВНУТРИ карточки: приложение показывает её из памяти, файлов на
    # диске нет — значит нечему устареть, потеряться при копировании и упасть.
    card["ui"]["html"] = (HERE / "panel.html").read_text(encoding="utf-8")
    REGISTRY.mkdir(parents=True, exist_ok=True)
    out = REGISTRY / (card["id"] + ".json")
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ok", out)
    print("Готово. Открой Extella → Plugins → «__NAME_RU__». Порт не нужен, служба не нужна.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def generate(slug: str, name_ru: str, dat_ru: str, port: int, dest: Path,
             register: bool = True, thin: bool = False) -> None:
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

    if thin:
        # Тонкая панель: ни server.py, ни порта, ни автозапуска.
        (dest / "panel.html").write_text(fill(THIN_HTML), encoding="utf-8")
        (dest / "card.json").write_text(fill(THIN_CARD), encoding="utf-8")
        (dest / "install.py").write_text(fill(THIN_INSTALL), encoding="utf-8")
        (dest / "experts" / (slug + "_state.py")).write_text(fill(THIN_STATE_EXPERT), encoding="utf-8")
        (dest / "experts" / (slug + "_bind.py")).write_text(fill(THIN_BIND_EXPERT), encoding="utf-8")
        (dest / "experts" / (slug + "_ping.py")).write_text(fill(PING_EXPERT), encoding="utf-8")
        # Таблица маршрутов и диспетчер поверх неё — с рождения: продукт растёт
        # маршрутами, а панель получает их сама (канон 04.08).
        (dest / "app" / "routes.py").write_text(fill(THIN_ROUTES_PY), encoding="utf-8")
        (dest / "experts" / (slug + "_call.py")).write_text(
            fill(THIN_CALL_EXPERT).replace("__SLUG_UPPER__", slug.upper()), encoding="utf-8")
        (dest / "agent_passport.yaml").write_text(
            fill(PASSPORT_YAML).replace('hosting_profile: "client_server"',
                                        'hosting_profile: "bridge_only"')
                               .replace("# локальная панель 127.0.0.1:__PORT__ + эксперты на устройстве".replace("__PORT__", str(port)),
                                        "# страница в приложении + эксперты на устройстве; своего сервера нет"),
            encoding="utf-8")
        (dest / "MANIFEST.yaml").write_text(fill(MANIFEST_YAML_THIN), encoding="utf-8")
        (dest / "README.md").write_text(fill(README_MD).replace(
            "## Что уже правильно с рождения",
            "**Тонкий режим:** у продукта НЕТ своего сервера, порта и автозапуска — "
            "страница живёт в приложении, работу делают эксперты на устройстве через мост "
            "витрины. Токен в страницу не попадает вовсе.\n\n## Что уже правильно с рождения"),
            encoding="utf-8")
        shutil.copy(CANON_APP / "platform_client.py", dest / "app" / "platform_client.py")
        shutil.copy(CANON_APP / "agent_onboarding.py", dest / "app" / "agent_onboarding.py")
        print("Тонкий каркас «%s» создан: %s" % (name_ru, dest))
        print("Установка: python3 %s/install.py — без порта и без службы." % dest)
        return

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

    # ── Тонкий режим: панель без сервера ──────────────────────────────────────
    tmp2 = Path(tempfile.mkdtemp()) / "probe_thin"
    generate("probethin", "Тонкая проба", "тонкой пробе", 8918, tmp2, register=False, thin=True)
    for py in list(tmp2.rglob("*.py")):
        try:
            ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print("  ✗ тонкий: синтаксис", py.name, e)
            bad += 1

    # Ни порта, ни процесса, ни автозапуска — иначе это не тонкая панель.
    card = json.loads((tmp2 / "card.json").read_text(encoding="utf-8"))
    if card.get("ui", {}).get("type") != "html" or card.get("ui", {}).get("port") or card.get("service"):
        print("  ✗ тонкий: карточка не бессерверная:", card.get("ui"))
        bad += 1
    if not card.get("ui", {}).get("tokenless"):
        print("  ✗ тонкий: карточка не помечена tokenless — странице выдадут токен аккаунта")
        bad += 1

    page = (tmp2 / "panel.html").read_text(encoding="utf-8")
    leaks = [m for m in ("api.extella.ai", "X-Auth-Token", "auth_token") if m in page]
    if leaks:
        print("  ✗ тонкий: страница ходит в платформу сама:", leaks)
        bad += 1
    if "msg.target=" not in page.replace(" ", ""):
        print("  ✗ тонкий: мост зовётся без строкового target — установленная сборка "
              "витрины читает именно его, работа уедет на устройство по умолчанию")
        bad += 1
    # Ищем ОБРАЩЕНИЕ, а не упоминание: первая версия гейта краснела на комментарии,
    # который объясняет, что localhost убран. Ложный запрет обходят целиком.
    live_calls = [ln for ln in page.splitlines()
                  if ("127.0.0.1" in ln or "localhost" in ln)
                  and not ln.lstrip().startswith(("//", "*", "/*", "#"))]
    if live_calls:
        print("  ✗ тонкий: страница обращается к localhost — это и есть то, от чего "
              "тонкий режим уходит (устройство приходит в etb_init):")
        for ln in live_calls[:3]:
            print("      " + ln.strip()[:100])
        bad += 1
    if "d.res" not in page:
        print("  ✗ тонкий: панель не читает поле res — в установленной сборке витрины "
              "каждый успешный вызов выглядел бы пустым")
        bad += 1
    # Контракт сверяем с ЖИВОЙ сборкой витрины, а не с исходниками: на машине
    # человека работает именно она (урок 04.08).
    art = Path.home() / "Library/Application Support/extella-desktop/toolbar.js"
    if art.exists():
        blob = art.read_text(encoding="utf-8", errors="replace")
        if "e.data.target" not in blob:
            print("  ~ в установленной витрине нет чтения e.data.target — контракт моста изменился")
        if "etb_expert_result" not in blob:
            print("  ✗ установленная витрина не знает моста экспертов — тонкий режим не заработает")
            bad += 1

    # Эксперты исполняются как их зовёт листенер — на ЧУЖОМ HOME.
    import tempfile as _tf
    fake_home = _tf.mkdtemp()
    env_home = os.environ.get("HOME")
    os.environ["HOME"] = fake_home
    try:
        for name, kwargs, expect in (("probethin_state", {}, "success"),
                                     ("probethin_bind", {"agent_id": "agent_extella_default"}, "error"),
                                     ("probethin_bind", {"agent_id": "agent_qwen_x"}, "success"),
                                     ("probethin_ping", {}, "success")):
            src = (tmp2 / "experts" / (name + ".py")).read_text(encoding="utf-8")
            ns = {}
            exec(compile(src, name, "exec"), ns)
            got = json.loads(ns[name](**kwargs)).get("status")
            if got != expect:
                print("  ✗ тонкий: %s дал %s вместо %s" % (name, got, expect))
                bad += 1
    finally:
        if env_home:
            os.environ["HOME"] = env_home
    if not bad:
        print("  ✓ тонкий режим: без порта и процесса, токена нет, работа закреплена, эксперты живы")

    canon_gate2 = Path.home() / "Documents/Extella/extella-toolbar-src/tools/check_panel_canon.py"
    if canon_gate2.exists():
        r = subprocess.run([sys.executable, str(canon_gate2), str(tmp2 / "panel.html")],
                           capture_output=True, text=True)
        if "✕" in r.stdout:
            print("  ✗ тонкая панель вне канона дизайна:\n" + r.stdout[-500:])
            bad += 1
        else:
            print("  ✓ тонкая панель проходит канон дизайна")
    shutil.rmtree(tmp2.parent, ignore_errors=True)

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
    thin = "--serverless" in argv
    argv = [a for a in argv if not a.startswith("--")]
    slug, name_ru, dat_ru, port = argv[0], argv[1], argv[2], int(argv[3])
    dest = Path(argv[4]).expanduser() if len(argv) > 4 else Path.home() / "Documents" / ("extella-" + slug)
    generate(slug, name_ru, dat_ru, port, dest, thin=thin)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
