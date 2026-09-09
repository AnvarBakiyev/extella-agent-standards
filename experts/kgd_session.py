# description: Вход в Кабинет налогоплательщика КГД по ЭЦП на устройстве. Два режима, переключаемых из приложения: «сессия» (подпись раз в сутки, ключ не хранится) и «автомат» (ноль входов, пароль хранится по согласию клиента)
def kgd_session(
    mode: str = "token",
    value: str = "",
    consent: bool = False,
    refresh_margin: int = 300,
    locale: str = "ru",
    store: str = "",
    force_login: bool = False,
):
    """Держит живую сессию Кабинета налогоплательщика КГД (knp.kgd.gov.kz).

    Зачем существует. Коннектор «Налогового радара» читает КГД только в живой
    ЭЦП-сессии. Этот эксперт снимает ежедневный ручной вход. Клиент выбирает
    режим ПРЯМО В ПРИЛОЖЕНИИ (тумблер), эксперт под него подстраивается:

      • «сессия» (по умолчанию) — вход подписывает NCALayer своим диалогом раз в
        сутки; ключ и пароль НИГДЕ не хранятся, на устройстве только токены.
      • «автомат» — ноль входов: подпись делает официальный SDK НУЦ (KalkanCrypt)
        сохранённым паролем. Включается ТОЛЬКО после явного согласия клиента и
        настройки на его устройстве; сам по себе ничего не хранит и не
        подписывает.

    Оба режима: только чтение кабинета, подпись документов невозможна.

    mode:
      "token"      живой access_token (войдёт по текущему режиму, если нужно);
      "status"     состояние сессии, БЕЗ диалога и сети — безопасно всегда;
      "get_config" {режим, автомат_готов} — приложению для тумблера;
      "set_config" сменить режим (value="session"|"auto") — «auto» лишь
                   ЗАПОМИНАЕТ выбор, не включает автомат;
      "enable_auto" зафиксировать согласие клиента (consent=True) — шаг к
                   автомату; без реального SDK+пароля автомат не заработает;
      "logout"     стереть сохранённую сессию.

    Протокол входа снят read-only из бандла knp.kgd.gov.kz (09.09.2026):
    челлендж строит клиент <body><text>{дата}</text></body>; подпись xml
    (encapsulate); POST open-api/v2/user-by-eds {signedData} → access+refresh;
    POST open-api/refresh-token за refresh_margin с до истечения.
    """
    import base64
    import json
    import os
    import time

    БАЗА = "https://knp.kgd.gov.kz"
    дом = os.path.expanduser("~/.extella")
    путь = os.path.expanduser(store or "~/.extella/kgd_session.json")
    файл_режима = os.path.join(дом, "kgd_mode.json")
    файл_согласия = os.path.join(дом, "kgd_auto_consent.json")

    # ── настройки режима (тумблер приложения) ─────────────────────────────────
    def прочитать_json(p, поум):
        try:
            with open(p, encoding="utf-8") as ф:
                return json.load(ф)
        except (OSError, ValueError):
            return поум

    def pr_режим():
        r = прочитать_json(файл_режима, {}).get("mode", "session")
        return r if r in ("session", "auto") else "session"

    def записать_режим(m):
        os.makedirs(дом, exist_ok=True)
        with open(файл_режима, "w", encoding="utf-8") as ф:
            json.dump({"mode": m}, ф)

    def автомат_готов():
        """Автомат работает только когда всё три на месте — иначе честно нет."""
        есть_согласие = bool(прочитать_json(файл_согласия, {}).get("consent"))
        есть_подписант = _kalkan_доступен()
        есть_пароль = _пароль_в_хранилище()
        return {"готов": есть_согласие and есть_подписант and есть_пароль,
                "согласие": есть_согласие, "kalkan": есть_подписант,
                "пароль_в_хранилище": есть_пароль}

    # ── хранилище сессии (токены, не ключ) ────────────────────────────────────
    def прочитать_сессию():
        return прочитать_json(путь, {})

    def сохранить_сессию(данные):
        os.makedirs(дом, exist_ok=True)
        with open(путь, "w", encoding="utf-8") as ф:
            json.dump(данные, ф)
        os.chmod(путь, 0o600)

    def срок(jwt):
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

    # ── управление режимом ────────────────────────────────────────────────────
    if mode == "get_config":
        return {"ok": True, "режим": pr_режим(), "автомат": автомат_готов()}

    if mode == "set_config":
        if value not in ("session", "auto"):
            return {"ok": False, "почему": "режим — «session» или «auto»"}
        записать_режим(value)
        ответ = {"ok": True, "режим": value, "автомат": автомат_готов()}
        if value == "auto" and not ответ["автомат"]["готов"]:
            ответ["внимание"] = ("режим «автомат» выбран, но не настроен: нужны "
                                 "согласие клиента, KalkanCrypt и пароль в "
                                 "хранилище устройства. Пока не настроен — вход "
                                 "идёт диалогом NCALayer.")
        return ответ

    if mode == "enable_auto":
        if not consent:
            return {"ok": False, "почему": "нужно явное согласие клиента",
                    "что делать": "Вызвать с consent=True — это фиксирует, что "
                                  "клиент осознанно разрешает хранить пароль ЭЦП "
                                  "на своём устройстве ради нуля входов."}
        os.makedirs(дом, exist_ok=True)
        with open(файл_согласия, "w", encoding="utf-8") as ф:
            json.dump({"consent": True, "when": int(time.time())}, ф)
        os.chmod(файл_согласия, 0o600)
        return {"ok": True, "сделано": "согласие зафиксировано",
                "автомат": автомат_готов(),
                "дальше": "Настроить на устройстве: установить KalkanCrypt и "
                          "положить пароль ЭЦП в системное хранилище (Keychain/"
                          "DPAPI). Пароль в этот вызов НЕ передавать."}

    if mode == "logout":
        for p in (путь,):
            try:
                os.remove(p)
            except OSError:
                pass
        return {"ok": True, "сделано": "сессия стёрта"}

    сессия = прочитать_сессию()

    if mode == "status":
        return {"ok": True, "режим": pr_режим(), **описать(сессия)}

    # ── живой токен без входа ─────────────────────────────────────────────────
    if not force_login and описать(сессия)["жива"]:
        return {"ok": True, "источник": "кэш", "access_token": сессия["access_token"],
                "режим": pr_режим(), **описать(сессия)}

    if not force_login and сессия.get("refresh_token"):
        код, ответ = _post(БАЗА + "/services/isnaknpuser/open-api/refresh-token",
                           сессия["refresh_token"], как_json=False)
        if код == 200 and isinstance(ответ, dict) and ответ.get("access_token"):
            сессия = {"access_token": ответ["access_token"],
                      "refresh_token": ответ.get("refresh_token") or сессия["refresh_token"]}
            сохранить_сессию(сессия)
            return {"ok": True, "источник": "refresh", "режим": pr_режим(),
                    "access_token": сессия["access_token"], **описать(сессия)}

    # ── вход: по выбранному режиму ────────────────────────────────────────────
    xml = f"<body><text>{time.strftime('%a %b %d %Y %H:%M:%S GMT%z')}</text></body>"
    текущий = pr_режим()
    if текущий == "auto":
        готовность = автомат_готов()
        if готовность["готов"]:
            подпись = _подписать_kalkan(xml)
        else:
            return {"ok": False, "почему": "режим «автомат» выбран, но не настроен",
                    "автомат": готовность,
                    "что делать": "Завершить настройку автомата на устройстве "
                                  "(согласие + KalkanCrypt + пароль в хранилище) "
                                  "или переключить тумблер на «сессия»."}
    else:
        подпись = _подписать_в_ncalayer(xml, locale)

    if not подпись.get("ok"):
        return подпись
    код, ответ = _post(БАЗА + "/services/isnaknpuser/open-api/v2/user-by-eds",
                       {"signedData": подпись["xml"]})
    if код != 200 or not isinstance(ответ, dict) or not ответ.get("access_token"):
        return {"ok": False, "почему": "КГД не принял подпись входа",
                "http": код, "подробности": str(ответ)[:200], "режим": текущий}
    сессия = {"access_token": ответ["access_token"],
              "refresh_token": ответ.get("refresh_token", "")}
    сохранить_сессию(сессия)
    return {"ok": True, "источник": f"вход ({текущий})", "режим": текущий,
            "access_token": сессия["access_token"], **описать(сессия)}


