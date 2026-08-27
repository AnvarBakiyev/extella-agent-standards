# description: Создать НЕопубликованный листинг-черновик для витрины «День первый»: имя и части от человека, страница собирается тут же — с его цифрами, интерактивным чек-листом и правилом дома. Публикации нет, покупки нет — черновик видит только владелец и удалить его можно в одно нажатие.
def journey_publish(name: str = "", parts: str = "", stats: str = "", rule: str = "") -> str:
    # Черновик, а не публикация, и БЕЗ покупки себе — намеренно. H20: у
    # опубликованного листинга каждая версия уходит в магазин сразу. H26 и
    # опыт деплоя: покупка делает листинг неудаляемым. Витрина не имеет права
    # оставлять после себя вечный мусор, поэтому создаётся ровно то, что
    # человек может стереть одним нажатием.
    # Страничный продукт публикуется БЕЗ source_type/attach_agent/source_id
    # (H53): с ними он встал бы дополнением к агенту и наплодил бы клонов.
    #
    # Страница — не записка, а маленькое работающее приложение (решение
    # владельца 22.08.2026): цифры ИЗ прогона человека, чек-лист порядка с
    # отметками и правило дома. Отметки живут, пока окно открыто: песочница
    # окна магазина не даёт localStorage, и врать «сохранено» нельзя.
    import base64, json, os, re, urllib.request, uuid

    имя = (name or "").strip()[:60] or "Порядок в Загрузках"
    части = [ч.strip() for ч in (parts or "").split("|") if ч.strip()][:8]
    if not части:
        return json.dumps({"status": "error",
                           "message": "нет частей: собери хотя бы две"}, ensure_ascii=False)

    цифры = {}
    try:
        цифры = json.loads(stats) if stats else {}
        if not isinstance(цифры, dict):
            цифры = {}
    except Exception:
        цифры = {}
    правило = (rule or "").strip()[:400]

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

    def безопасно(т):
        return str(т).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Блок «твои цифры» — только если разведка их передала.
    цифры_html = ""
    if цифры.get("files"):
        кат = цифры.get("categories") or {}
        строки_кат = "".join(
            "<div class='ряд'><span>" + безопасно(к.lower()) + "</span>"
            "<span class='чис'>" + безопасно(v) + "</span></div>"
            for к, v in list(кат.items())[:6])
        цифры_html = (
            "<section class='карта'><p class='метка'>твои цифры за день первый</p>"
            "<p class='большое'>" + безопасно(цифры.get("files")) + " файлов · " +
            безопасно(цифры.get("gb", "?")) + " гб</p>" + строки_кат + "</section>")

    пункты = "".join(
        "<li><label><input type='checkbox' data-шаг> <span>" + безопасно(ч) +
        "</span></label></li>" for ч in части)

    правило_html = ""
    if правило:
        правило_html = ("<section class='карта дом'><p class='метка'>правило этого дома</p>"
                        "<blockquote>" + безопасно(правило) + "</blockquote>"
                        "<p class='тихо'>Правило читается всегда и имеет приоритет: "
                        "даже кнопка ему не указ.</p></section>")

    страница = ("<!doctype html><html lang='ru'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + безопасно(имя) + "</title><style>"
        ":root{--фон:#FAF9F5;--пов:#FFFFFF;--текст:#0A0A0A;--акцент:#C57E33;"
        "--система:#2F6B66;--граница:#D7E0DC;--тихо:#7A7A7A}"
        "body{background:var(--фон);color:var(--текст);margin:0;"
        "font:400 15px/1.6 Nunito,-apple-system,sans-serif}"
        "button,input{font-family:inherit}"
        "main{max-width:640px;margin:0 auto;padding:48px 24px 64px}"
        "h1{font:400 26px/1.2 'Source Serif 4',Georgia,serif;margin:8px 0 24px}"
        ".метка{font:400 11px/1.4 'JetBrains Mono',monospace;color:var(--система);"
        "letter-spacing:.06em;margin:0 0 8px}"
        ".карта{background:var(--пов);border:1px solid var(--граница);"
        "border-radius:12px;padding:16px;margin:0 0 16px}"
        ".большое{font:400 20px/1.3 'Source Serif 4',Georgia,serif;margin:0 0 12px}"
        ".ряд{display:flex;justify-content:space-between;padding:4px 0;"
        "border-top:1px solid var(--граница)}"
        ".чис{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--система)}"
        "ol{list-style:none;margin:0;padding:0}"
        "ol li{padding:8px 0;border-top:1px solid var(--граница)}"
        "ol li:first-child{border-top:0}"
        "label{display:flex;gap:12px;align-items:baseline;cursor:pointer}"
        "input[type=checkbox]{accent-color:var(--акцент)}"
        ":checked+span{color:var(--тихо);text-decoration:line-through}"
        "blockquote{margin:0;font:400 15px/1.5 'Source Serif 4',Georgia,serif}"
        ".дом{border-color:var(--система)}"
        ".тихо{color:var(--тихо);font-size:13px;margin:8px 0 0}"
        ".счёт{font-family:'JetBrains Mono',monospace;font-size:13px;"
        "color:var(--система);margin:12px 0 0}"
        ".сброс{background:none;border:1px solid var(--граница);border-radius:8px;"
        "padding:8px 16px;font-size:13px;color:var(--текст);cursor:pointer;margin-top:12px}"
        "</style><body><main>"
        "<p class='метка'>собрано в «день первый»</p>"
        "<h1>" + безопасно(имя) + "</h1>" + цифры_html +
        "<section class='карта'><p class='метка'>порядок работы</p>"
        "<ol>" + пункты + "</ol>"
        "<p class='счёт' id='счёт'>сделано 0 из " + str(len(части)) + "</p>"
        "<button class='сброс' id='сброс'>Снять отметки</button>"
        "<p class='тихо'>Отметки живут, пока окно открыто: черновик ничего не "
        "записывает на диск.</p></section>" + правило_html +
        "<p class='тихо'>Черновик. Публикация — отдельное решение владельца.</p>"
        "</main><script>"
        "(function(){var к=[].slice.call(document.querySelectorAll('[data-шаг]'));"
        "var с=document.getElementById('счёт');"
        "function считать(){var н=к.filter(function(x){return x.checked;}).length;"
        "с.textContent='сделано '+н+' из '+к.length;}"
        "к.forEach(function(x){x.addEventListener('change',считать);});"
        "document.getElementById('сброс').onclick=function(){"
        "к.forEach(function(x){x.checked=false;});считать();};"
        "})();</script></body></html>")

    # Плитка Bronze Engraved, отрисованная каноническим tools/bronze_icon.py
    # (глиф clipboard-check, 256px) и вшитая сюда картинкой: на устройстве нет
    # ни Chrome, ни набора Lucide, а генерировать плитку «своими руками» —
    # значит завести второй источник стиля. Без иконки продукт приезжает на
    # рабочий стол безымянным серым квадратом (замер владельца 23.08.2026).
    ИКОНКА_BASE64 = (
        "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"
        "H2C+MyBwfXWq/8T56dPTHV1MEOb7l6+evbZy/sTnOtPT5yem5g7l3eXdZu9AMdDIporVApUhlcOzcNtRHFwOr0hSG8+BI8ze"
        "wMSo9fE6jySikUVMn9irFAMviHSHpik8slFkZ2Aichi0uScn9+/6gVimv31Iwt6I782LZ/NrZwvHP1X+Zh+6qy+uXHrhdy4/"
        "8ce/uXDx3MViwn/+22fxlU8+s/PZ5Xy6PxE4fZj3l9+J0H/QxJ+R9bC/kVHCf9T9YP+lvk/WP0jqR8jflzg4lH8vmvJ91WfF"
        "zVZsv7cqbd3I6mr197FuVa7W5VoNHGs7qnK2Z895D7q9XhVp9PtOT6/+u3ftmvrxd0y97uBO3Ku0njSfHbj7gftmb7rzPZ2p"
        "nfcYI5yY3QM1uxeduT0wmOiX+Kyz2PDWhqu0npMc0kcSfGKtZhoCApB1F07bOQFSr3fcgYCJO1/WCcjUqCScO0AF2B19NKwn"
        "KMTqgRPndF2/6g8osuMyCqJbVzebxfLV68gXLxflQvl5vrr01MqFU5+49OzXnzT2UXDJ2rklPPUHX1p7ZmLPntKZqPPH8v5R"
        "Qv8k+yee+x8i/B9Ud58PCwDssw+K72MgME8+syBAHV6CgASA8rP1gkBRHp1amHrLfdOvOTjbe03B+GV0teeWO26aO3LvOybm"
        "9rwlm5zcr3WGzuzOIirYgWymiGU6O8tQpAzP3d77SLiuNZtgc5thCPNl3qfDfQN2IrI+306UxUCEztZb27ZELsN+Wg8ihwBE"
        "CGPywANt5giCOYNtIroIK/O1wiu7S9BFaWb0688v95auPLx85ukvXTt78rz5rJPr1XNL+vifPNU/camY5LNOv17nNzJo2c99"
        "JtjfAkAT+wsAiHX+xgCAkWGiACMSBCwAGEmBwCoBg1FBwP490b2a/ciDc7cfnOnfU8RoO+x3B+/6rrunDt3+9mLZ8H7V6exx"
        "NztR5CqTM8gmi0CsmDcwuwyzyblyA3r7ibxY2bzjLpxDELl8sONOk7cAt1hNGFBS/Vlmd+Bl7EGb7VSW28B7K8Xq70o5i29e"
        "zFHM4Juf4vagpPNr/ZX5J1YuvviVKye+6X6bT/f0woWlzlMff3zylKlThx/V+Y20Cf2bdv2Nif1Tn5WfU+dfdxpgZKNTASNt"
        "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"
        "Cra1AAAAAElFTkSuQmCC"
    )

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
    куски.append(("--" + граница + "\r\nContent-Disposition: form-data; name=\"icon\"; "
                  "filename=\"icon.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
                 + base64.b64decode(ИКОНКА_BASE64) + b"\r\n")
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
    лид = м.group(1)

    # Плитка на рабочий стол ставится ЗДЕСЬ, а не руками через «Buy & Deploy».
    # Замер 23.08.2026: purchase-stream у бесплатного неопубликованного
    # черновика заводит ярлык (событие webapp с shortcut_id), и листинг после
    # этого ОСТАЁТСЯ удаляемым — DELETE /api/listing отвечает 200. Прежний
    # страх «покупка делает листинг вечным» относился к опубликованным (H26),
    # к своему черновику он не применяется.
    мв = re.search(r'"version_id"\s*:\s*"([0-9a-f-]{36})"', ответ)
    вид = мв.group(1) if мв else ""
    if not вид:
        try:
            з2 = urllib.request.Request("https://os.extella.ai/api/my-listings",
                                        headers={"X-Extella-Token": ток})
            with urllib.request.urlopen(з2, timeout=60) as о2:
                свои = json.loads(о2.read().decode()).get("listings", [])
            for л in свои:
                if str(л.get("id") or "") == лид and (л.get("versions") or []):
                    вид = str((л["versions"][0]).get("id") or "")
                    break
        except Exception:
            вид = ""

    на_столе = False
    если_не_вышло = ""
    if вид:
        try:
            з3 = urllib.request.Request(
                "https://os.extella.ai/api/purchase-stream/" + вид,
                data=b"{}", method="POST",
                headers={"X-Extella-Token": ток, "Content-Type": "application/json"})
            with urllib.request.urlopen(з3, timeout=180) as о3:
                поток = о3.read().decode()
            на_столе = ('"webapp"' in поток) or ('"done"' in поток)
            if not на_столе:
                если_не_вышло = "установка не подтвердилась"
        except Exception as e:
            если_не_вышло = str(e)[:100]
    else:
        если_не_вышло = "не нашёлся номер версии"

    итог = {"status": "success", "listing_id": лид, "name": имя,
            "parts": len(части), "published": False,
            "with_stats": bool(цифры_html), "with_rule": bool(правило_html),
            "with_icon": True, "on_desktop": на_столе}
    itog_msg = ("приложение создано и поставлено на рабочий стол — не опубликовано, "
                "видишь только ты")
    if not на_столе:
        itog_msg = ("черновик создан, но плитка на рабочий стол не встала: " +
                    (если_не_вышло or "причина неизвестна") +
                    ". Открой магазин и нажми Buy & Deploy у этой карточки.")
    итог["message"] = itog_msg
    return json.dumps(итог, ensure_ascii=False)
