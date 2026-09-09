# description: Вход в Кабинет налогоплательщика КГД по ЭЦП на устройстве: подпись в NCALayer, сессия хранится локально и переиспользуется до истечения
def kgd_session(
    mode: str = "token",
    refresh_margin: int = 300,
    locale: str = "ru",
    store: str = "",
    force_login: bool = False,
):
    """Держит живую сессию Кабинета налогоплательщика КГД (knp.kgd.gov.kz).

    Зачем существует. Коннектор «Налогового радара» читает КГД только в живой
    ЭЦП-сессии, и до сих пор клиент логинился руками каждый день. Этот эксперт
    снимает ежедневный вход, НЕ трогая ключ: подпись делает NCALayer своим
    диалогом (человек сам выбирает ключ и вводит пароль — пароль нам не виден),
    а полученные токены сессии хранятся на устройстве и переиспользуются, пока
    живы. Ключ ЭЦП и пароль в эксперт не попадают вообще. Это ярус «сессия, не
    ключ»: человек подписывает вход только когда сессия действительно истекла.

    Протокол снят read-only из публичного бандла knp.kgd.gov.kz (09.09.2026):
      1. челлендж строит сам клиент: <body><text>{дата}</text></body>;
      2. NCALayer kz.gov.pki.knca.basics/sign, format=xml, encapsulate=true
         → body.result[0] — подписанный XML;
      3. POST /services/isnaknpuser/open-api/v2/user-by-eds {"signedData": xml}
         → access_token + refresh_token;
      4. POST /services/isnaknpuser/open-api/refresh-token (тело — refresh_token)
         за refresh_margin секунд до истечения JWT.

    Параметры:
      mode  — "token"  вернуть живой access_token (обновит или войдёт при нужде);
              "status" только состояние сессии, БЕЗ диалогов и сети —
                       безопасно звать сколько угодно;
              "logout" стереть сохранённую сессию.
      refresh_margin — за сколько секунд до истечения обновлять (как сайт: 300).
      locale — локаль диалога NCALayer.
      store  — путь к файлу сессии; пусто — ~/.extella/kgd_session.json (права 0600).
      force_login — войти заново подписью, даже если сессия жива.

    Железные правила: только вход и обновление сессии — никаких действий в
    кабинете; ключ/пароль не читаются и не хранятся; токены целиком в вывод не
    печатаются; подпись документов этим экспертом невозможна по построению.
    """
    import base64
    import json
    import os
    import time

    БАЗА = "https://knp.kgd.gov.kz"
    путь = os.path.expanduser(store or "~/.extella/kgd_session.json")

    # ── хранилище сессии (токены, не ключ) ───────────────────────────────────
    def прочитать():
        try:
            with open(путь, encoding="utf-8") as ф:
                return json.load(ф)
        except (OSError, ValueError):
            return {}

    def сохранить(данные):
        os.makedirs(os.path.dirname(путь), exist_ok=True)
        with open(путь, "w", encoding="utf-8") as ф:
            json.dump(данные, ф)
        os.chmod(путь, 0o600)

    def срок(jwt):
        """exp из JWT без проверки подписи — нужен только момент истечения."""
        try:
            тело = jwt.split(".")[1]
            тело += "=" * (-len(тело) % 4)
            return int(json.loads(base64.urlsafe_b64decode(тело)).get("exp", 0))
        except Exception:                                         # noqa: BLE001
            return 0

    def описать(данные):
        exp = срок(данные.get("access_token", ""))
        осталось = exp - int(time.time())
        return {"есть_сессия": bool(данные.get("access_token")),
                "истекает_через_сек": осталось if exp else None,
                "жива": осталось > refresh_margin,
                "есть_refresh": bool(данные.get("refresh_token"))}

    сессия = прочитать()

    if mode == "logout":
        try:
            os.remove(путь)
        except OSError:
            pass
        return {"ok": True, "сделано": "сессия стёрта"}

    if mode == "status":
        return {"ok": True, **описать(сессия)}

    # ── живой токен без диалога ───────────────────────────────────────────────
    if not force_login and описать(сессия)["жива"]:
        return {"ok": True, "источник": "кэш", "access_token": сессия["access_token"],
                **описать(сессия)}

    # ── обновление по refresh_token (без человека) ────────────────────────────
    if not force_login and сессия.get("refresh_token"):
        код, ответ = _post(БАЗА + "/services/isnaknpuser/open-api/refresh-token",
                           сессия["refresh_token"], как_json=False)
        if код == 200 and isinstance(ответ, dict) and ответ.get("access_token"):
            сессия = {"access_token": ответ["access_token"],
                      "refresh_token": ответ.get("refresh_token") or сессия["refresh_token"],
                      "xsrf": сессия.get("xsrf", "")}
            сохранить(сессия)
            return {"ok": True, "источник": "refresh", "access_token": сессия["access_token"],
                    **описать(сессия)}
        # refresh умер — честно идём на вход подписью

    # ── вход подписью: NCALayer сам спрашивает ключ и пароль ─────────────────
    xml = f"<body><text>{time.strftime('%a %b %d %Y %H:%M:%S GMT%z')}</text></body>"
    подпись = _подписать_в_ncalayer(xml, locale)
    if not подпись.get("ok"):
        return подпись
    код, ответ = _post(БАЗА + "/services/isnaknpuser/open-api/v2/user-by-eds",
                       {"signedData": подпись["xml"]})
    if код != 200 or not isinstance(ответ, dict) or not ответ.get("access_token"):
        return {"ok": False, "почему": "КГД не принял подпись входа",
                "http": код, "подробности": str(ответ)[:200],
                "что делать": "Проверить, что ключ действителен и не отозван: на "
                              "боевом кабинете просроченные и отозванные ключи "
                              "отклоняются; при повторе — снять ответ в DevTools."}
    сессия = {"access_token": ответ["access_token"],
              "refresh_token": ответ.get("refresh_token", ""),
              "xsrf": подпись.get("xsrf", "")}
    сохранить(сессия)
    return {"ok": True, "источник": "вход подписью", "access_token": сессия["access_token"],
            **описать(сессия)}


