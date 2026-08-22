# description: Нарисовать карту папки в приложении «Доска схем» на этом устройстве: заголовок и плитки категорий с числами. Пишет только свои элементы с меткой источника, чужое и нарисованное человеком не трогает; повтор заменяет свой прошлый рисунок.
def journey_board_scheme(folder: str = "~/Downloads") -> str:
    # Одно приложение зовёт другое: эксперт пишет в локальное хранилище Доски
    # схем (порт 34786). Два правила соседства — те же, что у tools/на_доску.py:
    # пишем только своё с меткой ext_<источник>_, повтор заменяет свой прошлый
    # рисунок; чужие элементы переносятся как есть. Проверено 22.08.2026:
    # 481 чужой элемент цел при записи и стирании.
    import json, os, time, urllib.request

    ГРУППЫ = {
        "Документы": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages"},
        "Таблицы": {".xls", ".xlsx", ".csv", ".numbers"},
        "Картинки": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".heic"},
        "Видео": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
        "Аудио": {".mp3", ".wav", ".m4a", ".aac", ".flac"},
        "Код": {".py", ".js", ".mjs", ".html", ".css", ".json", ".sh", ".ts"},
        "Архивы": {".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".iso"},
    }
    МЕТКА = "ext_denперв_"
    АДРЕС = "http://127.0.0.1:34786/_extella_storage"

    путь = os.path.expanduser(folder)
    if not os.path.isdir(путь):
        return json.dumps({"status": "error", "message": "папки нет: " + folder},
                          ensure_ascii=False)

    счёт = {}
    for имя in os.listdir(путь):
        полный = os.path.join(путь, имя)
        if имя.startswith(".") or not os.path.isfile(полный):
            continue
        расш = os.path.splitext(имя)[1].lower()
        группа = next((г for г, н in ГРУППЫ.items() if расш in н), "Прочее")
        счёт[группа] = счёт.get(группа, 0) + 1

    def хранилище(тело=None):
        if тело is None:
            with urllib.request.urlopen(АДРЕС, timeout=15) as о:
                return json.loads(о.read().decode())
        з = urllib.request.Request(АДРЕС, data=json.dumps(тело, ensure_ascii=False).encode(),
                                   headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(з, timeout=25) as о:
            return json.loads(о.read().decode())

    try:
        было = хранилище()
    except Exception as e:
        return json.dumps({"status": "error",
                           "message": "Доска схем не отвечает на этом устройстве: "
                           + str(e)[:100] + ". Поставь её из магазина и открой один раз."},
                          ensure_ascii=False)

    эл = json.loads(было.get("excalidraw") or "[]")
    чужие = [e for e in эл if not str(e.get("id", "")).startswith(МЕТКА)]
    живые = [e for e in чужие if not e.get("isDeleted")]
    низ = max((e.get("y", 0) + (e.get("height") or 0) for e in живые), default=0)
    y0 = низ + 240 if живые else 80
    t = int(time.time())

    def элемент(идент, **поля):
        база = {"id": МЕТКА + идент, "angle": 0, "strokeColor": "#C57E33",
                "backgroundColor": "transparent", "fillStyle": "solid",
                "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
                "opacity": 100, "seed": t + len(поля), "version": 1,
                "versionNonce": t, "isDeleted": False, "groupIds": [],
                "boundElements": [], "updated": t, "link": None, "locked": False}
        база.update(поля)
        return база

    def текст(идент, x, y, слова, размер=16):
        return элемент(идент, type="text", x=x, y=y, width=len(слова) * размер * .62,
                       height=размер * 1.4, roundness=None, text=слова,
                       fontSize=размер, fontFamily=1, textAlign="left",
                       verticalAlign="top", baseline=размер,
                       containerId=None, originalText=слова, lineHeight=1.25)

    мои = [текст("title", 60, y0, "Загрузки — карта от " + time.strftime("%d.%m"), 22)]
    x = 60
    for группа, n in sorted(счёт.items(), key=lambda п: -п[1]):
        мои.append(элемент("box_" + группа, type="rectangle", x=x, y=y0 + 48,
                           width=150, height=72, roundness={"type": 3}))
        мои.append(текст("name_" + группа, x + 12, y0 + 60, группа, 14))
        мои.append(текст("num_" + группа, x + 12, y0 + 84, str(n) + " шт", 18))
        x += 168

    хранилище({"ключ": "excalidraw",
               "значение": json.dumps(чужие + мои, ensure_ascii=False)})
    return json.dumps({"status": "success", "drawn": len(мои),
                       "groups": len(счёт), "kept": len(чужие),
                       "message": "карта легла на Доску схем — открой её заново"},
                      ensure_ascii=False)
