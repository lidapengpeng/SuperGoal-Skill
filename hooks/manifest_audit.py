#!/usr/bin/env python3
"""Validate SuperGoal's portable run manifest and optional binding canary.

This tool intentionally validates only declared, user-retained JSON evidence.
It does not read Codex's private SQLite files, rollout logs, or hook payload
schemas.  A PASS means the manifest is internally complete; it is not a claim
that the host runtime independently enforced the declarations.
"""

import argparse
import json
import re
import sys
from pathlib import PurePosixPath, Path


EXECUTOR_ROLE = "supergoal_luna_executor"
RESEARCHER_ROLE = "supergoal_researcher"
REVIEWER_ROLE = "supergoal_reviewer"
TASK_ROLES = {EXECUTOR_ROLE, RESEARCHER_ROLE}
PHASES = {"plan", "execution", "complete"}
TASK_STATUSES = {"planned", "running", "complete", "skipped", "blocked"}
RESERVED_OWNED_ROOTS = {".git", ".supergoal"}
SHA256 = re.compile(r"sha256:[0-9a-f]{64}", re.I)
SNAPSHOT_ID = re.compile(r"(?:sha256:|git:)?[0-9a-f]{40,64}", re.I)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _text_list(value):
    return isinstance(value, list) and all(_text(item) for item in value)


def _mapping(value):
    return isinstance(value, dict)


def _path(value):
    """Return a safe portable relative path, or False.

    The manifest needs names that can be compared across worktrees, rather
    than host-specific absolute paths.  A trailing slash is normalized away
    by the caller before comparison.
    """
    if not _text(value) or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and path != PurePosixPath(".") and ".." not in path.parts


def _paths_overlap(left, right):
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _review_problems(value, label):
    if not _mapping(value):
        return ["{} must be an object".format(label)]
    problems = []
    if value.get("role") != REVIEWER_ROLE:
        problems.append("{} must name {}".format(label, REVIEWER_ROLE))
    if value.get("verdict") != "PASS":
        problems.append("{} verdict must be PASS".format(label))
    if not _text_list(value.get("evidence")) or not value["evidence"]:
        problems.append("{} needs non-empty evidence".format(label))
    return problems


def _runtime_problems(value, task_id, role, model, effort):
    if not _mapping(value):
        return ["task {} completed without runtime binding evidence".format(task_id)]
    problems = []
    if value.get("agent_role") != role:
        problems.append("task {} runtime agent_role does not match role".format(task_id))
    if value.get("model") != model:
        problems.append("task {} runtime model does not match requested model".format(task_id))
    if value.get("reasoning_effort") != effort:
        problems.append("task {} runtime reasoning_effort does not match requested reasoning_effort".format(task_id))
    if not _text_list(value.get("evidence")) or not value["evidence"]:
        problems.append("task {} runtime needs non-empty evidence".format(task_id))
    return problems


