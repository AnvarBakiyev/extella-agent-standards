$extens("include.py")
def bld_edition(действие="состояние", подтверждено="нет"):
    """Издание для сборщика: показать состояние и поставить недостающее.

    ЗАЧЕМ. У платформы нет объекта «издание»: это несколько листингов, которые
    покупатель должен найти и купить по одному. Этот эксперт исполняется НА ЕГО
    МАШИНЕ, где лежит его токен, и ставит состав целиком.

    СОСТАВ ЗАШИТ ЗДЕСЬ НАМЕРЕННО. Если бы список приходил параметром со страницы,
    страница могла бы попросить поставить что угодно. Эксперт ставит только то,
    что записано в нём самом и что человек прочитал в карточке издания.

    Действия:
      состояние — что уже стоит, а чего нет. Ничего не меняет
      поставить — доставить недостающее (нужно подтверждено="да")
    """
    import json, pathlib, urllib.request

    def отдать(д):
        return json.dumps(д, ensure_ascii=False)

    СОСТАВ = [
        {"вид": "приложение", "имя": "Разработка на Extella",
         "listing_id": "880d12e4-f082-486e-b92a-57e4eb09866d",
         "зачем": "единый вход: канон, порядок стройки, путь до магазина"},
        {"вид": "репозиторий", "имя": "Стандарты и гейты локально",
         "репо": "AnvarBakiyev/extella-agent-standards", "тег": "v0.2.0",
         "куда": "extella/standards",
         "зачем": "проверки идут без сети, прямо на машине"},
    ]

    def токен():
        п = pathlib.Path.home() / ".extella" / "api_token.txt"
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

    def зов(путь, тело=None):
        д = json.dumps(тело).encode() if тело is not None else None
        з = {"X-Extella-Token": т}
        if д:
            з["Content-Type"] = "application/json"
        r = urllib.request.Request("https://os.extella.ai" + путь, data=д, headers=з,
                                   method="POST" if д else "GET")
        try:
            with urllib.request.urlopen(r, timeout=180) as о:
                return о.status, о.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:200]
        except Exception as e:
            return 0, str(e)[:160]

    # Что уже куплено — читаем состояние, а не помним о прошлых установках.
    куплено = set()
    код, тело = зов("/api/my-purchases")
    if код == 200:
        куплено = {п.get("listing_id") for п in json.loads(тело).get("purchases", [])}

    дом = pathlib.Path.home()
    части = []
    for ч in СОСТАВ:
        если_стоит = False
        где = ""
        if ч["вид"] == "приложение":
            если_стоит = ч["listing_id"] in куплено
        else:
            путь = дом / ч["куда"]
            если_стоит = путь.exists() and any(путь.rglob("*"))
            где = str(путь)
        части.append({**{k: v for k, v in ч.items() if k != "listing_id"},
                      "стоит": если_стоит, "где": где})

    если_ставить = подтверждено == "да" and действие == "поставить"
    поставлено = []
    if если_ставить:
        for ч, вид in zip(СОСТАВ, части):
            if вид["стоит"]:
                continue
            if ч["вид"] == "приложение":
                # У листинга берём последнюю версию и покупаем её.
                код, тело = зов(f"/api/listing/{ч['listing_id']}")
                if код != 200:
                    вид["итог"] = f"листинг недоступен ({код})"
                    continue
                версии = json.loads(тело).get("versions", [])
                if not версии:
                    вид["итог"] = "у листинга нет версий"
                    continue
                код, тело = зов(f"/api/purchase/{версии[0]['id']}", тело={})
                вид["итог"] = "поставлено" if код == 200 else f"не поставилось ({код})"
                вид["стоит"] = код == 200
            else:
                адрес = (f"https://codeload.github.com/{ч['репо']}"
                         f"/tar.gz/refs/tags/{ч['тег']}")
                try:
                    import io, os, tarfile
                    with urllib.request.urlopen(адрес, timeout=180) as о:
                        данные = о.read()
                    корень = (дом / ч["куда"]).resolve()
                    корень.mkdir(parents=True, exist_ok=True)
                    with tarfile.open(fileobj=io.BytesIO(данные)) as t:
                        for член in t.getmembers():
                            цель = (корень / член.name).resolve()
                            if not str(цель).startswith(str(корень) + os.sep):
                                raise ValueError(f"архив пишет наружу: {член.name}")
                            if член.issym() or член.islnk():
                                raise ValueError(f"ссылка в архиве: {член.name}")
                        t.extractall(корень)
                    вид["итог"] = "поставлено"
                    вид["стоит"] = True
                except Exception as e:
                    вид["итог"] = f"не поставилось: {str(e)[:120]}"
            if вид["стоит"]:
                поставлено.append(вид["имя"])

    return отдать({
        "издание": "Издание для сборщика",
        "части": части,
        "готово": all(ч["стоит"] for ч in части),
        "поставлено_сейчас": поставлено,
        "подсказка": "" if если_ставить else
                     "ничего не менял: это состояние. Кнопка ставит недостающее",
    })
