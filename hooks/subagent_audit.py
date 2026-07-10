#!/usr/bin/env python3
"""Experimental state-write advisory for SuperGoal's named subagent roles.

All three named roles are prohibited from changing durable ``.supergoal``
state.  The controller is the sole manifest writer; executor code writes are
isolated in task worktrees and are declared in ``run_manifest.json`` instead.
``.supergoal/tmp/`` and ``.supergoal/worktrees/`` are intentionally scratch
surfaces, not durable controller state.

The Start/Stop payload shape is surface-dependent, so this tool is deliberately
an advisory guard, not a claim of sandbox enforcement.  It stores a hash
baseline outside the repository and compares durable state after a role stops.
It does not inspect Codex private SQLite files or rollout transcripts.
"""

import hashlib
import json
import os
import sys
from pathlib import Path


WRITE_SCOPES = {
    "supergoal_luna_executor": set(),
    "supergoal_researcher": set(),
    "supergoal_reviewer": set(),
}
AGENT_TYPE_KEYS = ("agent_type", "subagent_type", "agentType", "subagentType")
AGENT_ID_KEYS = ("agent_id", "subagent_id", "task_id", "thread_id", "agentId", "taskId")
AUDIT_ROOT = Path.home() / ".codex" / "supergoal-audit"


def find_supergoal(cwd):
    path = Path(cwd or ".").resolve()
    for candidate in (path, *path.parents):
        supergoal = candidate / ".supergoal"
        if supergoal.is_dir():
            return supergoal
        if (candidate / ".git").exists():
            break
    return None


def get_agent_type(event):
    for key in AGENT_TYPE_KEYS:
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    for parent in ("subagent", "agent"):
        value = event.get(parent)
        if isinstance(value, dict):
            name = value.get("type") or value.get("name")
            if isinstance(name, str) and name:
                return name
    return None


def get_agent_id(event):
    for key in AGENT_ID_KEYS:
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    for parent in ("subagent", "agent"):
        value = event.get(parent)
        if isinstance(value, dict):
            for key in ("id", "task_id", "thread_id"):
                task_id = value.get(key)
                if isinstance(task_id, str) and task_id:
                    return task_id
    return None


def snapshot(supergoal):
    """Map durable controller state to hashes; exclude scratch/worktrees."""
    result = {}
    for path in sorted(Path(supergoal).rglob("*")):
        relative = path.relative_to(supergoal).as_posix()
        if relative.startswith(("tmp/", "worktrees/")):
            continue
        try:
            if path.is_symlink():
                result[relative] = "SYMLINK:" + os.readlink(path)
            elif path.is_file():
                result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            result[relative] = "UNREADABLE:" + type(error).__name__
    return result


def changed_paths(baseline, current):
    return sorted(path for path in set(baseline) | set(current) if baseline.get(path) != current.get(path))


def scope_violations(agent_type, baseline, current):
    allowed = WRITE_SCOPES.get(agent_type, set())
    return [path for path in changed_paths(baseline, current) if path not in allowed]


def describe_scope(agent_type):
    if agent_type in WRITE_SCOPES:
        return "no durable .supergoal writes; executor code writes belong only in its declared worktree"
    return "unmatched role"


def baseline_path(supergoal, agent_type, task_id, audit_root=None):
    root = Path(audit_root) if audit_root is not None else AUDIT_ROOT
    repo_key = hashlib.sha256(str(Path(supergoal).resolve()).encode("utf-8")).hexdigest()[:24]
    task_key = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:24]
    return root / repo_key / (agent_type + "-" + task_key + ".json")


def read_baseline(supergoal, agent_type, task_id, audit_root=None):
    path = baseline_path(supergoal, agent_type, task_id, audit_root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or value.get("agent_type") != agent_type or value.get("task_id") != task_id:
        return None
    return value.get("snapshot") if isinstance(value.get("snapshot"), dict) else None


def write_baseline(supergoal, agent_type, task_id, state, audit_root=None):
    path = baseline_path(supergoal, agent_type, task_id, audit_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"agent_type": agent_type, "task_id": task_id, "snapshot": state}, sort_keys=True), encoding="utf-8")
        return True
    except OSError:
        return False


def audit(supergoal, agent_type, task_id, audit_root=None):
    baseline = read_baseline(supergoal, agent_type, task_id, audit_root)
    if baseline is None:
        return None, None
    current = snapshot(supergoal)
    violations = scope_violations(agent_type, baseline, current)
    violations.extend(
        "{} (unsafe durable entry)".format(path)
        for path, digest in current.items()
        if digest.startswith(("SYMLINK:", "UNREADABLE:"))
    )
    return sorted(set(violations)), current


def block_reason(agent_type, violations):
    return (
        "SuperGoal state-write advisory: {} changed durable .supergoal files "
        "outside its declared scope: {}. Allowed: {}. The controller owns "
        "run_manifest.json and mission state."
    ).format(agent_type, ", ".join(".supergoal/" + path for path in violations), describe_scope(agent_type))


def hook_decision(event, phase, audit_root=None):
    agent_type = get_agent_type(event)
    if agent_type not in WRITE_SCOPES:
        return None
    supergoal = find_supergoal(event.get("cwd", "."))
    if supergoal is None:
        return None
    task_id = get_agent_id(event)
    if task_id is None:
        return {"decision": "block", "reason": "SuperGoal state-write advisory: recognized role {} has no runtime task ID.".format(agent_type)}
    if phase == "start":
        if write_baseline(supergoal, agent_type, task_id, snapshot(supergoal), audit_root):
            return None
        return {"decision": "block", "reason": "SuperGoal state-write advisory: could not create baseline for {}.".format(task_id)}
    violations, _ = audit(supergoal, agent_type, task_id, audit_root)
    if violations is None:
        return {"decision": "block", "reason": "SuperGoal state-write advisory: no baseline exists for {}.".format(task_id)}
    return {"decision": "block", "reason": block_reason(agent_type, violations)} if violations else None


def run_hook(phase):
    try:
        event = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except (json.JSONDecodeError, ValueError):
        return
    decision = hook_decision(event, phase)
    if decision:
        print(json.dumps(decision, ensure_ascii=False, sort_keys=True))


def run_cli(argv):
    if len(argv) != 3 or argv[0] not in {"--snapshot", "--audit"}:
        print("usage: subagent_audit.py [--snapshot|--audit] <role> <task-id>", file=sys.stderr)
        return 2
    mode, agent_type, task_id = argv
    if agent_type not in WRITE_SCOPES:
        print("subagent_audit: unknown role {!r}".format(agent_type), file=sys.stderr)
        return 1
    supergoal = find_supergoal(".")
    if supergoal is None:
        print("subagent_audit: no .supergoal directory found", file=sys.stderr)
        return 1
    if mode == "--snapshot":
        if not write_baseline(supergoal, agent_type, task_id, snapshot(supergoal)):
            print("subagent_audit: could not write baseline", file=sys.stderr)
            return 1
        print("state baseline recorded for {} {}".format(agent_type, task_id))
        return 0
    violations, _ = audit(supergoal, agent_type, task_id)
    if violations is None:
        print("subagent_audit: no baseline; run --snapshot first", file=sys.stderr)
        return 1
    if violations:
        print(block_reason(agent_type, violations))
        return 1
    print("state scope clean for {} {}".format(agent_type, task_id))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--hook-start":
        run_hook("start")
    elif len(sys.argv) > 1 and sys.argv[1] == "--hook-stop":
        run_hook("stop")
    elif len(sys.argv) > 1:
        sys.exit(run_cli(sys.argv[1:]))
    else:
        run_hook("stop")
