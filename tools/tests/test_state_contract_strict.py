#!/usr/bin/env python3
"""Regression coverage for the exact extella.automation_state.v1 value contract."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "state_contract"
sys.path.insert(0, str(TOOLS))

from check_state_contract import check_report  # noqa: E402


def fixture(name):
    with (FIXTURES / name).open(encoding="utf-8") as source:
        return json.load(source)


def codes(report):
    return {item["code"] for item in report["errors"]}


class StateContractStrictTest(unittest.TestCase):
    def test_positive_fixtures_pass(self):
        for name in ("valid_full.json", "valid_unknowns.json"):
            with self.subTest(name=name):
                report = check_report(fixture(name))
                self.assertTrue(report["ready"], report)
                self.assertEqual([], report["errors"])

    def test_invalid_types_fixture_closes_the_presence_only_hole(self):
        report = check_report(fixture("invalid_types.json"))
        self.assertFalse(report["ready"])
        self.assertTrue({
            "STATE_ENABLED_TYPE",
            "STATE_ACTIVE_VERSION_INVALID",
            "STATE_LAST_RUN_INVALID",
            "STATE_LAST_RESULT_INVALID",
            "STATE_ERROR_CODE_REQUIRED",
            "STATE_SCHEDULE_ACTIVE_REQUIRED",
            "STATE_SCHEDULE_NEXT_RUN_REQUIRED",
            "STATE_CHECKED_AT_FORMAT",
            "BOUND_TO_HOSTING_INVALID",
            "BOUND_TO_HOST_INVALID",
            "BOUND_TO_PLATFORM_PROFILE_ID_INVALID",
            "BOUND_TO_ACCOUNT_REF_INVALID",
            "BOUND_TO_AGENT_ID_INVALID",
            "BOUND_TO_SINCE_FORMAT",
        }.issubset(codes(report)), report)

    def test_invalid_nested_fixture_reports_each_nested_path(self):
        report = check_report(fixture("invalid_nested.json"))
        self.assertFalse(report["ready"])
        expected = {
            ("STATE_LAST_RUN_INVALID", "last_run.at"),
            ("STATE_ERROR_CODE_REQUIRED", "last_error.code"),
            ("STATE_ERROR_MESSAGE_RU_REQUIRED", "last_error.message_ru"),
            ("STATE_ERROR_MESSAGE_EN_REQUIRED", "last_error.message_en"),
            ("STATE_SCHEDULE_SHAPE", "schedules[0]"),
            ("STATE_SCHEDULE_ID_REQUIRED", "schedules[1].id"),
            ("STATE_SCHEDULE_NEXT_RUN_INVALID", "schedules[1].next_run"),
            ("STATE_SCHEDULE_NEXT_RUN_REQUIRED", "schedules[2].next_run"),
            ("BOUND_TO_AGENT_ID_DUPLICATE", "bound_to.agent_ids[1]"),
            ("BOUND_TO_AGENT_ID_INVALID", "bound_to.agent_ids[2]"),
        }
        actual = {(item["code"], item["path"]) for item in report["errors"]}
        self.assertTrue(expected.issubset(actual), report)

    def test_last_run_accepts_only_a_timestamp_or_timestamp_object(self):
        base = fixture("valid_unknowns.json")
        accepted = [
            None,
            "2026-08-10T09:14:00Z",
            1770000000,
            {"at": "2026-08-10T09:14:00+05:00", "kind": "manual"},
            {"ts": 1770000000},
        ]
        rejected = [True, "yesterday", [], {}, {"kind": "manual"}, {"at": None}]
        for value in accepted:
            with self.subTest(accepted=value):
                doc = copy.deepcopy(base)
                doc["last_run"] = value
                self.assertTrue(check_report(doc)["ready"], check_report(doc))
        for value in rejected:
            with self.subTest(rejected=value):
                doc = copy.deepcopy(base)
                doc["last_run"] = value
                self.assertIn("STATE_LAST_RUN_INVALID", codes(check_report(doc)))

    def test_semver_and_last_result_use_closed_grammars(self):
        base = fixture("valid_unknowns.json")
        for value in (None, "0.0.0", "1.2.3-alpha.1+build.7"):
            with self.subTest(version=value):
                doc = copy.deepcopy(base)
                doc["active_version"] = value
                self.assertTrue(check_report(doc)["ready"], check_report(doc))
        for value in ("1.2", "01.2.3", "1.2.3-01", " 1.2.3", 123):
            with self.subTest(invalid_version=value):
                doc = copy.deepcopy(base)
                doc["active_version"] = value
                self.assertIn("STATE_ACTIVE_VERSION_INVALID", codes(check_report(doc)))
        for value in (None, "ok", "failed", "partial"):
            with self.subTest(result=value):
                doc = copy.deepcopy(base)
                doc["last_result"] = value
                self.assertTrue(check_report(doc)["ready"], check_report(doc))
        for value in ("error", "running", True, {}):
            with self.subTest(invalid_result=value):
                doc = copy.deepcopy(base)
                doc["last_result"] = value
                self.assertIn("STATE_LAST_RESULT_INVALID", codes(check_report(doc)))

    def test_cli_returns_zero_for_positive_and_one_for_negative_fixture(self):
        gate = TOOLS / "check_state_contract.py"
        for name, expected in (("valid_full.json", 0), ("invalid_types.json", 1)):
            with self.subTest(name=name):
                result = subprocess.run(
                    [sys.executable, str(gate), str(FIXTURES / name), "--json"],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(expected == 0, payload["ready"])

    def test_every_issue_stays_machine_readable_and_bilingual(self):
        for name in ("invalid_types.json", "invalid_nested.json"):
            report = check_report(fixture(name))
            for issue in report["errors"] + report["warnings"]:
                with self.subTest(name=name, code=issue.get("code")):
                    self.assertTrue(issue.get("code"))
                    self.assertTrue(issue.get("path") is not None)
                    self.assertTrue(issue.get("message_ru"))
                    self.assertTrue(issue.get("message_en"))


if __name__ == "__main__":
    unittest.main()
