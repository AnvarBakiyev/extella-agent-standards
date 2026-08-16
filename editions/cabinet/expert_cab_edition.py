$extens("include.py")
def cab_edition(действие="состояние", подтверждено="нет"):
    """Тихий кабинет: инструменты, работающие без интернета и без аккаунта.

    ЗАЧЕМ. У платформы нет объекта «издание»: есть листинги, которые покупаются по
    одному, и приложения, которые надо где-то взять и чем-то поднять. Этот эксперт
    исполняется НА МАШИНЕ ПОКУПАТЕЛЯ и делает обе половины: ставит окна из магазина
    и раскладывает сами приложения с их официальных релизов.

    СОСТАВ ЗАШИТ ЗДЕСЬ НАМЕРЕННО. Приходи он параметром со страницы — страница могла бы
    попросить скачать что угодно и запустить на этой машине. Человек получает ровно то,
    что прочитал в карточке.

    Действия:
      состояние — что уже стоит, а чего нет. Ничего не меняет
      поставить — доставить недостающее (нужно подтверждено="да")
    """
    import json, os, pathlib, shutil, subprocess, tarfile, urllib.request, zipfile, io

    def отдать(д):
        return json.dumps(д, ensure_ascii=False)

    ДОМ = pathlib.Path.home()
    КАБИНЕТ = ДОМ / "extella-cabinet"
    АГЕНТЫ = ДОМ / "Library" / "LaunchAgents"

    # Каждое приложение: окно в магазине + сама программа на диске + порт, на котором
    # она поднимается. Версии прибиты гвоздями: «последняя» однажды приедет другой.
    СОСТАВ = [
        {"имя": "Доска", "папка": "board", "порт": 34785,
         "listing_id": "e8c87ee0-8faa-47ca-8d50-7624c8c2d26b",
         "проба": "favicon-32x32.png",
         "источник": None,          # готового релиза нет — собирается из исходников
         "зачем": "набросать схему от руки, пока говоришь"},
        {"имя": "Читалка", "папка": "reader", "порт": 34787,
         "listing_id": "9136f984-8a6d-4e47-a494-e75dfbefe65b",
         "проба": "web/viewer.html",
         "источник": {"вид": "zip", "тег": "v6.2.108",
                      "адрес": "https://github.com/mozilla/pdf.js/releases/download/"
                               "v6.2.108/pdfjs-6.2.108-dist.zip",
                      "лишнее": []},
         "зачем": "читать договоры, не загружая их на чужой сервер"},
    ]

    def токен():
        п = ДОМ / ".extella" / "api_token.txt"
        if п.exists() and п.read_text().strip():
            return п.read_text().strip()
        к = ДОМ / "extella_wizard" / "app" / "config.json"
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

    куплено = set()
    код, тело = зов("/api/my-purchases")
    if код == 200:
        куплено = {п.get("listing_id") for п in json.loads(тело).get("purchases", [])}

    def агент_имя(папка):
        return f"ai.extella.cabinet.{папка}"

    def служба_жива(папка):
        итог = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        return агент_имя(папка) in итог.stdout


    # --- наши доводки поверх чужих программ ---------------------------------
    # Обе правки помечены и снимаются: чужой код мы не переписываем молча.
    ПРОБА_НАЧАЛО = "<!-- extella-проба: начало"
    ПРОБА = (ПРОБА_НАЧАЛО + " -->\n"
             "<script>(function(){var ок=false,причина=\"\";"
             "try{localStorage.setItem(\"__extella_проба\",\"1\");"
             "localStorage.removeItem(\"__extella_проба\");ок=true;}"
             "catch(e){причина=String((e&&e.name)||e).slice(0,60);}"
             "try{if(window.parent&&window.parent!==window){"
             "window.parent.postMessage({type:\"extella_проба\",ок:ок,"
             "причина:причина},\"*\");}}catch(e){}})();</script>\n"
             "<!-- extella-проба: конец -->\n")

    def вставить_пробу(файл):
        """Окно ОС узнаёт о закрытом хранилище только от самой страницы приложения:
        снаружи чужое происхождение не прочитать, а отдельный файл-разведчик не
        доезжает — excalidraw ставит service worker на весь порт."""
        if not файл.exists():
            return "страницы приложения нет"
        т = файл.read_text(errors="ignore")
        if ПРОБА_НАЧАЛО in т:
            return "проба уже стоит"
        копия = файл.with_suffix(файл.suffix + ".до_пробы")
        if not копия.exists():
            shutil.copy2(файл, копия)
        м = т.lower().find("<head>")
        файл.write_text(т[:м + 6] + ПРОБА + т[м + 6:] if м >= 0 else ПРОБА + т)
        return "проба вставлена"

    # --- состояние ----------------------------------------------------------
    части = []
    for ч in СОСТАВ:
        путь = КАБИНЕТ / ч["папка"]
        программа = (путь / ч["проба"]).exists()
        части.append({
            "имя": ч["имя"], "зачем": ч["зачем"], "папка": str(путь),
            # Адрес нужен витрине, чтобы из неё можно было ОТКРЫТЬ приложение.
            # Без этого витрина только рапортует о галочках, а работать негде.
            "адрес": f"http://localhost:{ч['порт']}/",
            "окно_куплено": ч["listing_id"] in куплено,
            "программа_на_диске": программа,
            "служба_поднята": служба_жива(ч["папка"]) if программа else False,
            "стоит": программа and ч["listing_id"] in куплено,
            "готового_релиза_нет": ч["источник"] is None,
        })

    если_ставить = подтверждено == "да" and действие == "поставить"
    if если_ставить:
        КАБИНЕТ.mkdir(parents=True, exist_ok=True)
        АГЕНТЫ.mkdir(parents=True, exist_ok=True)

        for ч, вид in zip(СОСТАВ, части):
            шаги = []

            # 1. Окно из магазина.
            if not вид["окно_куплено"]:
                код, тело = зов(f"/api/listing/{ч['listing_id']}")
                версии = json.loads(тело).get("versions", []) if код == 200 else []
                if not версии:
                    шаги.append(f"окно недоступно ({код})")
                else:
                    код, _ = зов(f"/api/purchase/{версии[0]['id']}", тело={})
                    шаги.append("окно поставлено" if код == 200 else f"окно не встало ({код})")
                    вид["окно_куплено"] = код == 200

            # 2. Сама программа.
            if not вид["программа_на_диске"]:
                и = ч["источник"]
                if и is None:
                    # Честно: у этой программы нет готового релиза, её надо собрать.
                    # Молча пропустить — значит соврать зелёной галочкой.
                    шаги.append("нет готового релиза: программа собирается из исходников, "
                                "этот шаг издание пока не делает за вас")
                else:
                    цель = (КАБИНЕТ / ч["папка"]).resolve()
                    try:
                        with urllib.request.urlopen(и["адрес"], timeout=600) as о:
                            данные = о.read()
                        цель.mkdir(parents=True, exist_ok=True)
                        with zipfile.ZipFile(io.BytesIO(данные)) as z:
                            for член in z.namelist():
                                п = (цель / член).resolve()
                                if not str(п).startswith(str(цель) + os.sep):
                                    raise ValueError(f"архив пишет наружу: {член}")
                            z.extractall(цель)
                        for лишнее in и.get("лишнее", []):
                            shutil.rmtree(цель / лишнее, ignore_errors=True)
                        шаги.append(f"программа поставлена ({и['тег']})")
                        вид["программа_на_диске"] = (цель / ч["проба"]).exists()
                        шаги.append(вставить_пробу(цель / ч.get("вход", "index.html")))
                    except Exception as e:
                        шаги.append(f"программа не поставилась: {str(e)[:120]}")

            # 3. Служба: поднимается сама при входе, слушает только этот компьютер.
            if вид["программа_на_диске"] and not вид["служба_поднята"]:
                файл = АГЕНТЫ / f"{агент_имя(ч['папка'])}.plist"
                файл.write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>\n'
                    f'  <key>Label</key><string>{агент_имя(ч["папка"])}</string>\n'
                    '  <key>ProgramArguments</key><array>\n'
                    '    <string>/usr/bin/python3</string><string>-m</string>\n'
                    '    <string>http.server</string>\n'
                    f'    <string>{ч["порт"]}</string>\n'
                    '    <string>--bind</string><string>127.0.0.1</string>\n'
                    '    <string>--directory</string>\n'
                    f'    <string>{КАБИНЕТ / ч["папка"]}</string>\n'
                    '  </array>\n'
                    '  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>\n'
                    '</dict></plist>\n')
                кто = subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip()
                subprocess.run(["launchctl", "bootout", f"gui/{кто}/{агент_имя(ч['папка'])}"],
                               capture_output=True)
                subprocess.run(["launchctl", "bootstrap", f"gui/{кто}", str(файл)],
                               capture_output=True)
                вид["служба_поднята"] = служба_жива(ч["папка"])
                шаги.append("служба поднята" if вид["служба_поднята"] else "служба не поднялась")

            вид["стоит"] = вид["окно_куплено"] and вид["программа_на_диске"]
            if шаги:
                вид["итог"] = "; ".join(шаги)

    return отдать({
        "издание": "Тихий кабинет",
        "части": части,
        "готово": all(ч["стоит"] for ч in части),
        "подсказка": "" if если_ставить else
                     "ничего не менял: это состояние. Кнопка ставит недостающее",
    })