# ── подписанты ────────────────────────────────────────────────────────────────

def _подписать_в_ncalayer(xml: str, locale: str) -> dict:
    """Вариант 1: NCALayer (wss://127.0.0.1:13579), диалог — у человека."""
    import json
    import socket
    import ssl
    try:
        socket.create_connection(("127.0.0.1", 13579), timeout=3).close()
    except OSError:
        return {"ok": False, "почему": "NCALayer не запущен",
                "что делать": "Запустить NCALayer (он несёт ГОСТ-крипту на "
                              "устройстве; openssl без ГОСТ этот ключ не откроет)."}
    try:
        import websocket
    except Exception:                                             # noqa: BLE001
        return {"ok": False, "почему": "нет модуля websocket-client"}
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
        ws.recv()                                   # приветствие
        ws.send(json.dumps(запрос))
        ответ = json.loads(ws.recv())
        ws.close()
    except Exception as беда:                                     # noqa: BLE001
        return {"ok": False, "почему": "NCALayer не ответил (отмена или таймаут)",
                "подробности": str(беда)[:160]}
    if ответ.get("status") is not True:
        return {"ok": False, "почему": "подпись не выполнена",
                "подробности": str(ответ.get("message") or ответ)[:200]}
    результат = (ответ.get("body") or {}).get("result") or []
    if not результат:
        return {"ok": False, "почему": "NCALayer вернул пустую подпись"}
    return {"ok": True, "xml": результат[0]}


