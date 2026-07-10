#!/usr/bin/env python3
"""Deterministic stdlib tests for SuperGoal's portable manifest audit."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from manifest_audit import audit_manifest, validate_binding_canary, validate_manifest


SCRIPT = Path(__file__).with_name("manifest_audit.py")
BASE_SHA = "sha256:" + "a" * 64


def _review():
    return {
        "role": "supergoal_reviewer",
        "verdict": "PASS",
        "evidence": ["review record"],
    }


def _task(task_id, role, *, writes, status="complete", depends_on=None, path=None, worktree=None):
    task = {
        "id": task_id,
        "parent": "controller",
        "role": role,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "xhigh",
        "base_sha": BASE_SHA,
        "depends_on": depends_on or [],
        "writes": writes,
        "owned_paths": [path] if path else [],
        "forbidden_paths": [".supergoal", ".git"],
        "worktree": worktree,
        "verify": ["python3 -m unittest"],
        "status": status,
        "result": "completed {}".format(task_id),
        "evidence": ["test command exited 0"],
        "output_sha256": "sha256:" + "b" * 64,
        "runtime": {
            "agent_role": role,
            "model": "gpt-5.6-luna",
            "reasoning_effort": "xhigh",
            "evidence": ["runtime observation"],
        },
    }
    if status != "complete":
        task.pop("output_sha256")
        task.pop("runtime")
        task.pop("evidence")
    return task


def _manifest(phase="complete", tasks=None):
    return {
        "version": 1,
        "run_id": "run-20260709-a",
        "base_sha": BASE_SHA,
        "phase": phase,
        "controller": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "ultra",
            "evidence": ["controller runtime observation"],
        },
        "plan": {"review": _review()},
        "research": {"status": "complete", "evidence": ["research merged"]},
        "tasks": tasks if tasks is not None else [
            _task("research", "supergoal_researcher", writes=False, worktree=None),
            _task(
                "implement",
                "supergoal_luna_executor",
                writes=True,
                depends_on=["research"],
                path="src/feature.py",
                worktree=".supergoal/worktrees/implement",
            ),
        ],
        "integration": {"status": "complete", "evidence": ["merged in dependency order"]},
        "review": _review(),
        "final_verification": {"status": "PASS", "evidence": ["full suite exited 0"]},
    }


class ManifestAuditTests(unittest.TestCase):
    def test_plan_only_zero_workers_passes(self):
        manifest = _manifest("plan", [])
        for key in ("research", "integration", "review", "final_verification"):
            manifest.pop(key)
        result = validate_manifest(manifest)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["summary"]["task_count"], 0)

    def test_complete_manifest_passes_from_file_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run_manifest.json"
            path.write_text(json.dumps(_manifest(), sort_keys=True), encoding="utf-8")
            direct = audit_manifest(path)
            command = subprocess.run(
                [sys.executable, str(SCRIPT), "--manifest", str(path)],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertTrue(direct["pass"], direct)
            self.assertEqual(command.returncode, 0, command.stdout)
            self.assertEqual(json.loads(command.stdout), direct)

    def test_task_needs_model_effort_and_direct_parent(self):
        for field, value, needle in (
            ("model", "", "task implement needs a model"),
            ("reasoning_effort", "", "task implement needs reasoning_effort"),
            ("parent", "research", "nested parents"),
        ):
            with self.subTest(field=field):
                manifest = _manifest()
                manifest["tasks"][1][field] = value
                result = validate_manifest(manifest)
                self.assertFalse(result["pass"])
                self.assertTrue(any(needle in problem for problem in result["problems"]), result)

    def test_completed_task_needs_result_evidence_hash_and_runtime_binding(self):
        for field, value, needle in (
            ("result", "", "needs a result"),
            ("evidence", [], "needs evidence"),
            ("output_sha256", "self-report", "needs output_sha256"),
            ("runtime", {"agent_role": "supergoal_luna_executor"}, "runtime model does not match requested model"),
        ):
            with self.subTest(field=field):
                manifest = _manifest()
                manifest["tasks"][1][field] = value
                result = validate_manifest(manifest)
                self.assertFalse(result["pass"])
                self.assertTrue(any(needle in problem for problem in result["problems"]), result)

    def test_task_base_sha_and_path_boundaries(self):
        manifest = _manifest()
        manifest["tasks"][1]["base_sha"] = "stale-self-report"
        manifest["tasks"][1]["forbidden_paths"] = ["src"]
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("no valid base_sha" in problem for problem in result["problems"]), result)
        self.assertTrue(any("owns a forbidden path" in problem for problem in result["problems"]), result)

    def test_later_wave_may_use_a_new_valid_base_sha(self):
        manifest = _manifest()
        manifest["tasks"][1]["base_sha"] = "sha256:" + "c" * 64
        result = validate_manifest(manifest)
        self.assertTrue(result["pass"], result)

    def test_controller_needs_observed_evidence(self):
        manifest = _manifest()
        manifest["controller"]["evidence"] = []
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertIn("controller needs non-empty evidence", result["problems"])

    def test_runtime_may_use_a_profile_changed_model_when_it_matches_request(self):
        manifest = _manifest()
        manifest["controller"]["model"] = "gpt-controller-custom"
        manifest["controller"]["reasoning_effort"] = "high"
        task = manifest["tasks"][1]
        task["model"] = "gpt-executor-custom"
        task["reasoning_effort"] = "max"
        task["runtime"]["model"] = task["model"]
        task["runtime"]["reasoning_effort"] = task["reasoning_effort"]
        self.assertTrue(validate_manifest(manifest)["pass"])

    def test_owned_paths_and_writer_worktrees_are_unique(self):
        manifest = _manifest()
        second = _task(
            "implement-two",
            "supergoal_luna_executor",
            writes=True,
            path="src/feature.py",
            worktree=".supergoal/worktrees/implement",
        )
        manifest["tasks"].append(second)
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("owned path overlaps" in problem for problem in result["problems"]), result)
        self.assertTrue(any("share worktree" in problem for problem in result["problems"]), result)

    def test_normalized_paths_cannot_bypass_ownership_overlap(self):
        manifest = _manifest()
        manifest["tasks"].append(_task(
            "implement-normalized",
            "supergoal_luna_executor",
            writes=True,
            path="src//feature.py",
            worktree=".supergoal/worktrees/normalized",
        ))
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("owned path overlaps" in problem for problem in result["problems"]), result)

    def test_controller_state_and_windows_separators_are_not_ownable(self):
        manifest = _manifest()
        manifest["tasks"][1]["owned_paths"] = [".supergoal/run_manifest.json"]
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("may not own controller state" in problem for problem in result["problems"]), result)

        manifest = _manifest()
        manifest["tasks"][1]["owned_paths"] = ["src\\feature.py"]
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("safe relative paths" in problem for problem in result["problems"]), result)

    def test_read_only_workers_cannot_claim_paths_or_worktree(self):
        manifest = _manifest()
        research = manifest["tasks"][0]
        research["owned_paths"] = ["docs/notes.md"]
        research["worktree"] = ".supergoal/worktrees/research"
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("read-only task research may not own paths" in problem for problem in result["problems"]), result)
        self.assertTrue(any("worktree null or empty" in problem for problem in result["problems"]), result)

    def test_dag_cycles_and_completion_closure_fail(self):
        manifest = _manifest()
        manifest["tasks"][0]["depends_on"] = ["implement"]
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("contains a cycle" in problem for problem in result["problems"]), result)

        manifest = _manifest("execution")
        manifest["tasks"][0]["status"] = "planned"
        manifest["tasks"][0].pop("output_sha256")
        manifest["tasks"][0].pop("runtime")
        manifest["tasks"][0].pop("evidence")
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("unfinished dependency" in problem for problem in result["problems"]), result)

    def test_complete_requires_terminal_integration_review_and_final_validation(self):
        manifest = _manifest()
        manifest["tasks"][1]["status"] = "running"
        manifest["tasks"][1].pop("output_sha256")
        manifest["tasks"][1].pop("runtime")
        manifest["tasks"][1].pop("evidence")
        manifest["integration"] = {"status": "pending"}
        manifest["review"]["verdict"] = "FAIL"
        manifest["final_verification"]["status"] = "FAIL"
        result = validate_manifest(manifest)
        self.assertFalse(result["pass"])
        self.assertTrue(any("non-terminal tasks" in problem for problem in result["problems"]), result)
        self.assertTrue(any("completed integration" in problem for problem in result["problems"]), result)
        self.assertTrue(any("final independent review verdict" in problem for problem in result["problems"]), result)
        self.assertTrue(any("final_verification status" in problem for problem in result["problems"]), result)

    def test_maximum_ten_direct_task_records(self):
        tasks = [
            _task(
                "worker-{:02d}".format(index),
                "supergoal_luna_executor",
                writes=True,
                path="src/f{:02d}.py".format(index),
                worktree=".supergoal/worktrees/{:02d}".format(index),
            )
            for index in range(11)
        ]
        result = validate_manifest(_manifest("execution", tasks))
        self.assertFalse(result["pass"])
        self.assertIn("tasks may contain at most 10 direct task records", result["problems"])

    def test_binding_canary_accepts_observed_executor_only(self):
        good = {
            "executors": [{
                "id": "canary-1",
                "agent_role": "supergoal_luna_executor",
                "requested_model": "gpt-5.6-luna",
                "requested_reasoning_effort": "xhigh",
                "model": "gpt-5.6-luna",
                "reasoning_effort": "xhigh",
                "evidence": ["UI/runtime observation"],
            }]
        }
        self.assertTrue(validate_binding_canary(good)["pass"])
        bad = copy.deepcopy(good)
        bad["executors"][0]["model"] = "gpt-5.6-sol"
        result = validate_binding_canary(bad)
        self.assertFalse(result["pass"])
        self.assertTrue(any("model does not match" in problem for problem in result["problems"]), result)

    def test_binding_canary_cli_is_machine_checkable(self):
        observation = {
            "executors": [{
                "id": "canary-1",
                "agent_role": "supergoal_luna_executor",
                "requested_model": "gpt-5.6-luna",
                "requested_reasoning_effort": "xhigh",
                "model": "gpt-5.6-luna",
                "reasoning_effort": "xhigh",
                "evidence": ["runtime observation"],
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canary.json"
            path.write_text(json.dumps(observation), encoding="utf-8")
            command = subprocess.run(
                [sys.executable, str(SCRIPT), "--binding-canary", str(path)],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(command.returncode, 0, command.stdout)
            self.assertTrue(json.loads(command.stdout)["pass"])


if __name__ == "__main__":
    unittest.main()
