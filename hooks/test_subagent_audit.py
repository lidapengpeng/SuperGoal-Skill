#!/usr/bin/env python3
"""Deterministic tests for the namespaced state-write advisory."""

import tempfile
import unittest
from pathlib import Path

from subagent_audit import (
    WRITE_SCOPES,
    audit,
    changed_paths,
    find_supergoal,
    get_agent_id,
    get_agent_type,
    hook_decision,
    scope_violations,
    snapshot,
    write_baseline,
)


ROLE = "supergoal_luna_executor"


class SubagentAuditTests(unittest.TestCase):
    def test_namespaced_roster_and_payload_extraction(self):
        self.assertEqual(set(WRITE_SCOPES), {
            "supergoal_luna_executor",
            "supergoal_researcher",
            "supergoal_reviewer",
        })
        self.assertEqual(get_agent_type({"agent_type": ROLE}), ROLE)
        self.assertEqual(get_agent_type({"subagent": {"name": "supergoal_researcher"}}), "supergoal_researcher")
        self.assertEqual(get_agent_id({"agent": {"thread_id": "task-1"}}), "task-1")
        self.assertIsNone(get_agent_type({"nothing": 1}))

    def test_snapshot_diff_and_scope_detect_durable_state_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            supergoal = Path(directory) / ".supergoal"
            (supergoal / "tmp").mkdir(parents=True)
            (supergoal / "worktrees" / "task-1").mkdir(parents=True)
            (supergoal / "tmp" / "scratch.txt").write_text("scratch", encoding="utf-8")
            (supergoal / "worktrees" / "task-1" / "change.py").write_text("change", encoding="utf-8")
            (supergoal / "run_manifest.json").write_text("{}", encoding="utf-8")
            before = snapshot(supergoal)
            (supergoal / "run_manifest.json").write_text('{"changed":true}', encoding="utf-8")
            after = snapshot(supergoal)
            self.assertEqual(changed_paths(before, after), ["run_manifest.json"])
            self.assertEqual(scope_violations(ROLE, before, after), ["run_manifest.json"])
            self.assertNotIn("tmp/scratch.txt", before)
            self.assertNotIn("worktrees/task-1/change.py", before)

    def test_protected_baseline_and_hook_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            supergoal = root / ".supergoal"
            supergoal.mkdir()
            audit_root = root / "audit-state"
            event = {"cwd": str(root), "agent_type": ROLE, "agent_id": "task-1"}
            self.assertIsNone(hook_decision(event, "start", audit_root))
            (supergoal / "run_manifest.json").write_text("{}", encoding="utf-8")
            decision = hook_decision(event, "stop", audit_root)
            self.assertEqual(decision["decision"], "block")
            self.assertIn("run_manifest.json", decision["reason"])

            self.assertTrue(write_baseline(supergoal, ROLE, "task-2", snapshot(supergoal), audit_root))
            violations, current = audit(supergoal, ROLE, "task-2", audit_root)
            self.assertEqual(violations, [])
            self.assertIsInstance(current, dict)

    def test_missing_baseline_and_git_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            supergoal = root / ".supergoal"
            supergoal.mkdir()
            event = {"cwd": str(root), "agent_type": ROLE, "agent_id": "missing"}
            decision = hook_decision(event, "stop", root / "audit-state")
            self.assertIn("no baseline", decision["reason"])
            nested = root / "nested"
            nested.mkdir()
            self.assertEqual(find_supergoal(nested), supergoal.resolve())


if __name__ == "__main__":
    unittest.main()
