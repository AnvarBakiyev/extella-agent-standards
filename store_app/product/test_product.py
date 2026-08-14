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

deploy_spec = importlib.util.spec_from_file_location("deploy_product", HERE / "deploy_product.py")
deploy_product = importlib.util.module_from_spec(deploy_spec)
deploy_spec.loader.exec_module(deploy_product)


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
        self.assertEqual(value["code"], "unsupported_step")
        self.assertFalse(value["model_called"])

    def test_deploy_requires_public_version_guard_and_cannot_publish_listing(self):
        source = (HERE / "deploy_product.py").read_text()
        self.assertIn("/api/add-version-stream/", source)
        self.assertNotIn("/api/publish-stream", source)
        self.assertNotIn("/publish\"", source)
        self.assertIn('VERSION = "3.0.4"', source)
        self.assertIn('files={"page": PAGE}', source)
        self.assertIn("--allow-public-version", source)

    def test_live_acceptance_unwraps_two_result_envelopes(self):
        value = deploy_product.unwrap_run_result({
            "result": {"result": json.dumps({
                "status": "success",
                "code": "ready",
                "model_called": False,
                "agent_called": False,
            })}
        })
        self.assertEqual(value["code"], "ready")


if __name__ == "__main__":
    unittest.main()
