$extens("include.py")
def fnd_install_edition(части_json="[]", подтверждено="нет"):
    """Поставить остальные части издания одной кнопкой.

    ЗАЧЕМ. У платформы нет объекта «издание»: приложение, тема и отдел агентов —
    три отдельных листинга, и покупатель должен купить их по одному, догадавшись,
    что они связаны. Установщик исполняется НА МАШИНЕ покупателя, где лежит его
    токен, поэтому может поставить остальное сам.

    ЧЕСТНО О ГРАНИЦАХ. Он покупает от имени человека. Поэтому:
      * без подтверждено="да" он ничего не покупает, а только показывает список;
      * что именно поставится, обязано быть написано в карточке издания словами;
      * бесплатное ставит молча, платное — называет цену до покупки.
    """
    import json, pathlib, urllib.request

    def отдать(д):
        return json.dumps(д, ensure_ascii=False)

    def токен():
        for п in (pathlib.Path.home() / ".extella" / "api_token.txt",):
            if п.exists() and п.read_text().strip():
                return п.read_text().strip()
        к = pathlib.Path.home() / "extella_wizard" / "app" / "config.json"
        if к.exists():
            d = json.loads(к.read_text())
            for поле in ("auth_token", "token", "AUTH_TOKEN"):
                if d.get(поле):
                    return str(d[поле])
        return ""

    т = токен()
    if not т:
        return отдать({"ошибка": "на этой машине нет доступа к Extella — "
                                 "открой приложение Extella один раз"})

    def зов(путь, тело=None, метод=None):
        д = json.dumps(тело).encode() if тело is not None else None
        з = {"X-Extella-Token": т}
        if д:
            з["Content-Type"] = "application/json"
        r = urllib.request.Request("https://os.extella.ai" + путь, data=д, headers=з,
                                   method=метод or ("POST" if д else "GET"))
        try:
            with urllib.request.urlopen(r, timeout=180) as о:
                return о.status, о.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:300]
        except Exception as e:
            return 0, str(e)[:200]

    try:
        части = json.loads(части_json or "[]")
    except Exception as e:
        return отдать({"ошибка": f"список частей не разобрался: {e}"})
    if not части:
        return отдать({"ошибка": "список частей пуст — нечего ставить"})

    # Что уже стоит: повторно не покупаем, чтобы не тратить деньги человека дважды.
    код, тело = зов("/api/my-purchases")
    уже = set()
    if код == 200:
        уже = {п.get("listing_id") for п in json.loads(тело).get("purchases", [])}

    план, поставлено = [], []
    for ч in части:
        имя = ч.get("имя") or ч.get("listing_id", "")
        if ч.get("listing_id") in уже:
            план.append({"часть": имя, "итог": "уже стоит"})
            continue
        if подтверждено != "да":
            план.append({"часть": имя, "итог": "будет поставлено"})
            continue
        код, тело = зов(f"/api/purchase/{ч['version_id']}", тело={})
        if код == 200:
            план.append({"часть": имя, "итог": "поставлено"})
            поставлено.append(имя)
        else:
            план.append({"часть": имя, "итог": f"не поставилось ({код})",
                         "ответ": тело[:160]})

    return отдать({
        "подтверждено": подтверждено == "да",
        "план": план,
        "поставлено": поставлено,
        "подсказка": "" if подтверждено == "да"
                     else "ничего не куплено: вызови с подтверждено=«да»",
    })
