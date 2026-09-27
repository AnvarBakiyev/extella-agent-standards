# -*- coding: utf-8 -*-
"""Модуль допуска для серверного приложения Extella OS: «дать доступ» / «отозвать».

Откуда: приложение «Учёт клейм НацЭкс» (Гульжан, 25.09.2026), сервер `naceks_server.py`,
согласовано с Codex (bus/collaboration/2026-09-25-shared-data-architecture.md). Здесь —
самостоятельная выжимка без прикладной логики: только личность, роли, сессии, аудит.

ИДЕЯ. В странице приложения НЕТ общего ключа. ОС выдаёт каждому открывшему приложение
свой `app_token` (подстановка `{{app_token}}` в html). Страница присылает его серверу;
сервер САМ спрашивает у ОС `POST {OS_BASE}/api/app-agent/whoami {app_token}` и получает
проверенную личность `{user, email, agent_id, listing_id}` (поле `user` = EMAIL, замер
25.09.2026). Личность сверяется с таблицей ролей `state/roles.json` → короткая сессия.
Незнакомый человек попадает в `state/pending.json`, администратор выдаёт доступ из
приложения («Дать доступ»), отзыв («Отозвать») гасит сессии мгновенно.

ИНВАРИАНТЫ (каждый проверяется в --selftest на нарочно испорченной копии):
  1. Мусорный/чужой app_token → 401, сессии нет.            (личность только от ОС)
  2. Ключ другого приложения (listing_id ≠ наш) → 403.       (не «любой пользователь ОС»)
  3. Незнакомый → 403 no_role и запись в pending.json.       (админ увидит, кому выдать)
  4. Свой → 200 + сессия с ролью; роль перечитывается на КАЖДОМ запросе.
  5. Отзыв (revoke) или удаление из roles.json напрямую → действующая сессия → 401.
  6. Админ-методы для роли user → 403; нельзя отозвать собственный доступ.
  7. Повреждённый roles.json = никому нет доступа, а не «всем» и не падение.
  8. В аудите нет ни app_token, ни ключа сессии — только кто/что/когда.

ВСТРАИВАНИЕ. См. README.md рядом: RoleStore + whoami() + AccessGate — три вещи, которые
подключаются к любому http-серверу; страница — access_page.js.
"""
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request

SESSION_TTL = 8 * 3600          # рабочий день; отзыв покупки на платформе виден при новой сессии
SESSION_HEADER = "X-App-Session"
ADMIN_ONLY = {"list_users", "grant_user", "revoke_user"}


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def write_json_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class RoleStore:
    """roles.json (кто допущен), pending.json (кто просит), audit.log (кто что сделал),
    сессии в памяти. Ключ пользователя — то, что ОС вернула в `user` (email)."""

    def __init__(self, state_dir):
        self.state = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.roles_path = os.path.join(state_dir, "roles.json")
        self.pending_path = os.path.join(state_dir, "pending.json")
        self.audit_path = os.path.join(state_dir, "audit.log")
        self.sessions = {}
        self.sessions_lock = threading.Lock()

    # ── журнал действий: только добавление, без секретов ──────────────────
    def audit(self, user, action, **fields):
        line = json.dumps(dict({"time": now(), "user": user, "action": action}, **fields),
                          ensure_ascii=False)
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ── роли ──────────────────────────────────────────────────────────────
    def roles(self):
        r = read_json(self.roles_path, None)
        return r if isinstance(r, dict) else {}      # инвариант 7

    def role_of(self, user):
        r = self.roles().get(str(user))
        return r if isinstance(r, dict) else None

    def pending(self):
        p = read_json(self.pending_path, None)
        return p if isinstance(p, dict) else {}

    def add_pending(self, user, email):
        p = self.pending()
        p[str(user)] = {"email": email,
                        "first_seen": p.get(str(user), {}).get("first_seen") or now(),
                        "last_seen": now()}
        write_json_atomic(self.pending_path, p)

    def grant(self, user, name="", role="user", email=""):
        if role not in ("user", "admin"):
            return False
        r = self.roles()
        r[str(user)] = {"name": name or email or str(user), "role": role, "email": email,
                        "granted": now()}
        write_json_atomic(self.roles_path, r)
        p = self.pending()
        if str(user) in p:
            del p[str(user)]
            write_json_atomic(self.pending_path, p)
        return True

    def revoke(self, user):
        r = self.roles()
        if str(user) not in r:
            return False
        del r[str(user)]
        write_json_atomic(self.roles_path, r)
        with self.sessions_lock:                      # инвариант 5: гасим сразу
            for k in [k for k, v in self.sessions.items() if v["user"] == str(user)]:
                del self.sessions[k]
        return True

    # ── сессии ────────────────────────────────────────────────────────────
    def new_session(self, ident):
        s = secrets.token_urlsafe(32)
        with self.sessions_lock:
            for k in [k for k, v in self.sessions.items() if v["exp"] < time.time()]:
                del self.sessions[k]
            self.sessions[s] = dict(ident, exp=time.time() + SESSION_TTL)
        return s

    def session(self, key):
        """Сессия жива, только если человек ВСЁ ЕЩЁ в ролях (инвариант 4/5)."""
        if not key:
            return None
        with self.sessions_lock:
            v = self.sessions.get(key)
        if not v or v["exp"] < time.time():
            return None
        r = self.role_of(v["user"])
        if not r:
            with self.sessions_lock:
                self.sessions.pop(key, None)
            return None
        return dict(v, role=r.get("role", "user"), name=r.get("name", ""))


