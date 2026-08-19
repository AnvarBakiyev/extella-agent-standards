def extella_codex_product_setup(action="preflight") -> str:
    import json, os, platform, secrets, shutil, subprocess, urllib.request
    step = action
    BUILDER_REPO = "https://github.com/AnvarBakiyev/extella-codex-bridge.git"
    BUILDER_REF = "v0.3.6"
    SETUP_VERSION = "3.2.19"
    # Independent agent-building standards contract; do not advance with bridge-only releases.
    STANDARDS_REF = "v0.3.0"
    MARKETPLACE = "extella-codex"
    PLUGIN = "extella-codex-bridge@extella-codex"

    def result(status, code, message, **extra):
        payload = {"status": status, "code": code, "message": message,
                   "step": step, "setup_version": SETUP_VERSION, "model_called": False,
                   "agent_called": False, "paid": False}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)

    HOME = os.path.expanduser("~")

    def shell_path_dirs():
        shell = os.environ.get("SHELL") or "/bin/zsh"
        for flags in ("-ilc", "-lc"):
            try:
                completed = subprocess.run(
                    [shell, flags, "printf %s \"$PATH\""],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, timeout=20, shell=False)
            except Exception:
                continue
            if completed.returncode == 0:
                roots = [part for part in (completed.stdout or "").split(":")
                         if part.startswith("/")]
                if roots:
                    return roots
        return []

    def version_manager_dirs():
        found = []
        for base in [os.path.join(HOME, ".nvm", "versions", "node"),
                     os.path.join(HOME, ".fnm", "node-versions"),
                     os.path.join(HOME, "n", "versions", "node"),
                     os.path.join(HOME, ".volta", "tools", "image", "node")]:
            try:
                entries = sorted(os.listdir(base))
            except Exception:
                continue
            for entry in entries:
                for tail in ((entry, "bin"), (entry, "installation", "bin")):
                    candidate = os.path.join(base, *tail)
                    if os.path.isdir(candidate):
                        found.append(candidate)
        return found

    def candidate_roots():
        roots = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
                 os.path.join(HOME, ".local", "bin"),
                 os.path.join(HOME, ".npm-global", "bin"),
                 os.path.join(HOME, ".bun", "bin"),
                 os.path.join(HOME, ".volta", "bin"),
                 os.path.join(HOME, "Library", "pnpm"),
                 os.path.join(HOME, ".yarn", "bin"),
                 os.path.join(HOME, ".asdf", "shims")]
        ordered = []
        for root in roots + version_manager_dirs() + shell_path_dirs():
            if root not in ordered:
                ordered.append(root)
        return ordered

    def find_command(name):
        found = shutil.which(name)
        if found:
            return found
        for root in candidate_roots():
            candidate = os.path.join(root, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return ""

    def safe_env():
        env = dict(os.environ)
        env["PATH"] = ":".join(candidate_roots() + [env.get("PATH", "")])
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GH_PROMPT_DISABLED"] = "1"
        for key in ["EXTELLA_API_TOKEN", "EXTELLA_SECONDARY_API_TOKEN",
                    "EXTELLA_BRIDGE_SECRET", "OPENAI_API_KEY", "CODEX_API_KEY"]:
            env.pop(key, None)
        return env

    def run(args, timeout=120, allow_failure=False):
        try:
            completed = subprocess.run(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, timeout=timeout,
                env=safe_env(), shell=False)
        except subprocess.TimeoutExpired:
            if allow_failure:
                return None
            raise RuntimeError("command_timeout")
        except Exception:
            if allow_failure:
                return None
            raise RuntimeError("command_failed")
        if completed.returncode != 0:
            if allow_failure:
                return None
            raise RuntimeError("command_exit_" + str(completed.returncode))
        return completed.stdout or ""

    def current_token():
        token = os.environ.get("EXTELLA_API_TOKEN", "").strip()
        if len(token) >= 8:
            return token
        try:
            token = open(os.path.join(HOME, ".extella", "api_token.txt"),
                encoding="utf-8").read(4096).strip()
        except Exception:
            token = ""
        if len(token) >= 8:
            return token
        try:
            probe = subprocess.run(["/bin/launchctl", "getenv",
                "EXTELLA_API_TOKEN"], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, timeout=20, shell=False)
            token = (probe.stdout or "").strip() if probe.returncode == 0 else ""
        except Exception:
            token = ""
        if len(token) >= 8:
            return token
        try:
            with open(os.path.join(HOME, "extella_wizard", "app", "config.json"),
                      "r", encoding="utf-8") as stream:
                wizard = json.loads(stream.read(65536))
            for field in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
                token = str(wizard.get(field) or "").strip()
                if len(token) >= 8:
                    return token
        except Exception:
            pass
        return ""

    def validate_token(token):
        if len(token) < 8:
            return False
        body = json.dumps({"token": token}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.extella.ai/api/token/validate", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status < 200 or response.status >= 300:
                    return False
                payload = json.loads(response.read(65537).decode("utf-8"))
                return payload.get("valid") is True
        except Exception:
            return False

    def parse_json(text):
        try:
            return json.loads(text)
        except Exception:
            return None

    def installed_plugin():
        listing = parse_json(run([codex, "plugin", "list", "--json"],
            timeout=60)) or {}
        for item in listing.get("installed", []):
            if (item.get("pluginId") == PLUGIN and
                    item.get("installed") is True and
                    item.get("enabled") is True and
                    item.get("version") == BUILDER_REF[1:]):
                source = item.get("source") or {}
                path = str(source.get("path", "") or "")
                if os.path.isabs(path):
                    return item, path
        return None, ""

    if platform.system() != "Darwin":
        return result("error", "unsupported_os",
            "Автоматическая установка пока поддерживает только macOS.")

    codex = find_command("codex")
    git = find_command("git")
    launchctl = find_command("launchctl")
    node = find_command("node")
    if not codex:
        return result("error", "codex_not_installed",
            "Codex не установлен на этом компьютере.")
    if not git or not launchctl or not node:
        return result("error", "system_tools_missing",
            "На компьютере не найдены системные инструменты git, node или launchctl.")

    if step == "preflight":
        # Preflight is deliberately local and side-effect-free. Extella
        # account credentials are not required until the later credentials
        # step, where they are installed into the local bridge environment.
        try:
            version = run([codex, "--version"], timeout=20).strip()[:120]
        except Exception:
            return result("error", "codex_version_check_failed",
                "Codex найден, но его не удалось запустить.")
        try:
            login = subprocess.run([codex, "login", "status"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=30, env=safe_env(), shell=False)
        except Exception:
            return result("error", "codex_login_check_failed",
                "Не удалось проверить вход в Codex.")
        if login.returncode != 0:
            reported = ((login.stdout or "") + "\n" +
                        (login.stderr or "")).strip().lower()
            if "not logged in" in reported:
                return result("error", "codex_auth_required",
                    "Войдите в Codex на этом компьютере командой `codex login`, затем повторите.")
            return result("error", "codex_login_check_failed",
                "Codex не смог проверить состояние входа.")
        return result("success", "preflight_ok", "Проверки пройдены.",
            codex_version=version, builder_ref=BUILDER_REF,
            standards_ref=STANDARDS_REF)

    if step == "install":
        try:
            listing_raw = run([codex, "plugin", "marketplace",
                "list", "--json"], timeout=45)
        except Exception:
            return result("error", "marketplace_list_failed",
                "Codex не смог прочитать список источников плагинов.")
        listing = parse_json(listing_raw)
        if not isinstance(listing, dict):
            return result("error", "marketplace_list_invalid",
                "Codex вернул неразборчивый список источников плагинов.")
        exists = any(item.get("name") == MARKETPLACE
            for item in listing.get("marketplaces", []))
        if exists:
            try:
                run([codex, "plugin", "marketplace", "remove", MARKETPLACE,
                    "--json"], timeout=90)
            except Exception:
                return result("error", "marketplace_remove_failed",
                    "Codex не смог обновить прежний источник Extella.")
        try:
            run([codex, "plugin", "marketplace", "add",
                "AnvarBakiyev/extella-codex-bridge", "--ref", BUILDER_REF,
                "--json"], timeout=180)
        except Exception:
            return result("error", "marketplace_add_failed",
                "Codex не смог добавить проверенный источник Extella.")
        try:
            run([codex, "plugin", "add", PLUGIN, "--json"], timeout=180)
        except Exception:
            return result("error", "plugin_install_failed",
                "Codex не смог установить Extella Codex Bridge.")
        try:
            installed, plugin_path = installed_plugin()
        except Exception:
            return result("error", "plugin_verification_failed",
                "Codex не смог проверить установленный мост.")
        if not installed or not plugin_path:
            return result("error", "plugin_version_mismatch",
                "Codex установил другую версию Extella Codex Bridge.")
        return result("success", "plugin_installed",
            "Extella Codex Bridge установлен.", plugin_version="0.3.6")

    if step == "credentials":
        token = current_token()
        if not validate_token(token):
            return result("error", "extella_token_unavailable",
                "Не удалось подтвердить токен текущего аккаунта Extella.")
        try:
            run([launchctl, "setenv", "EXTELLA_API_TOKEN", token], timeout=20)
            existing = run([launchctl, "getenv", "EXTELLA_BRIDGE_SECRET"],
                timeout=20, allow_failure=True) or ""
            if len(existing.strip()) < 32:
                bridge_secret = secrets.token_hex(32)
                run([launchctl, "setenv", "EXTELLA_BRIDGE_SECRET",
                    bridge_secret], timeout=20)
                bridge_secret = ""
        except Exception:
            return result("error", "credential_setup_failed",
                "Не удалось подключить локальные переменные Extella к Codex.")
        token = ""
        return result("success", "credentials_configured",
            "Аккаунт Extella подключён локально.")

    if step == "bridge":
        try:
            _, plugin_path = installed_plugin()
            script = os.path.join(plugin_path, "scripts",
                "configure-bridge-macos.mjs")
            if not plugin_path or not os.path.isfile(script):
                return result("error", "bridge_script_unavailable",
                    "Не найден проверенный установщик локального моста.")
            output = parse_json(run([node, script,
                "--account-wide",
                "--confirm-account-scope", "I_UNDERSTAND_ALL_AGENTS",
                "--capability", "general-assistance",
                "--provider", "codex",
                "--confirm-live-cost", "I_UNDERSTAND_COST"],
                timeout=180)) or {}
            if (output.get("status") != "configured" or
                    output.get("authorization_scope") != "account"):
                raise RuntimeError("bridge_not_configured")
        except Exception:
            return result("error", "bridge_setup_failed",
                "Не удалось запустить локальный мост Codex.")
        return result("success", "bridge_ready",
            "Локальный мост Codex запущен.", live_enabled=True)

    if step == "verify":
        try:
            installed, _ = installed_plugin()
            if not installed:
                return result("error", "plugin_verification_failed",
                    "Codex не подтвердил установленную версию Extella Codex Bridge.")
            token_present = run([launchctl, "getenv", "EXTELLA_API_TOKEN"],
                timeout=20, allow_failure=True) or ""
            secret_present = run([launchctl, "getenv", "EXTELLA_BRIDGE_SECRET"],
                timeout=20, allow_failure=True) or ""
            binding = run([launchctl, "getenv",
                "EXTELLA_BRIDGE_ACCOUNT_BINDING"],
                timeout=20, allow_failure=True) or ""
            port = run([launchctl, "getenv", "EXTELLA_BRIDGE_PORT"],
                timeout=20, allow_failure=True) or "8787"
            if (len(token_present.strip()) < 8 or
                    len(secret_present.strip()) < 32 or
                    len(binding.strip()) != 64):
                return result("error", "environment_verification_failed",
                    "Локальные параметры подключения не сохранились.")
            with urllib.request.urlopen("http://127.0.0.1:" +
                    str(int(port.strip())) + "/health", timeout=10) as response:
                health = json.loads(response.read(65536).decode("utf-8"))
            if (health.get("status") != "ok" or
                    health.get("live_enabled") is not True or
                    "codex" not in health.get("providers", []) or
                    "account" not in health.get("authorization_scopes", []) or
                    health.get("execution_policy_version") != "1.0" or
                    health.get("default_execution_profile_id") != "answer-only" or
                    not any(item.get("id") == "answer-only" and
                        item.get("status") == "available" for item in
                        health.get("execution_profiles", []))):
                return result("error", "bridge_verification_failed",
                    "Локальный мост не подтвердил account-wide режим.")
        except Exception:
            return result("error", "verification_failed",
                "Не удалось проверить итоговую конфигурацию Codex.")
        return result("success", "ready", "Codex подключён к Extella.",
            plugin_version="0.3.6", restart_required=False,
            live_enabled=True, authorization_scope="account",
            execution_policy_version=health.get("execution_policy_version"),
            default_execution_profile_id=health.get("default_execution_profile_id"),
            execution_profiles=health.get("execution_profiles", []))

    return result("error", "unsupported_step",
        "Установщик получил неизвестный этап.")