def _подписать_в_ncalayer(xml: str, locale: str) -> dict:
    """Подпись XML через NCALayer (wss://127.0.0.1:13579). Диалог — у человека."""
    import json
    import socket
    import ssl
    try:
        socket.create_connection(("127.0.0.1", 13579), timeout=3).close()
    except OSError:
        return {"ok": False, "почему": "NCALayer не запущен",
                "что делать": "Запустить NCALayer (он единственный носит ГОСТ-крипту "
                              "на устройстве; openssl без ГОСТ этот ключ не откроет)."}
    try:
        import websocket
    except Exception:                                             # noqa: BLE001
        return {"ok": False, "почему": "нет модуля websocket-client",
                "что делать": "Поставить websocket-client — им говорим с NCALayer."}
    запрос = {"module": "kz.gov.pki.knca.basics", "method": "sign",
              "args": {"allowedStorages": ["PKCS12", "AKKaztokenStore",
                                           "AKEToken72KStore", "AKEToken5110Store"],
                       "format": "xml", "data": xml,
                       "signingParams": {"decode": False, "encapsulate": True,
                                         "digested": False, "tsaProfile": False,
                                         "allowExpired": False, "allowRevoked": False},
                       "signerParams": {"extKeyUsageOids": [], "iin": "", "bin": "",
                                        "serialNumber": "", "chain": ""},
                       "locale": locale}}
    try:
        ws = websocket.create_connection("wss://127.0.0.1:13579",
                                         sslopt={"cert_reqs": ssl.CERT_NONE}, timeout=300)
        ws.recv()                                   # приветствие {"result":{"version":..}}
        ws.send(json.dumps(запрос))
        ответ = json.loads(ws.recv())
        ws.close()
    except Exception as беда:                                     # noqa: BLE001
        return {"ok": False, "почему": "NCALayer не ответил (отмена или таймаут)",
                "подробности": str(беда)[:160]}
    if ответ.get("status") is not True:
        return {"ok": False, "почему": "подпись не выполнена",
                "подробности": str(ответ.get("message") or ответ.get("body") or ответ)[:200],
                "что делать": "Если отменили диалог — просто повторить."}
    результат = (ответ.get("body") or {}).get("result") or []
    if not результат:
        return {"ok": False, "почему": "NCALayer вернул пустую подпись"}
    return {"ok": True, "xml": результат[0]}


def _post(url: str, тело, как_json: bool = True):
    """POST к КГД; кроме токенов ничего не хранится. Отказ — кодом, не стеком."""
    import json
    import urllib.error
    import urllib.request
    данные = json.dumps(тело).encode() if как_json else str(тело).encode()
    з = urllib.request.Request(url, data=данные, method="POST",
                               headers={"Content-Type": "application/json" if как_json
                                        else "text/plain", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(з, timeout=60) as о:
            текст = о.read().decode()
            код = о.status
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as e:                                        # noqa: BLE001
        return 0, f"не дошёл до КГД: {str(e)[:160]}"
    try:
        return код, json.loads(текст)
    except ValueError:
        return код, текст[:300]


def _selftest() -> int:
    """Без сети и без NCALayer: разбор JWT, хранилище, честные отказы."""
    import base64
    import json
    import os
    import tempfile
    import time
    провалы = []

    def случай(имя, условие):
        print(("  ✓ " if условие else "  ✗ ") + имя)
        if not условие:
            провалы.append(имя)

    print("Самопроверка kgd_session:")
    with tempfile.TemporaryDirectory() as d:
        путь = os.path.join(d, "s.json")
        # 1. пустое хранилище → статус честный, без диалога
        s = kgd_session(mode="status", store=путь)
        случай("пустая сессия → есть_сессия False", s["ok"] and not s["есть_сессия"])
        # 2. живой JWT в хранилище → токен из кэша, без сети и NCALayer
        exp = int(time.time()) + 3600
        тело = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
        jwt = f"x.{тело}.y"
        with open(путь, "w") as ф:
            json.dump({"access_token": jwt, "refresh_token": "r"}, ф)
        t = kgd_session(mode="token", store=путь)
        случай("живой токен отдаётся из кэша", t.get("ok") and t.get("источник") == "кэш")
        случай("истечение читается из JWT", 3500 < (t.get("истекает_через_сек") or 0) <= 3600)
        # 3. logout стирает файл
        kgd_session(mode="logout", store=путь)
        случай("logout стирает сессию", not os.path.exists(путь))
    # 4. NCALayer недоступен → честный отказ, не стек (порт заведомо закрыт)
    import socket
    try:
        socket.create_connection(("127.0.0.1", 13579), timeout=1).close()
        nca_жив = True
    except OSError:
        nca_жив = False
    if not nca_жив:
        о = _подписать_в_ncalayer("<body/>", "ru")
        случай("без NCALayer — честный отказ", not о.get("ok") and "NCALayer" in о.get("почему", ""))
    else:
        print("  ~ NCALayer запущен — проверку «его нет» пропускаю, диалог не дёргаю")
    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)
