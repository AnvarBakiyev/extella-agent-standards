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
        # Продукт рассчитан на macOS. На другой системе он отказывает РАНЬШЕ —
        # кодом unsupported_os, и это тоже честный отказ. Прежний тест ждал
        # только macOS-ветку и был зелёным ровно на машине автора: прогон на
        # чистой Linux-машине 16.08.2026 это и вскрыл.
        self.assertIn(value["code"], ("unsupported_step", "unsupported_os"))
        self.assertFalse(value["model_called"])

    def test_expert_handles_nvm_login_and_listener_token_sources(self):
        source = (HERE / "expert_extella_codex_product_setup.py").read_text()
        self.assertIn('for flags in ("-ilc", "-lc")', source)
        self.assertIn('".nvm", "versions", "node"', source)
        self.assertIn('env["PATH"] = ":".join(candidate_roots()', source)
        self.assertIn('"not logged in" in reported', source)
        self.assertIn('"codex_auth_required"', source)
        self.assertIn('"extella_wizard", "app", "config.json"', source)
        wizard_block = source[source.index('"extella_wizard"'):source.index("def validate_token")]
        self.assertNotIn("agent_id", wizard_block)

    def test_expert_generator_reads_the_canonical_bridge_checkout(self):
        source = (HERE / "build_expert.mjs").read_text()
        self.assertIn('"../../../extella-codex-bridge"', source)
        self.assertNotIn("extella-codex-bridge-guide-source-sync", source)

    def test_prerelease_provisions_all_three_setup_experts_with_matching_labels(self):
        # Проверяем структуру, а не конкретный номер версии: тест, приколоченный
        # к литералу «3.2.14», ломался каждый выпуск. Важно другое — выкладка
        # ставит все три установщика, а метка версии в коде совпадает с версией
        # листинга (страховка выкладки требует именно этого равенства).
        import re
        source = (HERE / "deploy_prerelease_claude.py").read_text()
        listing = re.search(r'^VERSION = "([\d.]+)"', source, re.M)
        self.assertIsNotNone(listing, "версия листинга не найдена в выкладке")
        version = listing.group(1)
        for name in ("extella_codex_product_setup",
                     "extella_claude_product_setup",
                     "extella_local_llm_product_setup"):
            self.assertIn(f'"{name}"', source, f"{name} не ставится выкладкой")
        for filename in ("expert_extella_codex_product_setup.py",
                         "expert_extella_local_llm_setup.py"):
            code = (HERE / filename).read_text()
            self.assertIn(f'SETUP_VERSION = "{version}"', code,
                          f"метка версии в {filename} отстала от версии листинга {version}")
            self.assertIn('"setup_version": SETUP_VERSION', code)

    def test_local_fallback_uses_the_same_discovery_and_token_contract(self):
        source = (HERE / "codex_setup.py").read_text()
        self.assertIn('for flags in ("-ilc", "-lc")', source)
        self.assertIn('home / ".nvm/versions/node"', source)
        self.assertIn('env["PATH"] = ":".join(candidate_roots()', source)
        environment = source.index('os.environ.get("EXTELLA_API_TOKEN"')
        token_file = source.index('".extella/api_token.txt"')
        launchctl = source.index('["/bin/launchctl", "getenv", "EXTELLA_API_TOKEN"]')
        wizard = source.index('"extella_wizard/app/config.json"')
        self.assertLess(environment, token_file)
        self.assertLess(token_file, launchctl)
        self.assertLess(launchctl, wizard)
        wizard_block = source[wizard:source.index("def refresh_local_marketplace")]
        self.assertNotIn("agent_id", wizard_block)

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
