# description: Создать НЕопубликованный листинг-черновик для витрины «День первый»: имя и части от человека, страница собирается тут же. Публикации нет, покупки нет — черновик видит только владелец и удалить его можно в одно нажатие.
def journey_publish(name: str = "", parts: str = "") -> str:
    # Черновик, а не публикация, и БЕЗ покупки себе — намеренно. H20: у
    # опубликованного листинга каждая версия уходит в магазин сразу. H26 и
    # опыт деплоя: покупка делает листинг неудаляемым. Витрина не имеет права
    # оставлять после себя вечный мусор, поэтому создаётся ровно то, что
    # человек может стереть одним нажатием.
    # Страничный продукт публикуется БЕЗ source_type/attach_agent/source_id
    # (H53): с ними он встал бы дополнением к агенту и наплодил бы клонов.
    import json, os, re, urllib.request, uuid

    имя = (name or "").strip()[:60] or "Моё первое приложение"
    части = [ч.strip() for ч in (parts or "").split("|") if ч.strip()][:8]
    if not части:
        return json.dumps({"status": "error",
                           "message": "нет частей: собери хотя бы две"}, ensure_ascii=False)

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

    ток = токен()
    if not ток:
        return json.dumps({"status": "error",
                           "message": "нет доступа к Extella на этом устройстве: "
                                      "открой приложение один раз"}, ensure_ascii=False)

    шаги = "".join("<li>" + ч.replace("<", "&lt;") + "</li>" for ч in части)
    страница = ("<!doctype html><meta charset='utf-8'><title>" + имя.replace("<", "&lt;") +
                "</title><body style=\"font-family:Georgia,serif;background:#FAF9F5;"
                "color:#0A0A0A;max-width:640px;margin:48px auto;padding:0 24px\">"
                "<p style='font-family:monospace;font-size:11px;color:#2F6B66'>"
                "СОБРАНО В «ДЕНЬ ПЕРВЫЙ»</p><h1>" + имя.replace("<", "&lt;") + "</h1>"
                "<p>Порядок работы:</p><ol>" + шаги + "</ol>"
                "<p style='color:#7A7A7A'>Черновик. Публикация — отдельное решение "
                "владельца.</p></body>")

    граница = uuid.uuid4().hex
    поля = {"version": "1.0.0", "price_credits": "0", "name": имя,
            "description": "Собрано в обучении «День первый»: " + ", ".join(части[:3]) + "…",
            "tags": json.dumps(["day-one", "draft"])}
    куски = []
    for k, v in поля.items():
        куски.append(("--" + граница + "\r\nContent-Disposition: form-data; name=\"" + k +
                      "\"\r\n\r\n" + v + "\r\n").encode())
    куски.append(("--" + граница + "\r\nContent-Disposition: form-data; name=\"page\"; "
                  "filename=\"index.html\"\r\nContent-Type: text/html\r\n\r\n").encode()
                 + страница.encode() + b"\r\n")
    куски.append(("--" + граница + "--\r\n").encode())

    з = urllib.request.Request("https://os.extella.ai/api/publish-stream",
                               data=b"".join(куски),
                               headers={"X-Extella-Token": ток,
                                        "Content-Type": "multipart/form-data; boundary=" + граница},
                               method="POST")
    try:
        with urllib.request.urlopen(з, timeout=120) as о:
            ответ = о.read().decode()
    except Exception as e:
        return json.dumps({"status": "error",
                           "message": "магазин не принял черновик: " + str(e)[:120]},
                          ensure_ascii=False)

    м = re.search(r'"listing_id"\s*:\s*"([0-9a-f-]{36})"', ответ)
    if not м:
        return json.dumps({"status": "error",
                           "message": "черновик не создался: в ответе нет идентификатора "
                                      "(начало: " + ответ[:100].replace('"', "'") + ")"},
                          ensure_ascii=False)
    return json.dumps({"status": "success", "listing_id": м.group(1), "name": имя,
                       "parts": len(части), "published": False,
                       "message": "черновик создан — не опубликован, виден только тебе"},
                      ensure_ascii=False)
