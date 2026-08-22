# description: Осмотр папки для витрины «День первый»: сводка по категориям, объём и примеры имён. Только чтение; ответ всегда маленький — большой список в потолок транспорта не упирается.
def journey_scan(folder: str = "~/Downloads") -> str:
    # Сводка, а не список: замер 22.08.2026 — полный список Загрузок (1969
    # файлов) не пролезает в транспорт эксперта (~200 КБ, H40). Поэтому наружу
    # уходят только числа и по три имени-примера на категорию.
    import json, os

    ГРУППЫ = {
        "Документы": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages"},
        "Таблицы": {".xls", ".xlsx", ".csv", ".numbers"},
        "Картинки": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".heic"},
        "Видео": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
        "Аудио": {".mp3", ".wav", ".m4a", ".aac", ".flac"},
        "Код": {".py", ".js", ".mjs", ".html", ".css", ".json", ".sh", ".ts"},
        "Архивы": {".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".iso"},
    }

    путь = os.path.expanduser(folder)
    if not os.path.isdir(путь):
        return json.dumps({"status": "error",
                           "message": "папки нет: " + folder}, ensure_ascii=False)

    счёт, примеры, объём, всего = {}, {}, 0, 0
    for имя in os.listdir(путь):
        полный = os.path.join(путь, имя)
        # Скрытые и служебные не считаются: они не беспорядок, а устройство системы.
        if имя.startswith(".") or not os.path.isfile(полный):
            continue
        всего += 1
        try:
            объём += os.path.getsize(полный)
        except OSError:
            pass
        расш = os.path.splitext(имя)[1].lower()
        группа = next((г for г, н in ГРУППЫ.items() if расш in н), "Прочее")
        счёт[группа] = счёт.get(группа, 0) + 1
        if len(примеры.setdefault(группа, [])) < 3:
            примеры[группа].append(имя[:60])

    return json.dumps({
        "status": "success", "folder": folder, "total": всего,
        "size_mb": round(объём / 1048576, 1),
        "categories": dict(sorted(счёт.items(), key=lambda x: -x[1])),
        "examples": примеры,
    }, ensure_ascii=False)
