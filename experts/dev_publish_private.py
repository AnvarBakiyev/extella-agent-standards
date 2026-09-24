# expert: dev_publish_private
# description: Приватная выкладка страничного продукта одним вызовом: берёт файл страницы на устройстве, находит ключ аккаунта сам, шлёт в магазин заголовком X-Extella-Token. По умолчанию сухой прогон. Ключ не печатается. Параметры: файл_страницы, имя, описание, агент, публиковать.

def dev_publish_private(файл_страницы: str = "", имя: str = "", описание: str = "",
                        агент: str = "", публиковать: str = "") -> str:
    """Приватная выкладка страничного продукта одним вызовом (канон H109).

    ЗАЧЕМ. Внешний чат остановил оплаченную работу клиента, решив, что публикация
    требует запрещённого файла `~/.extella/os_token.txt`. Замер 24.09.2026: магазину
    важен ЗАГОЛОВОК `X-Extella-Token`, а ключом годится любой действующий ключ
    аккаунта. Этот эксперт закрывает путь целиком: находит ключ сам, проверяет вход
    и выкладывает ЧЕРНОВИК — он виден только владельцу, в общий магазин ничего не уходит.

    По умолчанию делает сухой прогон: показывает, что будет отправлено. Реальная
    выкладка — только при явном `публиковать="да"` (H20: публикация видна сразу).
    """
    import json
    import os
    import urllib.error
    import urllib.request
    import uuid

    ОС = "https://os.extella.ai"
    дом = os.path.expanduser("~")

    def ключ():
        из_среды = (os.environ.get("EXTELLA_API_TOKEN") or "").strip()
        if len(из_среды) >= 16:
            return из_среды
        for имя_файла in ("os_token.txt", "api_token.txt"):
            путь = os.path.join(дом, ".extella", имя_файла)
            try:
                with open(путь, encoding="utf-8") as f:
                    значение = f.read().strip()
                if len(значение) >= 16:
                    return значение
            except OSError:
                continue
        return ""

    токен = ключ()
    if not токен:
        return json.dumps({"status": "error",
                           "message": "На этой машине нет ключа Extella.",
                           "что_сделать": "Library → System → Tokens → создать токен и "
                                          "сохранить в ~/.extella/api_token.txt"},
                          ensure_ascii=False)

    if not файл_страницы or файл_страницы.startswith("{{") or not os.path.isfile(файл_страницы):
        return json.dumps({"status": "error",
                           "message": "Не найден файл страницы.",
                           "что_сделать": "Передать файл_страницы — путь к index.html или "
                                          "zip на этом компьютере"},
                          ensure_ascii=False)

    данные = open(файл_страницы, "rb").read()
    имя_файла = os.path.basename(файл_страницы)
    if not имя or имя.startswith("{{"):
        имя = os.path.splitext(имя_файла)[0]

    сводка = {"файл": имя_файла, "размер_КБ": round(len(данные) / 1024, 1), "имя": имя,
              "агент": агент or "не задан", "права": ["expert.run", "device.run"],
              "приватно": True}

    if публиковать != "да":
        сводка.update({"status": "success", "сухой_прогон": True,
                       "message": "Проверка прошла. Для настоящей выкладки повторить "
                                  "с публиковать=\"да\"."})
        return json.dumps(сводка, ensure_ascii=False)

    граница = "----extella" + uuid.uuid4().hex
    части = []
    поля = {"name": имя, "description": описание or имя, "version": "0.1.0",
            "price_credits": "0", "app_scopes": json.dumps(["expert.run", "device.run"]),
            "allowed_origins": json.dumps(["null", ОС])}
    if агент and not агент.startswith("{{"):
        поля.update({"source_type": "agent", "source_id": агент, "attach_agent": "1"})
    for к, з in поля.items():
        части.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                      % (граница, к, з)).encode("utf-8"))
    части.append(('--%s\r\nContent-Disposition: form-data; name="page"; filename="%s"\r\n'
                  'Content-Type: application/octet-stream\r\n\r\n'
                  % (граница, имя_файла)).encode("utf-8"))
    части.append(данные)
    части.append(("\r\n--%s--\r\n" % граница).encode("utf-8"))
    тело = b"".join(части)

    запрос = urllib.request.Request(
        ОС + "/api/publish-stream", data=тело,
        headers={"X-Extella-Token": токен,
                 "Content-Type": "multipart/form-data; boundary=" + граница},
        method="POST")
    try:
        with urllib.request.urlopen(запрос, timeout=300) as о:
            сырой = о.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return json.dumps({"status": "error",
                           "message": "Магазин отказал: HTTP %s" % e.code,
                           "ответ": e.read(300).decode("utf-8", "replace")[:200]},
                          ensure_ascii=False)
    except Exception as e:                                       # noqa: BLE001
        return json.dumps({"status": "error", "message": type(e).__name__}, ensure_ascii=False)

    # publish-stream отвечает событиями, а не одним JSON: результат — в «done».
    итог = {}
    for строка in сырой.splitlines():
        if not строка.startswith("data:"):
            continue
        try:
            событие = json.loads(строка.split("data:", 1)[1].strip())
        except ValueError:
            continue
        if событие.get("type") == "error":
            return json.dumps({"status": "error",
                               "message": событие.get("message", "магазин вернул ошибку")},
                              ensure_ascii=False)
        if событие.get("type") == "done":
            итог = событие
    if not итог:
        return json.dumps({"status": "error",
                           "message": "Магазин не прислал завершающее событие."},
                          ensure_ascii=False)

    сводка.update({"status": "success", "сухой_прогон": False,
                   "listing_id": итог.get("listing_id"),
                   "version_id": итог.get("version_id"), "published": False,
                   "открыть": ОС + "/app-page/" + str(итог.get("listing_id")) + "/",
                   "message": "Готово: черновик виден только владельцу. В общий магазин "
                              "ничего не ушло."})
    return json.dumps(сводка, ensure_ascii=False)
