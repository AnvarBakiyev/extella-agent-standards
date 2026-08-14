#!/usr/bin/env python3
"""Собрать детерминированный архив продукта с локальным marketplace моста."""

import argparse
import hashlib
import json
import pathlib
import shutil
import tempfile
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "store_app" / "product"
DIST = ROOT / "store_app" / "dist"
OUTPUT = DIST / "extella-development-3.0.0.zip"
EXPECTED_PLUGIN_VERSION = "0.3.4"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def copy_bridge(source_root: pathlib.Path, destination: pathlib.Path) -> None:
    manifest = json.loads((source_root / "plugins/extella-codex-bridge/.codex-plugin/plugin.json").read_text())
    if manifest.get("version") != EXPECTED_PLUGIN_VERSION:
        raise SystemExit("мост должен иметь версию 0.3.4 до сборки продукта")
    shutil.copytree(
        source_root / "plugins/extella-codex-bridge",
        destination / "plugins/extella-codex-bridge",
        ignore=shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc"),
    )
    (destination / ".agents/plugins").mkdir(parents=True)
    shutil.copy2(
        source_root / ".agents/plugins/marketplace.json",
        destination / ".agents/plugins/marketplace.json",
    )


def write_hash_manifest(stage: pathlib.Path) -> None:
    files = {}
    for path in sorted((stage / "bridge-marketplace").rglob("*")):
        if path.is_file():
            files[path.relative_to(stage).as_posix()] = sha256(path)
    files["codex_setup.py"] = sha256(stage / "codex_setup.py")
    (stage / "bundle-sha256.json").write_text(
        json.dumps({"algorithm": "sha256", "files": files}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_zip(stage: pathlib.Path) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                relative = path.relative_to(stage).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(2026, 8, 14, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o755 if path.name in {"install.py", "codex_setup.py"} else 0o644) << 16
                archive.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bridge-repo",
        type=pathlib.Path,
        default=ROOT.parent / "extella-codex-bridge-guide-source-sync",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="extella-development-product-") as temporary:
        stage = pathlib.Path(temporary)
        for name in ("MANIFEST.yaml", "install.py", "codex_setup.py"):
            shutil.copy2(PRODUCT / name, stage / name)
        shutil.copy2(ROOT / "templates/manifest_check.py", stage / "manifest_check.py")
        copy_bridge(args.bridge_repo.resolve(), stage / "bridge-marketplace")
        write_hash_manifest(stage)
        write_zip(stage)
    print(f"Собрал {OUTPUT}: {OUTPUT.stat().st_size} байт")


if __name__ == "__main__":
    main()
