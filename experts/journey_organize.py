# description: Раскладка папки для витрины «День первый»: план без изменений, исполнение только с подтверждением человека и с файлом отката, возврат как было. После раскладки открывает папку в Finder.
def journey_organize(folder: str = "~/Downloads", action: str = "plan",
                     confirm: str = "") -> str:
    # Три действия одного эксперта, у них общий словарь групп со сканером.
    #   plan    — что будет сделано; ничего не трогает
    #   execute — раскладывает; БЕЗ подтверждения отказывает, называя правило
    #   undo    — возвращает всё по файлу отката
    # Отказ без подтверждения — не защита от дурака, а сам показ: витрина
    # демонстрирует правило в действии, и правило обязано быть настоящим.
    import json, os, shutil, subprocess

    ГРУППЫ = {
        "Документы": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages"},
        "Таблицы": {".xls", ".xlsx", ".csv", ".numbers"},
        "Картинки": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".heic"},
        "Видео": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
        "Аудио": {".mp3", ".wav", ".m4a", ".aac", ".flac"},
        "Код": {".py", ".js", ".mjs", ".html", ".css", ".json", ".sh", ".ts"},
        "Архивы": {".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".iso"},
    }
    ПРАВИЛО = ("файлы не покидают свою папку никогда — раскладка только по "
               "подпапкам внутри неё; ничего не перемещать без подтверждения "
               "человека; у каждой раскладки обязан быть откат")

    путь = os.path.expanduser(folder)
    откат = os.path.join(путь, ".journey_undo.json")
    if not os.path.isdir(путь):
        return json.dumps({"status": "error", "message": "папки нет: " + folder},
                          ensure_ascii=False)

    def файлы():
        for имя in sorted(os.listdir(путь)):
            полный = os.path.join(путь, имя)
            if имя.startswith(".") or not os.path.isfile(полный):
                continue
            расш = os.path.splitext(имя)[1].lower()
            группа = next((г for г, н in ГРУППЫ.items() if расш in н), "Прочее")
            yield имя, полный, группа

    if action == "plan":
        счёт = {}
        for _, _, группа in файлы():
            счёт[группа] = счёт.get(группа, 0) + 1
        return json.dumps({"status": "success", "action": "plan",
                           "would_move": sum(счёт.values()),
                           "folders": dict(sorted(счёт.items(), key=lambda x: -x[1])),
                           "rule": ПРАВИЛО}, ensure_ascii=False)

    if action == "execute":
        if confirm != "да-перемещай":
            # Настоящий отказ, не декорация: без слова подтверждения эксперт
            # не двигает ничего и называет правило, которое его остановило.
            return json.dumps({"status": "refused", "rule": ПРАВИЛО,
                               "message": "раскладка не выполнена: нет подтверждения человека"},
                              ensure_ascii=False)
        сделано, журнал = 0, []
        for имя, полный, группа in list(файлы()):
            куда_папка = os.path.join(путь, группа)
            os.makedirs(куда_папка, exist_ok=True)
            куда = os.path.join(куда_папка, имя)
            if os.path.exists(куда):
                корень, расш = os.path.splitext(имя)
                н = 1
                while os.path.exists(куда):
                    куда = os.path.join(куда_папка, f"{корень}_{н}{расш}")
                    н += 1
            # Слово владельца 22.08.2026: из папки наружу — никогда. Проверка
            # структурная, а не на доверии: назначение обязано лежать внутри
            # исходной папки, иначе весь запуск останавливается до первого сдвига.
            if not os.path.realpath(куда).startswith(os.path.realpath(путь) + os.sep):
                return json.dumps({"status": "error",
                                   "message": "назначение вышло за пределы папки — раскладка остановлена"},
                                  ensure_ascii=False)
            shutil.move(полный, куда)
            журнал.append({"from": полный, "to": куда})
            сделано += 1
        with open(откат, "w", encoding="utf-8") as f:
            json.dump(журнал, f, ensure_ascii=False)
        # Показ результата там, где человек живёт, — в Finder, а не в нашем окне.
        try:
            subprocess.run(["/usr/bin/open", путь], timeout=10)
        except Exception:
            pass
        return json.dumps({"status": "success", "action": "execute",
                           "moved": сделано, "undo": откат}, ensure_ascii=False)

    if action == "undo":
        if not os.path.isfile(откат):
            return json.dumps({"status": "error",
                               "message": "файла отката нет — возвращать нечего"},
                              ensure_ascii=False)
        with open(откат, "r", encoding="utf-8") as f:
            журнал = json.load(f)
        назад = 0
        for з in reversed(журнал):
            if os.path.isfile(з["to"]):
                shutil.move(з["to"], з["from"])
                назад += 1
        os.remove(откат)
        for имя in os.listdir(путь):
            п = os.path.join(путь, имя)
            if os.path.isdir(п) and not os.listdir(п):
                os.rmdir(п)
        return json.dumps({"status": "success", "action": "undo",
                           "restored": назад}, ensure_ascii=False)

    return json.dumps({"status": "error", "message": "неизвестное действие: " + action},
                      ensure_ascii=False)
