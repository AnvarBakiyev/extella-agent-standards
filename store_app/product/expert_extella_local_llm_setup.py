def extella_local_llm_product_setup(action: str = "preflight") -> str:
    """Локальная модель для Extella: LM Studio + Qwen3.5 одной кнопкой.

    Шесть безмодельных этапов по канону установщика мостов: каждый ответ несёт
    версию, каждый отказ называет следующий шаг, ни один этап не тратит план.
    Скачивание модели — единственный долгий этап — идёт асинхронно: шаг model
    запускает загрузку в фоне и на повторных вызовах отдаёт прогресс, поэтому
    ни один вызов не упирается в отсечку платформы (~51 с, замер 18.08.2026).

    Разделение, ради которого продукт существует: разработка агентов требует
    сильной модели (мосты Claude/Codex), а РАБОТА агентов — тысячи дешёвых
    вызовов — уезжает на локальную модель: ноль за токен, данные не покидают
    машину. Конфиг листенера уже умеет llm_base_url/llm_model, платформа не
    меняется вовсе.
    """
    import json, os, platform, shutil, subprocess, urllib.request

    SETUP_VERSION = "3.2.16"
    HOME = os.path.expanduser("~")
    APP = "/Applications/LM Studio.app"
    BUNDLED_LMS = APP + "/Contents/Resources/app/.webpack/lms"
    LMS = os.path.join(HOME, ".lmstudio", "bin", "lms")
    PROFILE = os.path.join(HOME, ".lmstudio")
    MODELS_DIR = os.path.join(PROFILE, "models")
    WIZARD_CONFIG = os.path.join(HOME, "extella_wizard", "app", "config.json")
    SERVER = "http://127.0.0.1:1234"
    DOWNLOAD_LOG = os.path.join(PROFILE, ".extella_model_download.log")
    DOWNLOAD_PID = os.path.join(PROFILE, ".extella_model_download.pid")

    # Лестница по памяти. Замер 19.08.2026 на живом каталоге LM Studio:
    # интерактивный поиск отдаёт qwen/qwen3.5-9b и qwen/qwen3.5-35b-a3b.
    # 35B-A3B — MoE с 3B активных: быстрая при ~20 ГБ веса, поэтому нижняя
    # граница для неё — 24 ГБ. Ниже 12 ГБ честный отказ лучше зависшего Мака.
    LADDER = [(24, "qwen/qwen3.5-35b-a3b", 22), (12, "qwen/qwen3.5-9b", 7)]

    def result(status, code, message, **extra):
        payload = {"status": status, "code": code, "message": message,
                   "step": action, "setup_version": SETUP_VERSION,
                   "model_called": False, "agent_called": False, "paid": False}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)

    def run(args, timeout=120, env_path=True):
        env = dict(os.environ)
        if env_path:
            env["PATH"] = ":".join([os.path.join(HOME, ".lmstudio", "bin"),
                                    "/opt/homebrew/bin", "/usr/local/bin",
                                    "/usr/bin", "/bin", env.get("PATH", "")])
        try:
            return subprocess.run(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  timeout=timeout, shell=False, env=env)
        except Exception:
            return None

    def memory_gb():
        probe = run(["/usr/sbin/sysctl", "-n", "hw.memsize"], timeout=10)
        try:
            return int((probe.stdout or "0").strip()) // (1024 ** 3)
        except Exception:
            return 0

    def free_disk_gb():
        try:
            return shutil.disk_usage(HOME).free // (1024 ** 3)
        except Exception:
            return 0

    def pick_model():
        """Ступень выбирается по памяти И по свободному диску: замер 19.08.2026 —
        загрузка 35B умерла на живой машине с 1 ГБ свободного места, потому что
        preflight смотрел только память. Запас 6 ГБ — чтобы не добить диск в ноль."""
        gb = memory_gb()
        disk = free_disk_gb()
        for minimum, name, size_gb in LADDER:
            if gb >= minimum and disk >= size_gb + 6:
                return gb, name, size_gb
        return gb, "", 0

    def server_models():
        try:
            with urllib.request.urlopen(SERVER + "/v1/models", timeout=8) as r:
                return [str(m.get("id", "")) for m in
                        json.loads(r.read(65536).decode()).get("data", [])]
        except Exception:
            return None

    def model_on_disk(name):
        # Модель считается скачанной, когда lms ls её называет: частично
        # скачанные файлы в списке не появляются, поэтому чтение честное.
        listed = run([LMS, "ls"], timeout=30)
        short = name.split("/", 1)[-1]
        return bool(listed and listed.returncode == 0 and short in (listed.stdout or ""))

    def downloaded_bytes():
        total = 0
        for root, _dirs, files in os.walk(MODELS_DIR):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        return total

    def download_running():
        try:
            with open(DOWNLOAD_PID, "r", encoding="utf-8") as s:
                pid = int(s.read().strip())
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    if action == "preflight":
        if platform.system() != "Darwin":
            return result("error", "unsupported_os",
                          "Пока поддерживается только macOS.")
        gb, model, size = pick_model()
        if not model:
            disk = free_disk_gb()
            if gb >= LADDER[-1][0] and disk < LADDER[-1][2] + 6:
                return result("error", "not_enough_disk",
                              "Памяти достаточно (" + str(gb) + " ГБ), но на диске "
                              "свободно " + str(disk) + " ГБ, а младшей модели нужно " +
                              str(LADDER[-1][2] + 6) + ". Освободите место и нажмите "
                              "кнопку снова.", memory_gb=gb, free_disk_gb=disk)
            return result("error", "not_enough_memory",
                          "На этом компьютере " + str(gb) + " ГБ памяти — локальной "
                          "модели нужно от 12 ГБ. Используйте мосты Claude или Codex: "
                          "они работают без локальной модели.", memory_gb=gb)
        return result("success", "preflight_ok",
                      "Компьютер подходит: " + str(gb) + " ГБ памяти, модель " +
                      model + " (~" + str(size) + " ГБ на диске).",
                      memory_gb=gb, model=model, download_gb=size,
                      app_installed=os.path.isdir(APP))

    if action == "install":
        # Первый запуск приложения обязателен: замер 19.08.2026 — bootstrap
        # отказывается работать, пока приложение ни разу не запускалось.
        # Установка через brew только при полном отсутствии приложения.
        if not os.path.isdir(APP):
            brew = shutil.which("brew") or "/opt/homebrew/bin/brew"
            if not os.path.isfile(brew):
                return result("error", "lmstudio_not_installed",
                              "LM Studio не установлена, а Homebrew нет. Скачайте "
                              "приложение с lmstudio.ai и повторите.")
            installed = run([brew, "install", "--cask", "lm-studio"], timeout=900)
            if not installed or installed.returncode != 0:
                return result("error", "lmstudio_install_failed",
                              "Не удалось установить LM Studio: " +
                              ((installed.stdout or "").strip()[-160:] if installed else "нет ответа"))
        if not os.path.isdir(PROFILE):
            run(["/usr/bin/open", "-a", "LM Studio"], timeout=30)
            import time
            for _ in range(45):
                if os.path.isdir(PROFILE):
                    break
                time.sleep(2)
            if not os.path.isdir(PROFILE):
                return result("error", "first_run_incomplete",
                              "LM Studio открыта, но профиль ещё не создан. "
                              "Подождите несколько секунд и нажмите кнопку снова.")
        if not os.path.isfile(LMS):
            boot = run([BUNDLED_LMS, "bootstrap"], timeout=120)
            if not os.path.isfile(LMS):
                return result("error", "lms_bootstrap_failed",
                              "Не удалось подключить командную строку LM Studio: " +
                              ((boot.stdout or "").strip()[-160:] if boot else "нет ответа"))
        return result("success", "install_ok",
                      "LM Studio готова, командная строка подключена.")

    if action == "model":
        gb, model, size = pick_model()
        if not model:
            return result("error", "not_enough_memory",
                          "Памяти меньше 12 ГБ — модель ставить некуда.")
        if model_on_disk(model):
            for stale in (DOWNLOAD_PID, os.path.join(PROFILE, ".extella_model_attempts")):
                try:
                    os.remove(stale)
                except Exception:
                    pass
            return result("success", "model_ready",
                          "Модель " + model + " скачана.",
                          model=model, finished=True)
        if download_running():
            done = downloaded_bytes() / (1024 ** 3)
            return result("success", "model_downloading",
                          "Скачивается: " + ("%.1f" % done) + " из ~" + str(size) + " ГБ.",
                          model=model, finished=False,
                          progress_gb=round(done, 1), total_gb=size)
        # Умершая загрузка — не повод крутить вечный цикл: две неудачи подряд
        # означают настоящую причину (диск, сеть), и её надо назвать. Замер
        # 19.08.2026: загрузка умерла на 8-м гигабайте о полный диск, и без
        # счётчика шаг перезапускал бы её до бесконечности.
        attempts_path = os.path.join(PROFILE, ".extella_model_attempts")
        try:
            with open(attempts_path, "r", encoding="utf-8") as s_:
                attempts = int(s_.read().strip() or "0")
        except Exception:
            attempts = 0
        if attempts >= 2:
            tail = ""
            try:
                with open(DOWNLOAD_LOG, "rb") as s_:
                    s_.seek(max(0, os.path.getsize(DOWNLOAD_LOG) - 400))
                    tail = s_.read().decode("utf-8", "replace")[-200:]
            except Exception:
                pass
            try:
                os.remove(attempts_path)
            except Exception:
                pass
            return result("error", "model_download_failed",
                          "Скачивание дважды оборвалось. Свободно на диске: " +
                          str(free_disk_gb()) + " ГБ. Хвост журнала: " +
                          (tail.strip() or "пуст"), model=model)
        if free_disk_gb() < size + 6:
            return result("error", "not_enough_disk",
                          "Для " + model + " нужно " + str(size + 6) +
                          " ГБ свободного места, сейчас " + str(free_disk_gb()) +
                          ". Освободите диск и нажмите кнопку снова.", model=model)
        with open(attempts_path, "w", encoding="utf-8") as s_:
            s_.write(str(attempts + 1))
        # Запуск в фоне: сам вызов обязан вернуться быстро, иначе платформа
        # отложит его в задачу, дождаться которую страница не может.
        os.makedirs(MODELS_DIR, exist_ok=True)
        log = open(DOWNLOAD_LOG, "ab")
        child = subprocess.Popen(
            [LMS, "get", model, "--yes"],
            stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, PATH=os.path.join(HOME, ".lmstudio", "bin") +
                     ":/usr/bin:/bin"),
            start_new_session=True)
        with open(DOWNLOAD_PID, "w", encoding="utf-8") as s:
            s.write(str(child.pid))
        return result("success", "model_download_started",
                      "Скачивание " + model + " (~" + str(size) + " ГБ) запущено.",
                      model=model, finished=False, progress_gb=0.0, total_gb=size)

    if action == "server":
        models = server_models()
        if models is None:
            started = run([LMS, "server", "start"], timeout=90)
            models = server_models()
            if models is None:
                return result("error", "server_start_failed",
                              "Локальный сервер не поднялся: " +
                              ((started.stdout or "").strip()[-160:] if started else "нет ответа"))
        return result("success", "server_ok",
                      "Локальный сервер отвечает на " + SERVER + ".")

    if action == "configure":
        gb, model, _size = pick_model()
        if not os.path.isfile(WIZARD_CONFIG):
            return result("error", "wizard_config_missing",
                          "Конфиг листенера не найден. Откройте Extella на этом "
                          "компьютере один раз и повторите.")
        try:
            with open(WIZARD_CONFIG, "r", encoding="utf-8") as s:
                config = json.loads(s.read())
        except Exception:
            return result("error", "wizard_config_unreadable",
                          "Конфиг листенера не читается — правка отменена.")
        previous = {k: config.get(k) for k in ("llm_base_url", "llm_model")}
        config["llm_base_url"] = SERVER + "/v1"
        config["llm_model"] = model.split("/", 1)[-1]
        # Атомарно и с резервной копией: канон onboarding, та же механика.
        import tempfile, time as _t
        backup = WIZARD_CONFIG + ".bak_" + _t.strftime("%Y%m%dT%H%M%S")
        shutil.copy2(WIZARD_CONFIG, backup)
        fd, temporary = tempfile.mkstemp(dir=os.path.dirname(WIZARD_CONFIG),
                                         prefix=".config.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as s:
                s.write(json.dumps(config, ensure_ascii=False, indent=2))
            os.replace(temporary, WIZARD_CONFIG)
        except Exception:
            try:
                os.unlink(temporary)
            except Exception:
                pass
            return result("error", "wizard_config_write_failed",
                          "Не удалось записать конфиг; резервная копия цела: " + backup)
        return result("success", "configured",
                      "Листенер переключён на локальную модель.",
                      llm_base_url=config["llm_base_url"],
                      llm_model=config["llm_model"],
                      previous=previous, backup=os.path.basename(backup))

    if action in ("verify", "status"):
        gb, model, _size = pick_model()
        checks = {
            "app": os.path.isdir(APP),
            "cli": os.path.isfile(LMS),
            "model": bool(model) and model_on_disk(model),
            "server": server_models() is not None,
            "config": False,
        }
        try:
            with open(WIZARD_CONFIG, "r", encoding="utf-8") as s:
                config = json.loads(s.read())
            checks["config"] = (config.get("llm_base_url") == SERVER + "/v1")
        except Exception:
            pass
        ready = all(checks.values())
        remaining = [k for k, ok in checks.items() if not ok]
        if action == "status":
            return result("success", "status_read", "Состояние прочитано.",
                          completed=checks, ready_to_verify=ready,
                          resume_from=(remaining[0] if remaining else None))
        if not ready:
            return result("error", "verify_incomplete",
                          "Не готово: " + ", ".join(remaining) +
                          ". Нажмите кнопку ещё раз — установка продолжится "
                          "с недостающего шага.", completed=checks)
        # Проверка без вызова модели: сервер жив и конфиг указывает на него.
        # Первый настоящий ответ модель даст уже в работе — локально и
        # бесплатно, поэтому пробный прогон здесь не нужен и не делается.
        return result("success", "ready",
                      "Локальная модель подключена: " + model + " на " + SERVER + ".",
                      model=model, completed=checks)

    return result("error", "unsupported_step", "Неизвестный этап установки.")