def _task_problems(task, seen_ids, seen_owned, writers):
    """Validate one task and return `(problems, normalized_task)`.

    `normalized_task` contains only fields needed for cross-task checks, so
    the main validator never trusts parsing side effects from malformed input.
    """
    if not _mapping(task):
        return ["every task must be an object"], None

    problems = []
    task_id = task.get("id")
    if not isinstance(task_id, str) or not IDENTIFIER.fullmatch(task_id):
        problems.append("task has an invalid id")
        task_id = "<invalid>"
    elif task_id in seen_ids:
        problems.append("duplicate task id: {}".format(task_id))
    else:
        seen_ids.add(task_id)

    if task.get("parent") != "controller":
        problems.append("task {} must have parent=controller; nested parents are forbidden".format(task_id))
    role = task.get("role")
    if role not in TASK_ROLES:
        problems.append("task {} has an unknown role".format(task_id))
    model = task.get("model")
    if not _text(model):
        problems.append("task {} needs a model".format(task_id))
        model = ""
    effort = task.get("reasoning_effort")
    if not _text(effort):
        problems.append("task {} needs reasoning_effort".format(task_id))
        effort = ""
    if not isinstance(task.get("base_sha"), str) or not SNAPSHOT_ID.fullmatch(task["base_sha"]):
        problems.append("task {} has no valid base_sha".format(task_id))

    dependencies = task.get("depends_on")
    if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
        problems.append("task {} depends_on must be a string list".format(task_id))
        dependencies = []
    elif len(dependencies) != len(set(dependencies)):
        problems.append("task {} has duplicate dependencies".format(task_id))
    if task_id in dependencies:
        problems.append("task {} may not depend on itself".format(task_id))

    writes = task.get("writes")
    if not isinstance(writes, bool):
        problems.append("task {} writes must be boolean".format(task_id))
        writes = False
    if role == EXECUTOR_ROLE and writes is not True:
        problems.append("executor task {} must declare writes=true".format(task_id))
    if role == RESEARCHER_ROLE and writes is not False:
        problems.append("research task {} must declare writes=false".format(task_id))

    owned = task.get("owned_paths")
    if not isinstance(owned, list) or not all(_path(item) for item in owned):
        problems.append("task {} owned_paths must contain safe relative paths".format(task_id))
        owned = []
    else:
        owned = [str(PurePosixPath(item.rstrip("/"))) for item in owned]
        if len(owned) != len(set(owned)):
            problems.append("task {} repeats an owned path".format(task_id))
        if any(PurePosixPath(item).parts[0] in RESERVED_OWNED_ROOTS for item in owned):
            problems.append("task {} may not own controller state".format(task_id))
    forbidden = task.get("forbidden_paths")
    if not isinstance(forbidden, list) or not all(_path(item) for item in forbidden):
        problems.append("task {} forbidden_paths must contain safe relative paths".format(task_id))
        forbidden = []
    else:
        forbidden = [str(PurePosixPath(item.rstrip("/"))) for item in forbidden]
        if len(forbidden) != len(set(forbidden)):
            problems.append("task {} repeats a forbidden path".format(task_id))
    for left in owned:
        for right in forbidden:
            if _paths_overlap(left, right):
                problems.append("task {} owns a forbidden path: {} / {}".format(task_id, left, right))
    for path, owner in seen_owned:
        for owned_path in owned:
            if _paths_overlap(path, owned_path):
                problems.append("owned path overlaps: {} ({}) and {} ({})".format(path, owner, owned_path, task_id))
    seen_owned.extend((path, task_id) for path in owned)

    worktree = task.get("worktree")
    if writes:
        if not _text(worktree):
            problems.append("writer task {} needs a worktree".format(task_id))
        elif worktree in writers:
            problems.append("writer tasks {} and {} share worktree {}".format(writers[worktree], task_id, worktree))
        else:
            writers[worktree] = task_id
        if not owned:
            problems.append("writer task {} needs at least one owned path".format(task_id))
    else:
        if owned:
            problems.append("read-only task {} may not own paths".format(task_id))
        if worktree not in (None, ""):
            problems.append("read-only task {} must use worktree null or empty".format(task_id))

    verify = task.get("verify")
    if not _text_list(verify) or not verify:
        problems.append("task {} needs at least one verify item".format(task_id))
    status = task.get("status")
    if status not in TASK_STATUSES:
        problems.append("task {} has an invalid status".format(task_id))
    elif status == "complete":
        if not _text(task.get("result")):
            problems.append("completed task {} needs a result".format(task_id))
        if not _text_list(task.get("evidence")) or not task["evidence"]:
            problems.append("completed task {} needs evidence".format(task_id))
        if not isinstance(task.get("output_sha256"), str) or not SHA256.fullmatch(task["output_sha256"]):
            problems.append("completed task {} needs output_sha256".format(task_id))
        if role in TASK_ROLES:
            problems.extend(_runtime_problems(task.get("runtime"), task_id, role, model, effort))
    elif status in {"blocked", "skipped"} and not _text(task.get("result")):
        problems.append("{} task {} needs a result/reason".format(status, task_id))

    return problems, {
        "id": task_id,
        "depends_on": dependencies,
        "status": status,
        "writes": writes,
    }


def _dag_problems(tasks):
    by_id = {task["id"]: task for task in tasks if task is not None}
    problems = []
    for task in tasks:
        if task is None:
            continue
        for dependency in task["depends_on"]:
            if dependency not in by_id:
                problems.append("task {} depends on unknown task {}".format(task["id"], dependency))
            elif task["status"] in {"running", "complete"} and by_id[dependency]["status"] != "complete":
                problems.append("{} task {} has unfinished dependency {}".format(task["status"], task["id"], dependency))

    visiting, visited = set(), set()

    def visit(task_id):
        if task_id in visited:
            return
        if task_id in visiting:
            problems.append("task dependency graph contains a cycle at {}".format(task_id))
            return
        visiting.add(task_id)
        for dependency in by_id.get(task_id, {}).get("depends_on", []):
            if dependency in by_id:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(by_id):
        visit(task_id)
    return problems