def whoami(app_token, os_base="https://os.extella.ai", timeout=15):
    """Личность — только от ОС, по фиксированному адресу; любая беда = нет сессии.
    Возвращает (ident|None, http_code, причина)."""
    req = urllib.request.Request(os_base + "/api/app-agent/whoami",
                                 data=json.dumps({"app_token": app_token}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, (401 if e.code in (401, 403) else 502), "ОС не подтвердила ключ приложения (%s)" % e.code
    except Exception as e:
        return None, 502, "Extella OS недоступна: %s" % type(e).__name__
    if not isinstance(d, dict) or d.get("status") != "ok" or not d.get("user") or not d.get("listing_id"):
        return None, 502, "ОС ответила не той формой"
    return d, 200, ""


class AccessGate:
    """Две точки входа для http-обработчика: open_session() для POST /api/session и
    check() для каждого POST /api/call. Возвращают (код, объект-ответ)."""

    def __init__(self, store, listing_id, os_base="https://os.extella.ai", whoami_fn=None):
        self.st = store
        self.listing_id = str(listing_id)
        self.os_base = os_base
        self._whoami = whoami_fn or (lambda tok: whoami(tok, self.os_base))

    def open_session(self, app_token):
        tok = str(app_token or "")
        if not tok or len(tok) > 4096:
            return 401, {"status": "error", "reason": "нет ключа приложения"}
        ident, code, why = self._whoami(tok)
        if not ident:
            return code, {"status": "error", "reason": why}
        if str(ident.get("listing_id")) != self.listing_id:
            return 403, {"status": "error", "reason": "ключ выдан другому приложению"}       # инвариант 2
        user, email = str(ident["user"]), str(ident.get("email") or "")
        role = self.st.role_of(user)
        if not role:
            self.st.add_pending(user, email)                                                    # инвариант 3
            return 403, {"status": "error", "reason": "Доступ ещё не выдан. Запрос передан администратору.",
                         "no_role": True, "email": email}
        s = self.st.new_session({"user": user, "email": email, "role": role.get("role", "user"),
                                 "name": role.get("name", "")})
        return 200, {"status": "success", "session": s, "user": user, "email": email,
                     "role": role.get("role", "user"), "name": role.get("name", "")}

    def check(self, session_key, method):
        """→ (None, sess) если можно; иначе (код, ответ)."""
        sess = self.st.session(session_key or "")
        if not sess:
            return (401, {"status": "error", "reason": "сессия не действует — откройте приложение заново"}), None
        if method in ADMIN_ONLY and sess["role"] != "admin":
            return (403, {"status": "error", "reason": "только администратор"}), None          # инвариант 6
        return None, sess

    def admin(self, method, args, sess):
        """list_users / grant_user / revoke_user — тело ответа (уже после check())."""
        args = args or {}
        if method == "list_users":
            return {"status": "success", "result": {"users": self.st.roles(), "pending": self.st.pending()}}
        if method == "grant_user":
            u = str(args.get("user") or "")
            if not u:
                return {"status": "error", "reason": "нужен user"}
            pend = self.st.pending().get(u, {})
            role = str(args.get("role") or "user")
            okk = self.st.grant(u, name=str(args.get("name") or ""), role=role,
                                email=str(args.get("email") or pend.get("email") or ""))
            if okk:
                self.st.audit(sess["user"], "grant", target=u, role=role)
            return {"status": "success", "result": {"granted": True, "user": u}} if okk else \
                   {"status": "error", "reason": "роль: user|admin"}
        if method == "revoke_user":
            u = str(args.get("user") or "")
            if u == sess["user"]:
                return {"status": "error", "reason": "нельзя отозвать собственный доступ"}
            rv = self.st.revoke(u)
            if rv:
                self.st.audit(sess["user"], "revoke", target=u)
            return {"status": "success", "result": {"revoked": rv, "user": u}}
        return {"status": "error", "reason": "не админ-метод"}


# ══════════════════════════════════════════════════════════════════════════
# Самопроверка: гейт, который умеет падать. Заглушка ОС вместо сети.
# ══════════════════════════════════════════════════════════════════════════
def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="app_access_")
    st = RoleStore(tmp)
    TOK = {"good-A": {"status": "ok", "user": "a@x", "email": "a@x", "listing_id": "L1"},
           "good-B": {"status": "ok", "user": "b@x", "email": "b@x", "listing_id": "L1"},
           "other-app": {"status": "ok", "user": "c@x", "email": "c@x", "listing_id": "L2"},
           "bad-shape": {"status": "ok"}}

    def fake_whoami(tok):
        if tok not in TOK:
            return None, 401, "ОС не подтвердила ключ приложения (401)"
        d = TOK[tok]
        if not d.get("user"):
            return None, 502, "ОС ответила не той формой"
        return d, 200, ""

    gate = AccessGate(st, "L1", whoami_fn=fake_whoami)
    st.grant("a@x", name="Админ", role="admin", email="a@x")
    fails = []

    def check(name, cond):
        print(("  [ok] " if cond else "  [ПРОВАЛ] ") + name)
        if not cond:
            fails.append(name)

    c, d = gate.open_session("garbage");         check("1 мусорный app_token → 401", c == 401)
    c, d = gate.open_session("bad-shape");       check("1 ответ ОС не той формы → 502", c == 502)
    c, d = gate.open_session("other-app");       check("2 ключ другого приложения → 403", c == 403)
    c, d = gate.open_session("good-B");          check("3 незнакомый → 403 no_role + pending", c == 403 and d.get("no_role") and "b@x" in st.pending())
    c, dA = gate.open_session("good-A");         check("4 свой → 200 сессия admin", c == 200 and dA.get("role") == "admin")
    sA = dA["session"]
    e, sess = gate.check(sA, "list_users");      check("4 админ видит роли и ожидающих", e is None and "b@x" in gate.admin("list_users", {}, sess)["result"]["pending"])
    r = gate.admin("grant_user", {"user": "b@x", "name": "Б"}, sess); check("grant → user в ролях, ушёл из pending", r["status"] == "success" and st.role_of("b@x") and "b@x" not in st.pending())
    c, dB = gate.open_session("good-B");         check("выданный → 200 роль user", c == 200 and dB.get("role") == "user")
    sB = dB["session"]
    e, _ = gate.check(sB, "grant_user");         check("6 админ-метод для user → 403", e and e[0] == 403)
    r = gate.admin("revoke_user", {"user": "a@x"}, sess); check("6 нельзя отозвать себя", r["status"] == "error")
    r = gate.admin("revoke_user", {"user": "b@x"}, sess); e, _ = gate.check(sB, "ping"); check("5 отзыв гасит сессию → 401", r["result"]["revoked"] and e and e[0] == 401)
    gate.admin("grant_user", {"user": "b@x"}, sess); c, dB = gate.open_session("good-B"); sB = dB["session"]
    rr = st.roles(); rr.pop("b@x"); write_json_atomic(st.roles_path, rr)
    e, _ = gate.check(sB, "ping");               check("5 удаление из roles.json напрямую → 401", e and e[0] == 401)
    with open(st.roles_path, "w") as f: f.write("{broken json")
    c, d = gate.open_session("good-A");          check("7 повреждённый roles.json → никому (403), не падение", c == 403)
    write_json_atomic(st.roles_path, {"a@x": {"name": "Админ", "role": "admin", "email": "a@x"}})
    log = open(st.audit_path, encoding="utf-8").read()
    check("8 в аудите нет ключей сессий и app_token", sA not in log and sB not in log and "good-A" not in log and '"grant"' in log)
    # саботаж: модуль, который ПЕРЕСТАЛ перечитывать роли, должен провалить п.5
    class Sabotaged(RoleStore):
        def session(self, key):
            with self.sessions_lock:
                v = self.sessions.get(key)
            return dict(v, role="user", name="") if v else None
    st2 = Sabotaged(tempfile.mkdtemp(prefix="app_access_sab_")); g2 = AccessGate(st2, "L1", whoami_fn=fake_whoami)
    st2.grant("b@x", role="user", email="b@x"); c, d2 = g2.open_session("good-B"); rr = st2.roles(); rr.pop("b@x"); write_json_atomic(st2.roles_path, rr)
    e, _ = g2.check(d2["session"], "ping")
    check("саботаж воспроизведён: копия без перечитки ролей НЕ гасит сессию после удаления (настоящая — гасит)", e is None)
    if fails:
        print("МОДУЛЬ ДОПУСКА: ПРОВАЛ —", "; ".join(fails))
        return 1
    print("МОДУЛЬ ДОПУСКА: OK — 15 проверок, саботаж воспроизведён")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 0)