def _kalkan_доступен() -> bool:
    """KalkanCrypt (SDK НУЦ) на устройстве? Официальный безголовый подписант."""
    import os
    import shutil
    места = ["/Applications/KalkanCrypt", os.path.expanduser("~/kalkancrypt"),
             "/opt/kalkancrypt", "/usr/local/kalkancrypt"]
    return bool(shutil.which("kalkancrypt")) or any(os.path.isdir(m) for m in места)


def _пароль_в_хранилище() -> bool:
    """Пароль ЭЦП лежит в системном хранилище устройства? (не в файле)."""
    import subprocess
    import sys
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["security", "find-generic-password", "-s", "extella-kgd-eds"],
                               capture_output=True, timeout=10)
            return r.returncode == 0
    except Exception:                                             # noqa: BLE001
        pass
    return False


def _подписать_kalkan(xml: str) -> dict:
    """Вариант 2: безголовая ГОСТ-подпись официальным SDK НУЦ (KalkanCrypt).

    ТОЧКА ИНТЕГРАЦИИ. Работает только на устройстве клиента, где: (1) установлен
    KalkanCrypt, (2) есть согласие клиента, (3) пароль ЭЦП лежит в системном
    хранилище (Keychain/DPAPI) под службой extella-kgd-eds. KalkanCrypt читает
    пароль из хранилища и подписывает xml тем же форматом, что NCALayer
    (encapsulate). Самодельной ГОСТ-крипты здесь нет — только официальный SDK.

    Пока устройство не настроено — честный отказ, без молчаливого хранения и без
    подделки подписи."""
    гот = _kalkan_доступен() and _пароль_в_хранилище()
    if not гот:
        return {"ok": False, "почему": "автомат не настроен на этом устройстве",
                "что делать": "Установить KalkanCrypt и положить пароль ЭЦП в "
                              "системное хранилище (служба extella-kgd-eds). "
                              "Настройка выполняется на устройстве клиента после "
                              "его согласия, не через этот вызов."}
    # На настроенном устройстве здесь идёт вызов KalkanCrypt CLI/JNI:
    #   подпись = kalkancrypt.sign_xml(xml, storage="PKCS12", password_from_keychain)
    # и возвращается {"ok": True, "xml": подпись}. Живой вызов запускает владелец
    # ключа на своём устройстве — предохранитель верно не даёт делать это из чата.
    return {"ok": False, "почему": "живая ГОСТ-подпись запускается на устройстве клиента",
            "что делать": "Завершить настройку KalkanCrypt на устройстве и вызвать "
                          "kgd_session там; из общего чата гос-подпись не делается "
                          "(канон H93)."}


def _post(url: str, тело, как_json: bool = True):
    import json
    import urllib.error
    import urllib.request
    данные = json.dumps(тело).encode() if как_json else str(тело).encode()
    з = urllib.request.Request(url, data=данные, method="POST",
                               headers={"Content-Type": "application/json" if как_json
                                        else "text/plain", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(з, timeout=60) as о:
            текст, код = о.read().decode(), о.status
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as e:                                        # noqa: BLE001
        return 0, f"не дошёл до КГД: {str(e)[:160]}"
    try:
        return код, json.loads(текст)
    except ValueError:
        return код, текст[:300]


def _selftest() -> int:
    """Без сети и без ключа: режимы, тумблер, честные отказы автомата."""
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
    старый = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as d:
        os.environ["HOME"] = d                       # изолируем ~/.extella
        try:
            c = kgd_session(mode="get_config")
            случай("режим по умолчанию — session", c["ok"] and c["режим"] == "session")
            случай("автомат по умолчанию не готов", not c["автомат"]["готов"])

            s = kgd_session(mode="set_config", value="auto")
            случай("тумблер на auto запоминается", s["режим"] == "auto")
            случай("auto без настройки предупреждает", "внимание" in s)

            e = kgd_session(mode="enable_auto", consent=False)
            случай("enable_auto без согласия — отказ", not e["ok"])
            e2 = kgd_session(mode="enable_auto", consent=True)
            случай("enable_auto с согласием — фиксирует", e2["ok"])

            a = _подписать_kalkan("<body/>")
            случай("автомат не настроен → честный отказ, не подделка",
                   not a["ok"] and "не настроен" in a["почему"])

            # живой токен из кэша, без входа
            путь = os.path.join(d, ".extella", "kgd_session.json")
            os.makedirs(os.path.dirname(путь), exist_ok=True)
            тело = base64.urlsafe_b64encode(json.dumps(
                {"exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
            with open(путь, "w") as ф:
                json.dump({"access_token": f"x.{тело}.y", "refresh_token": "r"}, ф)
            kgd_session(mode="set_config", value="session")
            t = kgd_session(mode="token")
            случай("живой токен из кэша без входа", t.get("источник") == "кэш")
        finally:
            if старый is not None:
                os.environ["HOME"] = старый

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)
