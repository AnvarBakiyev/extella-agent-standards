#!/usr/bin/env python3
"""Безмодельная установка и проверка локального Extella ↔ Codex Bridge."""

import hashlib
import json
import os
import pathlib
import platform
import secrets
import shutil
import subprocess
import sys
import urllib.request


PRODUCT_VERSION = "3.0.0"
PLUGIN_VERSION = "0.3.4"
MARKETPLACE = "extella-codex"
PLUGIN_ID = "extella-codex-bridge@extella-codex"
HERE = pathlib.Path(__file__).resolve().parent
MARKETPLACE_ROOT = HERE / "bridge-marketplace"
HASH_MANIFEST = HERE / "bundle-sha256.json"


class SetupError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(root: pathlib.Path = HERE) -> None:
    manifest = json.loads((root / "bundle-sha256.json").read_text(encoding="utf-8"))
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, dict) or not files:
        raise SetupError("bundle_manifest_invalid", "манифест пакета пуст")
    for relative, expected in files.items():
        if not isinstance(relative, str) or relative.startswith(("/", "../")) or "/../" in relative:
            raise SetupError("bundle_manifest_invalid", "в манифесте небезопасный путь")
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise SetupError("bundle_integrity_failed", "контрольная сумма пакета не совпала")


def command(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for root in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"):
        candidate = pathlib.Path(root) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def safe_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = ":".join([
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
        env.get("PATH", ""),
    ])
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GH_PROMPT_DISABLED"] = "1"
    for key in (
        "EXTELLA_API_TOKEN", "EXTELLA_SECONDARY_API_TOKEN", "EXTELLA_BRIDGE_SECRET",
        "OPENAI_API_KEY", "CODEX_API_KEY",
    ):
        env.pop(key, None)
    return env


def run(args, timeout=180, allow_failure=False):
    try:
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=safe_env(),
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        if allow_failure:
            return None
        raise SetupError("command_timeout", "локальная команда не завершилась вовремя") from error
    except Exception as error:
        if allow_failure:
            return None
        raise SetupError("command_failed", "не удалось запустить локальную команду") from error
    if completed.returncode != 0 and not allow_failure:
        raise SetupError("command_failed", "локальная команда завершилась ошибкой")
    return completed


def json_stdout(completed) -> dict:
    try:
        value = json.loads((completed.stdout or "").strip() or "{}")
    except Exception as error:
        raise SetupError("command_result_invalid", "локальная команда вернула не JSON") from error
    if not isinstance(value, dict):
        raise SetupError("command_result_invalid", "локальная команда вернула неверную форму")
    return value


def plugin_record(codex: str):
    listed = json_stdout(run([codex, "plugin", "list", "--json"], timeout=60))
    for item in listed.get("installed", []):
        if (
            item.get("pluginId") == PLUGIN_ID
            and item.get("installed") is True
            and item.get("enabled") is True
            and item.get("version") == PLUGIN_VERSION
        ):
            return item
    return None


def bridge_health():
    launchctl = command("launchctl") or "/bin/launchctl"
    port_result = run([launchctl, "getenv", "EXTELLA_BRIDGE_PORT"], timeout=20, allow_failure=True)
    port = ((port_result.stdout if port_result else "") or "8787").strip() or "8787"
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/health", timeout=10) as response:
            value = json.loads(response.read(65537).decode("utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def status_payload() -> dict:
    codex = command("codex")
    if not codex:
        return success("needs_codex", connected=False, message="Установи Codex CLI и войди в ChatGPT.")
    record = plugin_record(codex)
    health = bridge_health() if record else None
    connected = bool(
        health
        and health.get("status") == "ok"
        and health.get("live_enabled") is True
        and "codex" in health.get("providers", [])
        and "account" in health.get("authorization_scopes", [])
    )
    return success(
        "ready" if connected else "needs_install",
        connected=connected,
        plugin_version=record.get("version") if record else None,
        message="Codex подключён." if connected else "Нажми «Подключить Codex» ещё раз.",
    )


def current_token() -> str:
    path = pathlib.Path.home() / ".extella" / "api_token.txt"
    try:
        token = path.read_text(encoding="utf-8").strip()
    except Exception:
        token = ""
    if len(token) < 8:
        raise SetupError("extella_token_unavailable", "Открой Extella Desktop на этом Mac и повтори.")
    try:
        body = json.dumps({"token": token}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.extella.ai/api/token/validate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            valid = response.status < 300 and json.loads(response.read(65537)).get("valid") is True
    except Exception:
        valid = False
    if not valid:
        token = ""
        raise SetupError("extella_token_unavailable", "Не удалось подтвердить текущий аккаунт Extella.")
    return token


def refresh_local_marketplace(codex: str) -> pathlib.Path:
    verify_bundle()
    listing = json_stdout(run([codex, "plugin", "marketplace", "list", "--json"], timeout=60))
    if any(item.get("name") == MARKETPLACE for item in listing.get("marketplaces", [])):
        run([codex, "plugin", "marketplace", "remove", MARKETPLACE, "--json"], timeout=90)
    run([codex, "plugin", "marketplace", "add", str(MARKETPLACE_ROOT), "--json"], timeout=180)
    run([codex, "plugin", "add", PLUGIN_ID, "--json"], timeout=180)
    record = plugin_record(codex)
    source = pathlib.Path(str(((record or {}).get("source") or {}).get("path") or ""))
    if not record or not source.is_absolute() or not source.is_dir():
        raise SetupError("plugin_verification_failed", "Codex не подтвердил мост версии 0.3.4.")
    return source


def configure_credentials() -> None:
    token = current_token()
    launchctl = command("launchctl") or "/bin/launchctl"
    run([launchctl, "setenv", "EXTELLA_API_TOKEN", token], timeout=20)
    token = ""
    existing = run([launchctl, "getenv", "EXTELLA_BRIDGE_SECRET"], timeout=20, allow_failure=True)
    if not existing or len((existing.stdout or "").strip()) < 32:
        secret = secrets.token_hex(32)
        run([launchctl, "setenv", "EXTELLA_BRIDGE_SECRET", secret], timeout=20)
        secret = ""


def configure_bridge(plugin_path: pathlib.Path, node: str) -> None:
    configure = plugin_path / "scripts" / "configure-bridge-macos.mjs"
    sync = plugin_path / "scripts" / "deploy-extella-assets.mjs"
    if not configure.is_file() or not sync.is_file():
        raise SetupError("bridge_script_unavailable", "В пакете нет проверенного установщика моста.")
    configured = json_stdout(run([
        node, str(configure), "--account-wide",
        "--confirm-account-scope", "I_UNDERSTAND_ALL_AGENTS",
        "--capability", "general-assistance", "--provider", "codex",
        "--confirm-live-cost", "I_UNDERSTAND_COST",
    ], timeout=300))
    if configured.get("status") != "configured" or configured.get("authorization_scope") != "account":
        raise SetupError("bridge_setup_failed", "Локальный мост не подтвердил account-wide режим.")
    run([node, str(sync)], timeout=180)


def success(code: str, **extra) -> dict:
    value = {
        "status": "success",
        "code": code,
        "model_called": False,
        "agent_called": False,
        "paid": False,
    }
    value.update(extra)
    return value


def install() -> dict:
    if platform.system() != "Darwin":
        raise SetupError("unsupported_os", "Автоматическое подключение пока поддерживает macOS.")
    codex, node = command("codex"), command("node")
    if not codex:
        raise SetupError("codex_not_installed", "Установи Codex CLI, войди в ChatGPT и повтори.")
    if not node:
        raise SetupError("node_not_installed", "Установи Node.js 20+ и повтори.")
    login = run([codex, "login", "status"], timeout=30, allow_failure=True)
    if not login or login.returncode != 0:
        raise SetupError("codex_login_required", "Войди в ChatGPT через Codex CLI и повтори.")
    plugin_path = refresh_local_marketplace(codex)
    configure_credentials()
    configure_bridge(plugin_path, node)
    result = status_payload()
    if result.get("code") != "ready" or result.get("connected") is not True:
        raise SetupError("bridge_verification_failed", "Health не подтвердил готовность моста.")
    result.update({
        "plugin_version": PLUGIN_VERSION,
        "message": "Codex подключён к текущему аккаунту Extella.",
    })
    return result


def main(argv) -> int:
    action = argv[1] if len(argv) > 1 else "status"
    try:
        if action == "status":
            value = status_payload()
        elif action == "install":
            value = install()
        else:
            raise SetupError("unsupported_action", "Неизвестное действие установщика.")
    except SetupError as error:
        value = {
            "status": "error",
            "code": error.code,
            "message": str(error),
            "model_called": False,
            "agent_called": False,
            "paid": False,
        }
    except Exception:
        value = {
            "status": "error",
            "code": "installer_failed",
            "message": "Не удалось подключить Codex. Можно безопасно повторить.",
            "model_called": False,
            "agent_called": False,
            "paid": False,
        }
    print(json.dumps(value, ensure_ascii=False))
    return 0 if value.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
