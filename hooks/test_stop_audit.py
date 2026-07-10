#!/usr/bin/env python3
"""Deterministic stdlib checks for the manifest-backed Stop advisory."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from stop_audit import completion_problems, find_supergoal, hook_decision, workspace_snapshot_id


SCRIPT = Path(__file__).with_name("stop_audit.py")
SHA = "sha256:" + "a" * 64


def _complete_manifest(phase="complete"):
    review = {
        "role": "supergoal_reviewer",
        "verdict": "PASS",
        "evidence": ["reviewed"],
    }
    return {
        "version": 1,
        "run_id": "run-stop-test",
        "base_sha": SHA,
        "phase": phase,
        "controller": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "ultra",
            "evidence": ["controller observation"],
        },
        "plan": {"review": review},
        "tasks": [],
        "integration": {"status": "complete", "evidence": ["merged"]},
        "review": review,
        "final_verification": {"status": "PASS", "evidence": ["tests passed"]},
    }


class StopAuditTests(unittest.TestCase):
    def _workspace(self, manifest=None, plan=False):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        supergoal = root / ".supergoal"
        supergoal.mkdir()
        if manifest is not None:
            (supergoal / "run_manifest.json").write_text(
                json.dumps(manifest, sort_keys=True), encoding="utf-8"
            )
        if plan:
            (supergoal / "PLAN.md").write_text("- [ ] active work\n", encoding="utf-8")
        return directory, root, supergoal

    def test_complete_manifest_allows_stop(self):
        directory, root, supergoal = self._workspace(_complete_manifest())
        with directory:
            self.assertEqual(completion_problems(supergoal), [])
            self.assertIsNone(hook_decision({"cwd": str(root), "stop_hook_active": False}))

    def test_execution_manifest_is_advised_not_complete(self):
        manifest = _complete_manifest("execution")
        for key in ("integration", "review", "final_verification"):
            manifest.pop(key)
        directory, root, _ = self._workspace(manifest)
        with directory:
            decision = hook_decision({"cwd": str(root), "stop_hook_active": False})
            self.assertEqual(decision["decision"], "block")
            self.assertIn("not complete", decision["reason"])

    def test_invalid_manifest_and_missing_active_manifest_are_advised(self):
        invalid = _complete_manifest()
        invalid["controller"]["model"] = ""
        directory, root, _ = self._workspace(invalid)
        with directory:
            decision = hook_decision({"cwd": str(root)})
            self.assertIn("controller needs a model", decision["reason"])

        directory, root, _ = self._workspace(plan=True)
        with directory:
            decision = hook_decision({"cwd": str(root)})
            self.assertIn("run_manifest.json is missing", decision["reason"])

    def test_inactive_or_repeat_stop_does_not_nudge(self):
        directory, root, _ = self._workspace()
        with directory:
            self.assertIsNone(hook_decision({"cwd": str(root)}))
            self.assertIsNone(hook_decision({"cwd": str(root), "stop_hook_active": True}))

    def test_cli_check_manifest_and_stdin_hook(self):
        directory, root, supergoal = self._workspace(_complete_manifest())
        with directory:
            manifest = supergoal / "run_manifest.json"
            checked = subprocess.run(
                [sys.executable, str(SCRIPT), "--check-manifest", "--manifest", str(manifest)],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertTrue(json.loads(checked.stdout)["pass"])

            execution = _complete_manifest("execution")
            for key in ("integration", "review", "final_verification"):
                execution.pop(key)
            manifest.write_text(json.dumps(execution), encoding="utf-8")
            event = subprocess.run(
                [sys.executable, str(SCRIPT)],
                input=json.dumps({"cwd": str(root), "stop_hook_active": False}),
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(event.returncode, 0, event.stderr)
            self.assertEqual(json.loads(event.stdout)["decision"], "block")

    def test_snapshot_excludes_state_files_and_find_walks_up(self):
        directory, root, supergoal = self._workspace(_complete_manifest())
        with directory:
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)
            source = root / "src" / "main.py"
            source.write_text("one\n", encoding="utf-8")
            first = workspace_snapshot_id(supergoal)
            (supergoal / "JOURNAL.md").write_text("state changes do not count\n", encoding="utf-8")
            self.assertEqual(first, workspace_snapshot_id(supergoal))
            source.write_text("two\n", encoding="utf-8")
            self.assertNotEqual(first, workspace_snapshot_id(supergoal))
            self.assertEqual(find_supergoal(nested), supergoal.resolve())


if __name__ == "__main__":
    unittest.main()
