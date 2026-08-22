# description: Найти концепт по смыслу для витрины «День первый»: возвращает заголовок и начало найденной записи знания плюс сам запрос. Показывает, что поиск идёт по смыслу, а не по совпадению слов.
def journey_concept(query: str = "как навести порядок в файлах") -> str:
    # Концепт объясняется не определением, а показом: человек видит СВОЙ
    # запрос обычными словами и найденную запись, где этих слов нет. Это и
    # есть разница между поиском по смыслу и поиском по совпадению.
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

    ток = токен()
    if not ток:
        return json.dumps({"status": "error",
                           "message": "нет доступа к Extella на этом устройстве"},
                          ensure_ascii=False)

    тело = json.dumps({"query": query, "limit": 3}).encode()
    з = urllib.request.Request("https://api.extella.ai/api/concept/search", data=тело,
                               headers={"Content-Type": "application/json",
                                        "X-Auth-Token": ток, "X-Profile-Id": "default",
                                        "X-Agent-Id": "agent_extella_default"},
                               method="POST")
    try:
        with urllib.request.urlopen(з, timeout=60) as о:
            д = json.loads(о.read().decode())
    except Exception as e:
        return json.dumps({"status": "error",
                           "message": "поиск знаний не ответил: " + str(e)[:120]},
                          ensure_ascii=False)

    найдено = д.get("results") or []
    if not найдено:
        return json.dumps({"status": "empty", "query": query,
                           "message": "в памяти этого аккаунта пока нет подходящих записей — "
                                      "их заводят по мере работы"}, ensure_ascii=False)

    первый = найдено[0]
    текст = str(первый.get("concept_text") or "").strip()
    # Заголовок — первая содержательная строка записи, не весь текст.
    строки = [с.strip() for с in текст.split("\n") if с.strip()]
    заголовок = (строки[0] if строки else "запись знания")[:90]
    начало = " ".join(строки[1:4])[:220] if len(строки) > 1 else текст[:220]

    # Совпало ли хоть одно слово запроса — этим и показываем поиск по смыслу.
    слова = [с.lower() for с in query.split() if len(с) > 4]
    буквально = sum(1 for с in слова if с in текст.lower())

    return json.dumps({"status": "success", "query": query, "found": len(найдено),
                       "title": заголовок, "snippet": начало,
                       "literal_matches": буквально, "words_asked": len(слова)},
                      ensure_ascii=False)
