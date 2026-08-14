def extella_codex_product_setup(action="status") -> str:
    """Запустить проверенный локальный setup; модель и токены наружу не возвращаются."""
    import json
    import os
    import pathlib
    import subprocess
    import sys

    if action not in ("status", "install"):
        return json.dumps({
            "status": "error", "code": "unsupported_action",
            "message": "Неизвестное действие установщика.",
            "model_called": False, "agent_called": False, "paid": False,
        }, ensure_ascii=False)
    script = pathlib.Path.home() / ".extella" / "extella-development" / "releases" / "3.0.0" / "codex_setup.py"
    if not script.is_file():
        return json.dumps({
            "status": "error", "code": "product_bundle_missing",
            "message": "Обнови или переустанови приложение «Разработка на Extella».",
            "model_called": False, "agent_called": False, "paid": False,
        }, ensure_ascii=False)
    env = dict(os.environ)
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        env.pop(key, None)
    try:
        completed = subprocess.run(
            [sys.executable, str(script), action],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=480 if action == "install" else 45,
            env=env,
            shell=False,
        )
        value = json.loads((completed.stdout or "").strip() or "{}")
    except Exception:
        value = {
            "status": "error", "code": "installer_failed",
            "message": "Локальный установщик не ответил. Можно безопасно повторить.",
            "model_called": False, "agent_called": False, "paid": False,
        }
    if not isinstance(value, dict) or not isinstance(value.get("status"), str) or not isinstance(value.get("code"), str):
        value = {
            "status": "error", "code": "installer_result_invalid",
            "message": "Установщик вернул неверную форму ответа.",
            "model_called": False, "agent_called": False, "paid": False,
        }
    return json.dumps(value, ensure_ascii=False)
