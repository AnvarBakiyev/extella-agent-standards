# expert: dev_connect_assistant
# description: Подключает ассистента (Claude/Codex) на ЭТОМ компьютере: кладёт ключ Extella в ~/.extella/api_token.txt с правами 600 и проверяет его рукопожатием. Ключ никуда не печатает. Параметры: token (передаёт платформа), проверить_только.

def dev_connect_assistant(token: str = "", проверить_только: str = "") -> str:
    """Одно действие вместо инструкции из пяти шагов.

    ЗАЧЕМ. Приложение Extella 1.3.0 не кладёт ключ на диск ни на одной системе
    (замер 24.09.2026: в сборке нет ни `api_token`, ни `token.txt`, ни `~/.extella/`).
    Поэтому на каждом новом компьютере ассистент оказывается без ключа, и человек
    упирается в «подключите Extella», не понимая, что именно сделать. Платформа при
    этом передаёт эксперту токен сама — значит подключение можно выполнить, а не
    объяснять.

    ЧЕСТНО О ГРАНИЦЕ. Токен приходит не всегда (замер 17.08.2026). Если его нет,
    эксперт не выдумывает обход, а называет единственное действие человека: экран
    токенов в приложении.

    БЕЗОПАСНОСТЬ. Значение ключа не возвращается и не пишется в журнал: наружу идут
    только путь, права и отпечаток (первые 8 символов sha256) — по нему можно
    сверить, тот ли ключ, не показывая сам ключ.
    """
    import hashlib
    import json
    import os
    import urllib.error
    import urllib.request

    дом = os.path.expanduser("~")
    папка = os.path.join(дом, ".extella")
    файл = os.path.join(папка, "api_token.txt")

    def отпечаток(значение: str) -> str:
        return hashlib.sha256(значение.encode("utf-8")).hexdigest()[:8]

    def рукопожатие(ключ: str) -> tuple:
        """Проверяем ключ живым вызовом, а не наличием файла: мёртвый ключ в файле
        выглядит как подключение и ломается позже."""
        запрос = urllib.request.Request(
            "https://api.extella.ai/api/agent/list",
            data=json.dumps({}).encode("utf-8"),
            headers={"X-Auth-Token": ключ, "X-Profile-Id": "default",
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(запрос, timeout=60) as о:
                return о.status == 200, f"HTTP {о.status}"
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}"
        except Exception as e:                                   # noqa: BLE001
            return False, type(e).__name__

    существующий = ""
    if os.path.exists(файл):
        try:
            with open(файл, encoding="utf-8") as f:
                существующий = f.read().strip()
        except OSError:
            существующий = ""

    ключ = (token or "").strip()
    # Плейсхолдер вместо значения — тот же случай, что «ключа нет».
    if ключ.startswith("{{"):
        ключ = ""

    if проверить_только:
        if not существующий:
            return json.dumps({"status": "error", "подключено": False,
                               "message": "Ключа на этом компьютере нет.",
                               "что_сделать": "В приложении Extella: Library → System → "
                                              "Tokens → создать токен и запустить это "
                                              "действие ещё раз."}, ensure_ascii=False)
        живой, как = рукопожатие(существующий)
        return json.dumps({"status": "success" if живой else "error",
                           "подключено": живой, "файл": файл,
                           "отпечаток": отпечаток(существующий), "ответ": как},
                          ensure_ascii=False)

    if not ключ:
        if существующий:
            живой, как = рукопожатие(существующий)
            if живой:
                return json.dumps({"status": "success", "подключено": True, "файл": файл,
                                   "отпечаток": отпечаток(существующий),
                                   "message": "Ключ уже на месте и работает."},
                                  ensure_ascii=False)
        return json.dumps({
            "status": "error", "подключено": False,
            "message": "Платформа не передала ключ этому вызову, а на диске рабочего нет.",
            "что_сделать": "В приложении Extella: Library → System → Tokens → создать "
                           "токен, скопировать и сохранить в ~/.extella/api_token.txt "
                           "(права 600). Присылать ключ в переписку не нужно никогда.",
        }, ensure_ascii=False)

    # Форма ключа проверяется до сети: иначе мусор возвращается как «платформа не приняла».
    if len(ключ) < 16 or not ключ.isascii() or any(с.isspace() for с in ключ):
        return json.dumps({"status": "error", "подключено": False,
                           "message": "Полученное значение не похоже на ключ Extella.",
                           "что_сделать": "Создать токен: Library → System → Tokens."},
                          ensure_ascii=False)

    живой, как = рукопожатие(ключ)
    if not живой:
        return json.dumps({"status": "error", "подключено": False,
                           "message": f"Ключ получен, но платформа его не приняла ({как}).",
                           "что_сделать": "Создать новый токен: Library → System → Tokens."},
                          ensure_ascii=False)

    try:
        os.makedirs(папка, exist_ok=True)
        # Пишем во временный файл и переносим: половина ключа на диске хуже, чем его отсутствие.
        временный = файл + ".tmp"
        with open(временный, "w", encoding="utf-8") as f:
            f.write(ключ + "\n")
        os.chmod(временный, 0o600)
        os.replace(временный, файл)
        os.chmod(файл, 0o600)
    except OSError as e:
        return json.dumps({"status": "error", "подключено": False,
                           "message": f"Не удалось записать ключ: {type(e).__name__}",
                           "что_сделать": "Проверить права на папку ~/.extella"},
                          ensure_ascii=False)

    return json.dumps({
        "status": "success", "подключено": True, "файл": файл, "права": "600",
        "отпечаток": отпечаток(ключ),
        "заменён_прежний": bool(существующий and существующий != ключ),
        "message": "Ключ на месте и проверен рукопожатием. Ассистент подключится без "
                   "дополнительных действий.",
    }, ensure_ascii=False)
