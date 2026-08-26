# description: Модуль «распознавание текста»: достаёт текст из картинки или PDF на этом компьютере. У PDF сначала берёт текстовый слой, скан распознаёт. Проверяет, что нужный язык установлен, и отказывается вместо выдачи мусора. Ничего не отправляет наружу и ничего не ставит без явного разрешения.
def toolkit_ocr_read(path: str = "", lang: str = "eng", install: str = "",
                     max_pages: str = "3") -> str:
    # ПРАВИЛО ЭТОГО МОДУЛЯ — ДВА.
    # 1. Картинка никуда не уходит: распознаём программой на этой машине.
    # 2. Ничего не ставим без явного слова человека. install="да-ставь" — это
    #    его решение, а не наше удобство.
    # И главное: если нужного ЯЗЫКА нет, мы отказываемся. Tesseract без языка
    # не падает — он выдаёт правдоподобный мусор, и это худший исход: продукт
    # выглядит работающим, а текст неверный. Замер 26.08.2026: на машине стоял
    # только eng, русского не было.
    import json, os, shutil, subprocess, tempfile

    def отказ(сообщение, **ещё):
        д = {"status": "error", "message": сообщение}
        д.update(ещё)
        return json.dumps(д, ensure_ascii=False)

    файл = os.path.expanduser((path or "").strip())
    if not файл:
        return отказ("не сказано, какой файл читать")
    if not os.path.isfile(файл):
        return отказ("файла нет по этому пути: " + os.path.basename(файл))

    язык = (lang or "eng").strip() or "eng"
    расш = os.path.splitext(файл)[1].lower()
    КАРТИНКИ = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
    try:
        страниц = max(1, min(20, int(str(max_pages).strip() or 3)))
    except ValueError:
        страниц = 3

    def найти(имя):
        # PATH у службы беднее, чем у человека в терминале: ищем и по обычным
        # местам, иначе «программа не установлена» при установленной программе.
        п = shutil.which(имя)
        if п:
            return п
        for корень in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):
            п = os.path.join(корень, имя)
            if os.path.isfile(п) and os.access(п, os.X_OK):
                return п
        return ""

    def выполнить(команда, таймаут=180):
        и = subprocess.run(команда, capture_output=True, text=True, timeout=таймаут)
        return и.returncode, (и.stdout or ""), (и.stderr or "")

    # ── PDF: сначала текстовый слой. Распознавать то, что уже написано, —
    #    значит потерять точность на ровном месте.
    if расш == ".pdf":
        pdftotext = найти("pdftotext")
        if pdftotext:
            код, вывод, _ = выполнить([pdftotext, "-l", str(страниц), файл, "-"])
            if код == 0 and len(вывод.strip()) > 40:
                return json.dumps({"status": "success", "file": os.path.basename(файл),
                                   "read_by": "текстовый слой PDF", "where": "на этом компьютере",
                                   "lang": "не потребовался", "left_device": False,
                                   "chars": len(вывод.strip()), "installed_anything": False,
                                   "text": вывод.strip()[:60000]}, ensure_ascii=False)
        # текстового слоя нет — это скан, нужна растеризация и распознавание
    elif расш not in КАРТИНКИ:
        return отказ("формат " + (расш or "без расширения") + " не читаю",
                     что_умею=list(КАРТИНКИ) + [".pdf"])

    tesseract = найти("tesseract")
    поставили = []

    if not tesseract:
        if str(install).strip().lower() != "да-ставь":
            return отказ("Распознавать нечем: программа tesseract на этой машине не "
                         "установлена. Я её сам не ставлю — это твоя машина. Разреши "
                         "явно: повтори с install=\"да-ставь\", и я поставлю её через "
                         "Homebrew. Или поставь сам: brew install tesseract",
                         нужно_разрешение=True, что_поставлю=["tesseract"])
        brew = найти("brew")
        if not brew:
            return отказ("нет Homebrew — ставить нечем. Поставь Homebrew, потом повтори.")
        код, _, ошибка = выполнить([brew, "install", "tesseract"], таймаут=900)
        if код != 0:
            return отказ("не удалось поставить tesseract: " + ошибка.strip()[-160:])
        поставили.append("tesseract")
        tesseract = найти("tesseract")
        if not tesseract:
            return отказ("tesseract поставился, но не нашёлся в путях — нужен перезапуск службы")

    # ── язык: без него распознавание выдаёт мусор, а не отказ
    код, вывод, ошибка = выполнить([tesseract, "--list-langs"], таймаут=60)
    языки = [с.strip() for с in (вывод + ошибка).splitlines()[1:] if с.strip()]
    if язык not in языки:
        if str(install).strip().lower() == "да-ставь" and найти("brew"):
            код2, _, ош2 = выполнить([найти("brew"), "install", "tesseract-lang"], таймаут=900)
            if код2 == 0:
                поставили.append("tesseract-lang")
                _, вывод, ошибка = выполнить([tesseract, "--list-langs"], таймаут=60)
                языки = [с.strip() for с in (вывод + ошибка).splitlines()[1:] if с.strip()]
        if язык not in языки:
            return отказ("Языка «" + язык + "» у распознавателя нет, а без него он выдаёт "
                         "не отказ, а правдоподобный мусор — поэтому я останавливаюсь. "
                         "Поставь языки: brew install tesseract-lang — или разреши мне "
                         "это сделать: install=\"да-ставь\".",
                         есть_языки=языки[:12], нужно_разрешение=True,
                         что_поставлю=["tesseract-lang"], поставлено=поставили)

    with tempfile.TemporaryDirectory() as вр:
        цели = []
        if расш == ".pdf":
            pdftoppm = найти("pdftoppm")
            if not pdftoppm:
                return отказ("PDF оказался сканом, а растеризовать его нечем: нет pdftoppm. "
                             "Поставь poppler: brew install poppler", поставлено=поставили)
            основа = os.path.join(вр, "стр")
            код, _, ошибка = выполнить([pdftoppm, "-r", "200", "-l", str(страниц),
                                        "-png", файл, основа], таймаут=300)
            if код != 0:
                return отказ("не удалось разложить PDF на страницы: " + ошибка.strip()[-140:])
            цели = sorted(os.path.join(вр, и) for и in os.listdir(вр) if и.endswith(".png"))
            if not цели:
                return отказ("из PDF не получилось ни одной страницы")
        else:
            цели = [файл]

        куски = []
        for стр in цели:
            код, вывод, ошибка = выполнить([tesseract, стр, "-", "-l", язык], таймаут=300)
            if код != 0:
                return отказ("распознавание не удалось: " + ошибка.strip()[-140:],
                             поставлено=поставили)
            куски.append(вывод.strip())

    текст = "\n\n".join(к for к in куски if к).strip()
    if not текст:
        return отказ("на изображении не нашлось текста", поставлено=поставили)

    return json.dumps({"status": "success", "file": os.path.basename(файл),
                       "read_by": "tesseract", "where": "на этом компьютере",
                       "lang": язык, "pages": len(цели), "left_device": False,
                       "chars": len(текст), "installed_anything": bool(поставили),
                       "installed": поставили, "text": текст[:60000]}, ensure_ascii=False)
