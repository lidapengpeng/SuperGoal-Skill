#!/usr/bin/env python3
"""One-stop SuperGoal completion advisory backed by ``run_manifest.json``.

The hook checks only portable state retained in ``.supergoal/run_manifest.json``.
It deliberately does not inspect Codex SQLite state, rollout transcripts, or
undocumented hook payload fields.  Consequently a block is an advisory that
the declared completion contract is incomplete, not proof that a host runtime
prevented a side effect.  ``stop_hook_active`` suppresses a repeat warning.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from manifest_audit import audit_manifest


MANIFEST_NAME = "run_manifest.json"
MAX_PROBLEMS = 5


def find_supergoal(cwd):
    """Find the nearest ``.supergoal`` directory without escaping a git root."""
    path = Path(cwd or ".").resolve()
    for candidate in (path, *path.parents):
        supergoal = candidate / ".supergoal"
        if supergoal.is_dir():
            return supergoal
        if (candidate / ".git").exists():
            break
    return None


def _active_without_manifest(supergoal):
    """Avoid nudging an untouched state directory, but protect active plans."""
    plan = supergoal / "PLAN.md"
    try:
        return plan.is_file() and bool(plan.read_text(encoding="utf-8", errors="replace").strip())
    except OSError:
        return False


def workspace_snapshot_id(supergoal):
    """Portable SHA-256 of workspace files outside ``.supergoal`` and ``.git``.

    This utility remains available for controllers that want a base snapshot;
    validation checks only the declared snapshot identifiers and never treats
    this digest as an undocumented runtime trace.
    """
    root = Path(supergoal).resolve().parent
    digest = hashlib.sha256()
    paths = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith((".supergoal/", ".git/")):
            continue
        paths.append((relative, path))
    for relative, path in sorted(paths):
        digest.update(relative.encode("utf-8", errors="surrogateescape") + b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"UNREADABLE")
    return "sha256:" + digest.hexdigest()


def design_draft_digest(design_text):
    """Compatibility helper for existing journal templates."""
    return "sha256:" + hashlib.sha256(design_text.encode("utf-8")).hexdigest()


def manifest_path(supergoal):
    return Path(supergoal) / MANIFEST_NAME


def completion_problems(supergoal):
    """Return declared-contract failures, including non-complete phases."""
    path = manifest_path(supergoal)
    if not path.is_file():
        return ["{} is missing; completion status cannot be audited".format(MANIFEST_NAME)]
    result = audit_manifest(path)
    problems = list(result.get("problems") or [])
    if not problems and result.get("summary", {}).get("phase") != "complete":
        problems.append("manifest phase is {}, not complete".format(result["summary"].get("phase")))
    return problems


def hook_decision(event):
    """Return a Codex-style advisory decision, or ``None`` when clear."""
    if not isinstance(event, dict) or event.get("stop_hook_active"):
        return None
    supergoal = find_supergoal(event.get("cwd", "."))
    if supergoal is None:
        return None
    path = manifest_path(supergoal)
    if not path.exists() and not _active_without_manifest(supergoal):
        return None
    problems = completion_problems(supergoal)
    if not problems:
        return None
    shown = "; ".join(problems[:MAX_PROBLEMS])
    if len(problems) > MAX_PROBLEMS:
        shown += "; and {} more".format(len(problems) - MAX_PROBLEMS)
    return {
        "decision": "block",
        "reason": (
            "SuperGoal completion advisory: declared work is not ready to "
            "close: {}. This is a one-stop reminder; verify the manifest "
            "and resume or end the session deliberately."
        ).format(shown),
    }


def _print_audit(path):
    result = audit_manifest(path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["pass"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-manifest", action="store_true", help="validate the portable manifest")
    parser.add_argument("--manifest", help="manifest path for --check-manifest")
    parser.add_argument("--snapshot-id", action="store_true", help="print a portable workspace snapshot digest")
    parser.add_argument("--design-digest", action="store_true", help="print a digest of DESIGN.md")
    args = parser.parse_args(argv)

    if args.check_manifest:
        if args.manifest:
            return _print_audit(args.manifest)
        supergoal = find_supergoal(".")
        if supergoal is None:
            print("stop_audit: no .supergoal directory found", file=sys.stderr)
            return 1
        return _print_audit(manifest_path(supergoal))
    if args.snapshot_id or args.design_digest:
        supergoal = find_supergoal(".")
        if supergoal is None:
            print("stop_audit: no .supergoal directory found", file=sys.stderr)
            return 1
        if args.snapshot_id:
            print(workspace_snapshot_id(supergoal))
        else:
            design = supergoal / "DESIGN.md"
            try:
                print(design_draft_digest(design.read_text(encoding="utf-8")))
            except OSError:
                print("stop_audit: DESIGN.md is missing", file=sys.stderr)
                return 1
        return 0

    try:
        event = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except (json.JSONDecodeError, ValueError):
        return 0
    decision = hook_decision(event)
    if decision:
        print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
