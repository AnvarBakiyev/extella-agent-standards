# description: Разведка возможностей этого человека для витрины «День первый»: есть ли кредиты на аккаунте, поднята ли локальная модель, отвечает ли Доска схем. Ничего не запускает и не тратит — только смотрит.
def journey_capabilities() -> str:
    # Витрина обязана вести человека по ТОМУ, что у него есть, а не по тому,
    # что есть у автора. Разведка отвечает быстро и никогда не отказывает
    # целиком: каждый пункт независим, недостающее — не поломка, а развилка.
    import json, os, urllib.request

    def токен():
        t = (os.environ.get("EXTELLA_API_TOKEN") or "").strip()
        if len(t) >= 8:
            return t
        for п in (os.path.expanduser("~/.extella/os_token.txt"),
                  os.path.expanduser("~/.extella/api_token.txt")):
            try:
                with open(п, "r", encoding="utf-8") as f:
                    t = f.read().strip()
                if len(t) >= 8:
                    return t
            except Exception:
                pass
        try:
            with open(os.path.expanduser("~/extella_wizard/app/config.json"),
                      "r", encoding="utf-8") as f:
                d = json.loads(f.read())
            for k in ("auth_token", "token"):
                if d.get(k):
                    return str(d[k])
        except Exception:
            pass
        return ""

    итог = {"status": "success", "credits": 0, "local_model": "",
            "board": False, "account": False}
    ток = токен()
    итог["account"] = bool(ток)

    if ток:
        try:
            з = urllib.request.Request("https://os.extella.ai/api/balance",
                                       headers={"X-Extella-Token": ток})
            with urllib.request.urlopen(з, timeout=20) as о:
                итог["credits"] = int(json.loads(о.read().decode()).get("balance") or 0)
        except Exception:
            pass

    # Локальная модель: спрашиваем список у LM Studio, имя не угадываем.
    try:
        with urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=6) as о:
            имена = [str(m.get("id", "")) for m in json.loads(о.read().decode()).get("data", [])]
        годные = [и for и in имена
                  if "embed" not in и.lower() and "reasoning" not in и.lower()]
        # Тот же список предпочтений, что и у самого вызова модели: разведка
        # обязана называть модель, которая ДЕЙСТВИТЕЛЬНО ответит, иначе она
        # обещает одно, а человек получает другое (порядок в списке не постоянен).
        выбрана = ""
        for метка in ("gemma-2-9b", "ministral-3-3b", "gemma", "ministral"):
            совпало = [и for и in годные if метка in и.lower()]
            if совпало:
                выбрана = совпало[0]
                break
        итог["local_model"] = выбрана or (годные or имена or [""])[0]
    except Exception:
        pass

    # Доска схем: отвечает ли соседнее приложение на своём порту.
    try:
        with urllib.request.urlopen("http://127.0.0.1:34786/_extella_storage", timeout=6):
            итог["board"] = True
    except Exception:
        pass

    return json.dumps(итог, ensure_ascii=False)
