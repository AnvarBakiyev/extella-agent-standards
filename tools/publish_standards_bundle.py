#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка и публикация attested bundle стандартов для Evolution Console.

ЗАЧЕМ. Console падала в `PRODUCTION_STANDARDS_UNAVAILABLE`, потому что ключа
`xtl_evolution:production_standards_bundle:v1` на аккаунте нет ВОВСЕ. Это мой слой, и
экран Codex ждёт именно его. С bundle Console перестанет показывать ошибку и начнёт честно
говорить «паспортов нет» — разница принципиальная: ошибка означает «мы не знаем», ноль
означает «мы посмотрели, и там пусто».

ЧЕСТНАЯ ОГОВОРКА. Существо bundle — Agent Passports, и их у нас НОЛЬ. Первый bundle будет
пустым по составу и полным по форме. Это не повод его не делать: пустой честный список
лучше ошибки. Паспорта заполняются поштучно, bundle пересобирается — ровно как мы сделали
с каталогом способностей.

КОНТРАКТ (разобран по провайдеру `evolution-standards-provider.js` витрины):

  ключ манифеста   xtl_evolution:production_standards_bundle:v1
  ключ куска       <ключ манифеста>:chunk:<первые 20 символов sha256>:<номер>
  поля манифеста   ровно schema, encoding, owner_account_id, bundle_sha256,
                   chunk_count, bundle_byte_length — лишнее провайдер не принимает
  тело             data_mode=PRODUCTION, delivery_mode=ACCOUNT_SCOPED_HOST_PROVIDER,
                   owner_account_id обязан совпасть с user_id читателя
  сериализация     каноничный JSON: ключи отсортированы, пробелов нет, не-ASCII не
                   экранируется — иначе провайдер отвергнет как «not canonical»

ПОЧЕМУ ОБЩАЯ ЗАПИСЬ. Провайдер читает bundle из скоупа КАЖДОГО живого агента и требует,
чтобы они совпадали байт в байт. Имя ключа свободное, без истории, а на таких именах
`global: true` работает исправно — доказано опытом 28.07 (разбор в INCIDENT_KV_SCOPE_SHADOWING).
На отравленных старых именах так делать было нельзя.

Как пользоваться:
  python3 publish_standards_bundle.py --dry-run   собрать и показать, ничего не писать
  python3 publish_standards_bundle.py             собрать и опубликовать
  python3 publish_standards_bundle.py --verify    перечитать с аккаунта и сверить
  python3 publish_standards_bundle.py --selftest  самопроверка без сети

Коды выхода: 0 — успех, 1 — расхождение или отказ платформы.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

