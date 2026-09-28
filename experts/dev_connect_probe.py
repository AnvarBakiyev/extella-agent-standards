# expert: dev_connect_probe
# description: Measures which Extella key the platform hands an expert (from an app window or directly). Writes NOTHING and never returns the key: only whether it arrived, its length, an 8-char fingerprint, whether core and store accept it, and whether it matches the key already on this device.

def dev_connect_probe(token: str = "", метка: str = "") -> str:
    """Замер перед кнопкой «Подключить мой редактор». Ничего не пишет.

    ЗАЧЕМ. Кнопка в окне приложения должна положить ключ Extella в
    ~/.extella/api_token.txt. Неизвестно, КАКОЙ ключ платформа отдаёт эксперту,
    когда его зовёт окно: полный ключ аккаунта, узкий пропуск окна или ничего.
    Писать до ответа на этот вопрос нельзя: на машине, где уже лежит рабочий ключ,
    запись узкого пропуска сломала бы подключённого ассистента.

    Поэтому эксперт только описывает полученное:
      • пришёл ли ключ и не осталась ли на его месте неподставленная метка;
      • длина — у ключа аккаунта 36 знаков, у пропуска окна около двухсот (H5);
      • отпечаток — первые 8 знаков sha256, чтобы сверять, не показывая ключ;
      • пускает ли его ядро ЧИТАЮЩИМ вызовом (рукопожатие initialize пропускает
        любую строку, поправка 28.09.2026, H81) и пускает ли магазин;
      • совпадает ли он с ключом, который уже лежит на этой машине.

    Значение ключа не возвращается и не пишется никуда.
    """
    import hashlib
    import json
    import os
    import platform
    import urllib.error
    import urllib.request

    def отпечаток(значение):
        return hashlib.sha256(значение.encode("utf-8")).hexdigest()[:8]

    def код_ответа(запрос):
        try:
            with urllib.request.urlopen(запрос, timeout=40) as о:
                return о.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:                                   # noqa: BLE001
            return type(e).__name__

    ключ = (token or "").strip()
    метка_осталась = ключ.startswith("{{")
    пришёл = bool(ключ) and not метка_осталась

    итог = {
        "status": "success",
        "метка_вызова": метка,
        "система": platform.system(),
        "ключ_пришёл": пришёл,
        "осталась_неподставленная_метка": метка_осталась,
        "длина": len(ключ) if пришёл else 0,
        "записано_на_диск": False,
    }

    файл = os.path.join(os.path.expanduser("~"), ".extella", "api_token.txt")
    на_диске = ""
    if os.path.exists(файл):
        try:
            with open(файл, encoding="utf-8") as f:
                на_диске = f.read().strip()
        except OSError:
            на_диске = ""
    итог["ключ_на_диске_есть"] = bool(на_диске)

    if пришёл:
        итог["отпечаток"] = отпечаток(ключ)
        итог["совпадает_с_ключом_на_диске"] = bool(на_диске) and на_диске == ключ
        ядро = urllib.request.Request(
            "https://api.extella.ai/api/agent/list", data=b"{}",
            headers={"X-Auth-Token": ключ, "X-Profile-Id": "default",
                     "Content-Type": "application/json"}, method="POST")
        итог["ядро_читающий_вызов"] = код_ответа(ядро)
        магазин = urllib.request.Request(
            "https://os.extella.ai/api/my-listings",
            headers={"X-Extella-Token": ключ}, method="GET")
        итог["магазин_читающий_вызов"] = код_ответа(магазин)
    if на_диске:
        итог["отпечаток_ключа_на_диске"] = отпечаток(на_диске)

    return json.dumps(итог, ensure_ascii=False)
