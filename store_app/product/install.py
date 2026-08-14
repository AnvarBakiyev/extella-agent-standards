#!/usr/bin/env python3
"""Разложить проверенный пакет моста; Codex подключается позже одной кнопкой."""

import json
import os
import pathlib
import shutil
import sys
import tempfile

import manifest_check
from codex_setup import PRODUCT_VERSION, verify_bundle


HERE = pathlib.Path(__file__).resolve().parent
PRODUCT_ROOT = pathlib.Path.home() / ".extella" / "extella-development"
RELEASES = PRODUCT_ROOT / "releases"
DESTINATION = RELEASES / PRODUCT_VERSION


def fail(message: str) -> int:
    print(json.dumps({"status": "error", "code": "install_failed", "message": message}, ensure_ascii=False))
    return 1


def copy_payload(destination: pathlib.Path) -> None:
    shutil.copy2(HERE / "codex_setup.py", destination / "codex_setup.py")
    shutil.copy2(HERE / "bundle-sha256.json", destination / "bundle-sha256.json")
    shutil.copytree(HERE / "bridge-marketplace", destination / "bridge-marketplace")


def main() -> int:
    if not manifest_check.run(HERE / "MANIFEST.yaml"):
        return fail("обязательные зависимости приложения не прошли проверку")
    try:
        verify_bundle(HERE)
    except Exception:
        return fail("контрольная сумма локального пакета моста не совпала")

    RELEASES.mkdir(parents=True, exist_ok=True, mode=0o700)
    if DESTINATION.exists():
        try:
            verify_bundle(DESTINATION)
        except Exception:
            return fail("установленная копия повреждена; переустанови приложение из магазина")
    else:
        temporary = pathlib.Path(tempfile.mkdtemp(prefix=".3.0.0-", dir=RELEASES))
        try:
            copy_payload(temporary)
            verify_bundle(temporary)
            temporary.rename(DESTINATION)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            return fail("не удалось разложить локальный пакет моста")

    binding = {
        "product": "extella-development",
        "version": PRODUCT_VERSION,
        "agent_bound": bool(os.environ.get("EXTELLA_AGENT_ID", "").strip()),
    }
    PRODUCT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    binding_path = PRODUCT_ROOT / "agent_binding.json"
    temporary_binding = PRODUCT_ROOT / ".agent_binding.json.tmp"
    temporary_binding.write_text(json.dumps(binding, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary_binding, 0o600)
    temporary_binding.replace(binding_path)
    print(json.dumps({
        "status": "success",
        "code": "product_staged",
        "version": PRODUCT_VERSION,
        "codex_connected": False,
        "model_called": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