def validate_manifest(manifest):
    """Return a stable JSON-safe validation result for a manifest object."""
    problems = []
    if not _mapping(manifest):
        return {"pass": False, "problems": ["manifest root must be an object"]}

    if manifest.get("version") != 1:
        problems.append("version must be 1")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not IDENTIFIER.fullmatch(run_id):
        problems.append("run_id is invalid")
    if not isinstance(manifest.get("base_sha"), str) or not SNAPSHOT_ID.fullmatch(manifest["base_sha"]):
        problems.append("base_sha is required and must be a snapshot identifier")
    phase = manifest.get("phase")
    if phase not in PHASES:
        problems.append("phase must be plan, execution, or complete")

    controller = manifest.get("controller")
    if not _mapping(controller):
        problems.append("controller must be an object")
    else:
        if not _text(controller.get("model")):
            problems.append("controller needs a model")
        if not _text(controller.get("reasoning_effort")):
            problems.append("controller needs reasoning_effort")
        if not _text_list(controller.get("evidence")) or not controller["evidence"]:
            problems.append("controller needs non-empty evidence")

    plan = manifest.get("plan")
    if not _mapping(plan):
        problems.append("plan must be an object")
    else:
        problems.extend(_review_problems(plan.get("review"), "plan review"))

    raw_tasks = manifest.get("tasks")
    if not isinstance(raw_tasks, list):
        problems.append("tasks must be a list")
        raw_tasks = []
    if len(raw_tasks) > 10:
        problems.append("tasks may contain at most 10 direct task records")
    seen_ids, seen_owned, writers, tasks = set(), [], {}, []
    for task in raw_tasks:
        task_problems, normalized = _task_problems(task, seen_ids, seen_owned, writers)
        problems.extend(task_problems)
        tasks.append(normalized)
    problems.extend(_dag_problems(tasks))

    research = manifest.get("research")
    if research is not None:
        if not _mapping(research) or research.get("status") not in {"not_needed", "pending", "complete"}:
            problems.append("research status must be not_needed, pending, or complete")
        elif research.get("status") == "complete" and (not _text_list(research.get("evidence")) or not research["evidence"]):
            problems.append("completed research needs evidence")
        elif phase == "complete" and research.get("status") == "pending":
            problems.append("complete manifest cannot leave research pending")

    integration = manifest.get("integration")
    if integration is not None:
        if not _mapping(integration) or integration.get("status") not in {"pending", "complete"}:
            problems.append("integration status must be pending or complete")
        elif integration.get("status") == "complete" and (not _text_list(integration.get("evidence")) or not integration["evidence"]):
            problems.append("completed integration needs evidence")

    if phase == "complete":
        if any(task is None or task["status"] not in {"complete", "skipped"} for task in tasks):
            problems.append("complete manifest has non-terminal tasks")
        if not _mapping(integration) or integration.get("status") != "complete":
            problems.append("complete manifest needs completed integration")
        problems.extend(_review_problems(manifest.get("review"), "final independent review"))
        final_verification = manifest.get("final_verification")
        if not _mapping(final_verification):
            problems.append("complete manifest needs final_verification")
        else:
            if final_verification.get("status") != "PASS":
                problems.append("final_verification status must be PASS")
            if not _text_list(final_verification.get("evidence")) or not final_verification["evidence"]:
                problems.append("final_verification needs evidence")

    summary = {
        "phase": phase,
        "task_count": len(raw_tasks),
        "completed_task_count": sum(task is not None and task["status"] == "complete" for task in tasks),
        "writer_count": sum(task is not None and task["writes"] for task in tasks),
    }
    return {"pass": not problems, "problems": problems, "summary": summary}


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, ["manifest not found: {}".format(path)]
    except (OSError, UnicodeDecodeError) as error:
        return None, ["could not read {}: {}".format(path, error)]
    except json.JSONDecodeError as error:
        return None, ["invalid JSON in {}: line {} column {}".format(path, error.lineno, error.colno)]


def audit_manifest(path):
    manifest, problems = load_json(path)
    if problems:
        return {"pass": False, "problems": problems}
    return validate_manifest(manifest)


def validate_binding_canary(observation):
    """Validate public/manual runtime observations for one or more executors.

    Input is intentionally small and generic so it can be populated from any
    supported UI/API observation without coupling this plugin to a private
    Codex persistence format.
    """
    if not _mapping(observation):
        return {"pass": False, "problems": ["binding canary root must be an object"]}
    executors = observation.get("executors")
    if not isinstance(executors, list) or not executors:
        return {"pass": False, "problems": ["binding canary needs at least one executor observation"]}
    problems, seen = [], set()
    for item in executors:
        if not _mapping(item):
            problems.append("every executor observation must be an object")
            continue
        task_id = item.get("id")
        if not isinstance(task_id, str) or not IDENTIFIER.fullmatch(task_id):
            problems.append("executor observation has invalid id")
        elif task_id in seen:
            problems.append("duplicate executor observation id: {}".format(task_id))
        else:
            seen.add(task_id)
        if item.get("agent_role") != EXECUTOR_ROLE:
            problems.append("executor {} agent_role is not {}".format(task_id, EXECUTOR_ROLE))
        expected_model = item.get("requested_model")
        expected_effort = item.get("requested_reasoning_effort")
        if not _text(expected_model):
            problems.append("executor {} needs requested_model".format(task_id))
        elif item.get("model") != expected_model:
            problems.append("executor {} model does not match requested_model".format(task_id))
        if not _text(expected_effort):
            problems.append("executor {} needs requested_reasoning_effort".format(task_id))
        elif item.get("reasoning_effort") != expected_effort:
            problems.append("executor {} reasoning_effort does not match requested_reasoning_effort".format(task_id))
        if not _text_list(item.get("evidence")) or not item["evidence"]:
            problems.append("executor {} needs observation evidence".format(task_id))
    return {"pass": not problems, "problems": problems, "executor_count": len(executors)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=".supergoal/run_manifest.json", help="manifest path")
    parser.add_argument("--binding-canary", metavar="OBSERVATION_JSON", help="validate supplied executor runtime observations")
    args = parser.parse_args(argv)
    if args.binding_canary:
        observation, problems = load_json(args.binding_canary)
        result = {"pass": False, "problems": problems} if problems else validate_binding_canary(observation)
    else:
        result = audit_manifest(args.manifest)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