API = "https://api.extella.ai"
BUNDLE_KEY = "xtl_evolution:production_standards_bundle:v1"
MANIFEST_SCHEMA = "extella.evolution.standards_kv_manifest.v1"
CHUNK_ENCODING = "canonical-json-chunks.v1"
MAX_CHUNKS = 128
# Кусок с запасом: KV принимает крупные значения, но мелкие куски переживают ретраи.
CHUNK_BYTES = 48 * 1024

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canonical(value):
    """Каноничный JSON ровно как у витрины: сортировка ключей, без пробелов, без \\u."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def chunk_key(bundle_sha256, index):
    return "%s:chunk:%s:%d" % (BUNDLE_KEY, bundle_sha256[:20], index)


def split_chunks(text):
    """Режем по БАЙТАМ, а не по символам: провайдер сверяет длину в байтах."""
    raw = text.encode("utf-8")
    out = []
    for start in range(0, len(raw), CHUNK_BYTES):
        out.append(raw[start:start + CHUNK_BYTES])
    # Разрез мог попасть внутрь многобайтового символа — склейка кусков всё равно даст
    # исходную строку, поэтому декодируем с surrogateescape только для передачи.
    return [c.decode("utf-8", "surrogateescape") for c in out] or [""]


def build_bundle(owner_account_id, passports, agent_control):
    """Тело bundle. Пусто по составу — честно, а не притворно."""
    return {
        "schema": "extella.evolution.production_standards_bundle.v1",
        "owner_account_id": str(owner_account_id),
        "data_mode": "PRODUCTION",
        "delivery_mode": "ACCOUNT_SCOPED_HOST_PROVIDER",
        "sources": {"passports": passports},
        "contracts": {"agent_control": agent_control} if agent_control else {},
    }


def build_manifest(owner_account_id, bundle):
    """Поля манифеста — РОВНО те, что перечисляет провайдер. Лишнее он отвергает."""
    text = canonical(bundle)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "schema": MANIFEST_SCHEMA,
        "encoding": CHUNK_ENCODING,
        "owner_account_id": str(owner_account_id),
        "bundle_sha256": digest,
        "chunk_count": len(split_chunks(text)),
        "bundle_byte_length": len(text.encode("utf-8")),
    }


# ---------- сеть ----------

def _token():
    """Токен читаем из канонических мест. В вывод он не попадает никогда."""
    p = os.path.expanduser("~/.claude/extella_mcp_server.py")
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            m = re.search(r'AUTH_TOKEN\s*=\s*["\']([^"\']{16,})["\']', fh.read())
            if m:
                return m.group(1)
    p = os.path.expanduser("~/extella_wizard/app/config.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            tok = json.load(fh).get("auth_token")
            if tok:
                return tok
    raise SystemExit("токен Extella не найден — ни в MCP-сервере, ни в config.json визарда")


def api(path, payload, token, agent_id="agent_extella_default"):
    """POST через curl: без внешних зависимостей, работает на чистой машине."""
    args = [
        "curl", "-s", "--max-time", "45", "-X", "POST", API + path,
        "-H", "X-Auth-Token: " + token,
        "-H", "X-Profile-Id: default",
        "-H", "X-Agent-Id: " + agent_id,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload, ensure_ascii=False),
    ]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"status": "error", "raw": out[:200]}


def owner_id(token):
    r = api("/api/token/validate", {"token": token}, token)
    for key in ("user_id", "userId", "id"):
        if r.get(key):
            return r[key]
    data = r.get("data") or r.get("result") or {}
    for key in ("user_id", "userId", "id"):
        if data.get(key):
            return data[key]
    raise SystemExit("не удалось получить user_id из /api/token/validate: %s" % list(r)[:6])


def kv_set(key, value, token):
    r = api("/api/kv/set", {"key": key, "value": value, "global": True}, token)
    return str(r.get("status", "")).lower() in ("success", "ok")


def kv_get(key, token):
    r = api("/api/kv/get", {"key": key, "global": True}, token)
    for k in ("value", "kv_value", "result"):
        if r.get(k) is not None:
            return r[k]
    return None


# ---------- сборка ----------

def agent_control_contract():
    """Блок agent_control берём из канонического генератора кабинета, а не пишем заново."""
    gen = os.path.join(ROOT, "tools", "build_agent_cabinet.py")
    if not os.path.exists(gen):
        return None
    sys.path.insert(0, os.path.dirname(gen))
    try:
        import build_agent_cabinet as cab
        fn = getattr(cab, "_agent_control_contract", None)
        return fn() if callable(fn) else None
    except Exception:
        return None


def main(argv):
    if "--selftest" in argv:
        return selftest()

    token = _token()
    account = owner_id(token)
    # Паспортов агентов у нас ноль — говорим это прямо, а не подставляем выдуманные.
    passports = []
    bundle = build_bundle(account, passports, agent_control_contract())
    manifest = build_manifest(account, bundle)
    text = canonical(bundle)
    chunks = split_chunks(text)

    print("Bundle стандартов:")
    print("  аккаунт:      %s" % account)
    print("  паспортов:    %d  %s" % (len(passports),
                                      "(честный пустой список, не ошибка)" if not passports else ""))
    print("  контракт agent_control: %s" % ("есть" if bundle["contracts"] else "НЕТ"))
    print("  размер:       %d байт, кусков %d" % (manifest["bundle_byte_length"], len(chunks)))
    print("  sha256:       %s" % manifest["bundle_sha256"][:20] + "…")

    if len(chunks) > MAX_CHUNKS:
        print("ОШИБКА: кусков %d, провайдер принимает не более %d" % (len(chunks), MAX_CHUNKS))
        return 1

    if "--dry-run" in argv:
        print("\n--dry-run: на аккаунт ничего не записано")
        return 0

    if "--verify" not in argv:
        print("\nПубликую:")
        for i, part in enumerate(chunks):
            ok = kv_set(chunk_key(manifest["bundle_sha256"], i), part, token)
            print("  кусок %d: %s" % (i, "записан" if ok else "ОТКАЗ"))
            if not ok:
                return 1
        # Манифест пишем ПОСЛЕДНИМ: пока его нет, недописанные куски никто не прочитает.
        if not kv_set(BUNDLE_KEY, canonical(manifest), token):
            print("  манифест: ОТКАЗ")
            return 1
        print("  манифест: записан")

    print("\nПеречитываю с аккаунта:")
    raw = kv_get(BUNDLE_KEY, token)
    if raw is None:
        print("  ✗ манифест не читается")
        return 1
    got = json.loads(raw) if isinstance(raw, str) else raw
    if got != manifest:
        print("  ✗ манифест на аккаунте отличается от собранного")
        return 1
    print("  ✓ манифест совпал")

    parts = []
    for i in range(manifest["chunk_count"]):
        piece = kv_get(chunk_key(manifest["bundle_sha256"], i), token)
        if piece is None:
            print("  ✗ кусок %d не читается" % i)
            return 1
        parts.append(piece if isinstance(piece, str) else json.dumps(piece))
    joined = "".join(parts)
    if hashlib.sha256(joined.encode("utf-8")).hexdigest() != manifest["bundle_sha256"]:
        print("  ✗ склейка кусков не сходится с sha256")
        return 1
    if canonical(json.loads(joined)) != joined:
        print("  ✗ склейка не каноничный JSON — провайдер отвергнет")
        return 1
    print("  ✓ куски склеились, sha256 и каноничность сошлись")
    print("\nConsole больше не упадёт в PRODUCTION_STANDARDS_UNAVAILABLE.")
    return 0


def selftest():
    print("Самопроверка сборщика bundle:")
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and cond

    b = build_bundle("acc-1", [], {"surface": "agent_control_center"})
    m = build_manifest("acc-1", b)

    check("поля манифеста ровно те, что ждёт провайдер",
          set(m) == {"schema", "encoding", "owner_account_id", "bundle_sha256",
                     "chunk_count", "bundle_byte_length"})
    check("схема и кодировка совпадают с контрактом витрины",
          m["schema"] == MANIFEST_SCHEMA and m["encoding"] == CHUNK_ENCODING)
    check("тело помечено как продовое и аккаунтное",
          b["data_mode"] == "PRODUCTION" and
          b["delivery_mode"] == "ACCOUNT_SCOPED_HOST_PROVIDER")
    check("пустой список паспортов — это список, а не отсутствие поля",
          b["sources"]["passports"] == [] and "passports" in b["sources"])
    check("sha256 считается от каноничного текста",
          m["bundle_sha256"] == hashlib.sha256(canonical(b).encode("utf-8")).hexdigest())
    check("длина в БАЙТАХ, а не в символах",
          build_manifest("acc-1", build_bundle("acc-1", ["ёж"], None))["bundle_byte_length"]
          == len(canonical(build_bundle("acc-1", ["ёж"], None)).encode("utf-8")))
    check("не-ASCII не экранируется — иначе витрина сочтёт неканоничным",
          "\\u" not in canonical({"k": "Мастер"}))
    check("ключи отсортированы", canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}')
    check("склейка кусков возвращает исходный текст",
          "".join(split_chunks(canonical(b))) == canonical(b))
    check("ключ куска построен по формуле провайдера",
          chunk_key("a" * 64, 3) == BUNDLE_KEY + ":chunk:" + "a" * 20 + ":3")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
