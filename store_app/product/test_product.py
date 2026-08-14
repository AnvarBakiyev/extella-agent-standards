#!/usr/bin/env python3
"""Локальные проверки продукта; не ставят плагин и не вызывают Extella."""

import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE = ROOT / "store_app" / "dist" / "extella-development-3.0.0.zip"

spec = importlib.util.spec_from_file_location("codex_setup", HERE / "codex_setup.py")
codex_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codex_setup)


class ProductTests(unittest.TestCase):
    def test_archive_contains_local_marketplace_and_valid_hashes(self):
        self.assertTrue(ARCHIVE.is_file())
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            with zipfile.ZipFile(ARCHIVE) as archive:
                archive.extractall(root)
            codex_setup.verify_bundle(root)
            plugin = json.loads((
                root / "bridge-marketplace/plugins/extella-codex-bridge/.codex-plugin/plugin.json"
            ).read_text())
            self.assertEqual(plugin["version"], "0.3.4")
            self.assertTrue((root / "bridge-marketplace/.agents/plugins/marketplace.json").is_file())

    def test_integrity_check_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "payload.txt").write_text("safe")
            digest = codex_setup.sha256(root / "payload.txt")
            (root / "bundle-sha256.json").write_text(json.dumps({"files": {"payload.txt": digest}}))
            codex_setup.verify_bundle(root)
            (root / "payload.txt").write_text("changed")
            with self.assertRaises(codex_setup.SetupError):
                codex_setup.verify_bundle(root)

    def test_expert_always_returns_json_for_unsupported_action(self):
        namespace = {}
        exec((HERE / "expert_extella_codex_product_setup.py").read_text(), namespace)
        value = json.loads(namespace["extella_codex_product_setup"]("unexpected"))
        self.assertEqual(value["status"], "error")
        self.assertEqual(value["code"], "unsupported_action")
        self.assertFalse(value["model_called"])


if __name__ == "__main__":
    unittest.main()
