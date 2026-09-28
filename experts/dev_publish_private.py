# expert: dev_publish_private
# description: Выкладка страничного продукта одним вызовом, скрытая из каталога: берёт файл страницы на устройстве, находит ключ аккаунта сам, шлёт в магазин заголовком X-Extella-Token и перечитывает созданную версию. По умолчанию сухой прогон — ничего не отправляет. Ключ не печатается. Параметры: файл_страницы, имя, описание, теги, агент, публиковать.

def dev_publish_private(файл_страницы: str = "", имя: str = "", описание: str = "",
                        теги: str = "", агент: str = "", публиковать: str = "") -> str:
    """Приватная выкладка страничного продукта одним вызовом (канон H109).

    ЗАЧЕМ. Внешний чат остановил оплаченную работу клиента, решив, что публикация
    требует запрещённого файла `~/.extella/os_token.txt`. Замер 24.09.2026: магазину
    важен ЗАГОЛОВОК `X-Extella-Token`, а ключом годится любой действующий ключ
    аккаунта. Этот эксперт закрывает путь целиком: находит ключ сам и выкладывает
    версию, СКРЫТУЮ ИЗ КАТАЛОГА (`published: false`).

    Скрытая из каталога — не значит закрытая: тело листинга сейчас видно и
    постороннему (письмо платформе §24). Поэтому эксперт не обещает приватность.

    По умолчанию — сухой прогон: показывает, что БУДЕТ отправлено, и честно говорит,
    что в сеть не ходил. Реальная выкладка — только при `публиковать="да"`.

    ПОПРАВКИ 28.09.2026 (аудит, F07): без поля `tags` магазин отвечает HTTP 400 — на
    этом встал участник обучения; сухой прогон называл себя «проверка прошла», хотя
    сети не касался; успех объявлялся по событию `done` без перечитывания версии; а
    ссылка `/app-page/<id>/` отдаёт 401 — её давать нельзя.
    """
    import json
    import os
    import urllib.error
    import urllib.request
    import uuid

    ОС = "https://os.extella.ai"
    дом = os.path.expanduser("~")

    # Порядок — как у platform_client.источники("магазин"): эксперт живёт на
    # устройстве и импортировать модуль репозитория не может, поэтому копия; её
    # расхождение с каноном — это H78, сверяет самопроверка обвязки.
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

    список_тегов = [т.strip() for т in (теги or "").split(",")
                    if т.strip() and not т.strip().startswith("{{")]
    if not список_тегов:
        # До сети, а не после: магазин ответит 400 «At least one tag is required»,
        # и человек будет искать причину в ключе или в файле.
        return json.dumps({"status": "error",
                           "message": "Нужен хотя бы один тег — без него магазин отвечает "
                                      "HTTP 400.",
                           "что_сделать": "Передать теги через запятую, например "
                                          "теги=\"документы, учёт\""},
                          ensure_ascii=False)

    сводка = {"файл": имя_файла, "размер_КБ": round(len(данные) / 1024, 1), "имя": имя,
              "теги": список_тегов, "агент": агент or "не задан",
              "права": ["expert.run", "device.run"], "скрыт_из_каталога": True}

    if публиковать != "да":
        # «dry_run», а не «success»: сухой прогон не касался сети и ничего не
        # доказывает про магазин. Называть его успешной проверкой — ложный зелёный.
        сводка.update({"status": "dry_run", "сухой_прогон": True,
                       "в_сеть_ходили": False,
                       "message": "Ничего не отправлено. Так будет выглядеть выкладка; "
                                  "для настоящей повторить с публиковать=\"да\"."})
        return json.dumps(сводка, ensure_ascii=False)

    граница = "----extella" + uuid.uuid4().hex
    части = []
    поля = {"name": имя, "description": описание or имя, "version": "0.1.0",
            "price_credits": "0", "app_scopes": json.dumps(["expert.run", "device.run"]),
            "allowed_origins": json.dumps(["null", ОС]),
            "tags": json.dumps(список_тегов, ensure_ascii=False)}
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

    лид, вид = итог.get("listing_id"), итог.get("version_id")

    # ПЕРЕЧИТЫВАЕМ, А НЕ ВЕРИМ СОБЫТИЮ. «done» говорит, что поток кончился; есть ли
    # версия в листинге и скрыт ли он — отвечает только чтение самого листинга.
    проверено, published = False, None
    if лид:
        try:
            чтение = urllib.request.Request(ОС + "/api/listing/" + str(лид),
                                            headers={"X-Extella-Token": токен})
            with urllib.request.urlopen(чтение, timeout=60) as о:
                карточка = json.loads(о.read().decode("utf-8", "replace"))
            листинг = карточка.get("listing", карточка)
            published = листинг.get("published")
            версии = карточка.get("versions") or листинг.get("versions") or []
            проверено = any(str(в.get("id")) == str(вид) for в in версии
                            if isinstance(в, dict)) if вид else False
        except Exception:                                        # noqa: BLE001
            проверено = False

    сводка.update({"status": "success" if проверено else "unverified",
                   "сухой_прогон": False, "в_сеть_ходили": True,
                   "listing_id": лид, "version_id": вид,
                   "published": published, "версия_перечитана": проверено,
                   # Ссылки не даём: /app-page/<id>/ отдаёт 401. Путь — словами.
                   "где_найти": "ОС → Магазин → мои продукты → " + имя,
                   "message": ("Версия создана и перечитана из листинга. Листинг скрыт "
                               "из каталога; приватность содержимого платформой не "
                               "подтверждена (§24)." if проверено else
                               "Магазин прислал «done», но перечитать версию не удалось — "
                               "успехом это не считаем. Проверь листинг руками.")})
    return json.dumps(сводка, ensure_ascii=False)
