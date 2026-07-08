#!/usr/bin/env python3
"""SuperGoal SubagentStop hook: enforce agent write scope (EXPERIMENTAL).

Blocks a write-capable cluster agent's turn when it created, modified, or
deleted a `.supergoal/` file outside its declared scope.

Mechanism: content-hash snapshots. Before spawning a write-capable wave the
scheduler runs `python subagent_audit.py --snapshot` (from anywhere in the
repo), which records a SHA-256 per `.supergoal/` file - `tmp/` excluded - into
`.supergoal/tmp/.write-audit-baseline`. When the agent's turn ends this hook
re-snapshots, diffs, and checks every changed path against the agent's
allow-list. Out-of-scope -> {"decision": "block", ...} on stdout; a clean diff
advances the baseline for the next write-capable agent.
`python subagent_audit.py --audit <agent>` runs the identical check from the
command line: the scheduler's manual safety net, and the way to exercise the
logic against a live install.

Why hashes and not `git status --short` (the first revision): in the common
layout `.supergoal/` is untracked, so git collapses the whole tree to one
`?? .supergoal/` line - baseline and post-violation output are identical - and a
content edit to an untracked file never changes status output at all. Hashing
sees content, not tracking state, and needs no git.

The three bulk-writer cluster agents each own exactly one `.supergoal/` document;
`worker` owns none (its real writes are code files outside `.supergoal/`, which
this hook does not audit - the packet's instruction scope and the completion
gates cover those). Reviewers never match this hook; they are read-only.

EXPERIMENTAL: the exact SubagentStop payload shape and the JSON-stdout
requirement were designed from Codex hook documentation, not verified against
a live install. Every failure mode degrades to "do not block" so a payload
mismatch can never wedge a session; until verified, the scheduler's `--audit`
pass after each write-capable wave stays the primary safety net. When the
hook does fire cleanly, it runs the same duplicate S/E-ID scan as `--audit`.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

# `.supergoal/`-relative files each write-capable agent may create or modify.
# `.supergoal/tmp/` is excluded from snapshots entirely, so scratch writes are
# implicitly allowed for everyone.
WRITE_SCOPES = {
    "researcher": {"RESEARCH.md"},
    "designer": {"DESIGN.md"},
    "synthesizer": {"DEBATE.md"},
    "worker": set(),
}

AGENT_TYPE_KEYS = ("agent_type", "subagent_type", "agentType", "subagentType")

BASELINE_REL = Path("tmp") / ".write-audit-baseline"


def find_supergoal(cwd):
    """Walk up from cwd to the git root looking for a .supergoal directory."""
    path = Path(cwd or ".").resolve()
    for candidate in (path, *path.parents):
        supergoal = candidate / ".supergoal"
        if supergoal.is_dir():
            return supergoal
        if (candidate / ".git").exists():
            break
    return None


def get_agent_type(event):
    """Best-effort extraction of the subagent type from an uncertain payload."""
    for key in AGENT_TYPE_KEYS:
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    for parent in ("subagent", "agent"):
        sub = event.get(parent)
        if isinstance(sub, dict):
            value = sub.get("type") or sub.get("name")
            if isinstance(value, str) and value:
                return value
    return None


def snapshot(supergoal):
    """{.supergoal-relative posix path: sha256} for every file.

    tmp/ is excluded (scratch space, open to all writers). archive/ is
    excluded too: no agent may write there anyway, hashing it makes every
    hook fire O(project history), and a baseline taken before archiving
    would mass-false-block the next mission's first agent after Next moves
    the root files.
    """
    out = {}
    for path in sorted(supergoal.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(supergoal).as_posix()
        if rel.startswith(("tmp/", "archive/")):
            continue
        try:
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue  # unreadable file: skip rather than wedge the audit
    return out


def changed_paths(baseline, current):
    """Created, modified, or deleted relative paths versus the baseline."""
    return sorted(
        p for p in set(baseline) | set(current)
        if baseline.get(p) != current.get(p)
    )


def scope_violations(agent_type, baseline, current):
    """Changed `.supergoal/` paths that are outside this agent's write scope."""
    allowed = WRITE_SCOPES.get(agent_type, set())
    return [p for p in changed_paths(baseline, current) if p not in allowed]


def describe_scope(agent_type):
    owned = sorted(WRITE_SCOPES.get(agent_type, set()))
    if not owned:
        return "only .supergoal/tmp/"
    return " + ".join(".supergoal/" + name for name in owned) + " (plus .supergoal/tmp/)"


def read_baseline(supergoal):
    """The stored snapshot dict, or None when absent or unparseable."""
    baseline_file = supergoal / BASELINE_REL
    if not baseline_file.is_file():
        return None
    try:
        data = json.loads(baseline_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_baseline(supergoal, snap):
    baseline_file = supergoal / BASELINE_REL
    try:
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text(
            json.dumps(snap, sort_keys=True, indent=1), encoding="utf-8"
        )
        return True
    except OSError:
        return False


def audit(supergoal, agent_type):
    """(violations, current_snapshot), or (None, None) when no baseline exists."""
    baseline = read_baseline(supergoal)
    if baseline is None:
        return None, None
    current = snapshot(supergoal)
    return scope_violations(agent_type, baseline, current), current


def duplicate_ids(supergoal):
    """S/E IDs defined more than once in RESEARCH.md.

    IDs are the cross-agent access mechanism; a crashed-and-rerun research
    call can mint duplicates, after which citations silently resolve to the
    wrong row. Definitions counted: register rows (`| S001 | ...`) and claim
    headers (`### E001 ...`).
    """
    research = supergoal / "RESEARCH.md"
    if not research.is_file():
        return []
    try:
        text = research.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    seen, dupes = set(), []
    for match in re.finditer(
        r"(?m)^\|\s*(S\d+)\s*\||^###\s+(E\d+)\b", text
    ):
        ident = match.group(1) or match.group(2)
        if ident in seen and ident not in dupes:
            dupes.append(ident)
        seen.add(ident)
    return dupes


def block_reason(agent_type, violations):
    return (
        "SuperGoal write-scope audit: {} changed .supergoal/ files outside its"
        " scope: {}. Allowed: {}. Revert or move those writes; the scheduler"
        " owns BRIEF/PLAN/JOURNAL and every other agent's documents.".format(
            agent_type,
            ", ".join(".supergoal/" + p for p in violations),
            describe_scope(agent_type),
        )
    )


def run_hook():
    """SubagentStop mode: event JSON on stdin, block JSON on stdout."""
    try:
        event = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except (json.JSONDecodeError, ValueError):
        return  # malformed input: never block

    if event.get("stop_hook_active"):
        return

    agent_type = get_agent_type(event)
    if agent_type not in WRITE_SCOPES:
        return  # reviewers, explorer, or an unknown type: nothing to audit

    supergoal = find_supergoal(event.get("cwd", "."))
    if supergoal is None:
        return

    violations, current = audit(supergoal, agent_type)
    if violations is None:
        return  # scheduler took no snapshot; the --audit net covers this wave
    problems = []
    if violations:
        problems.append(block_reason(agent_type, violations))
    # Same duplicate S/E-ID scan as CLI --audit: live SubagentStop must not
    # be a weaker net than the scheduler fallback.
    dupes = duplicate_ids(supergoal)
    if dupes:
        problems.append(
            "duplicate S/E-ID definitions in RESEARCH.md: {} - citations"
            " will resolve to the wrong row; renumber before design"
            " consumes them".format(", ".join(dupes))
        )
    if problems:
        print(json.dumps(
            {"decision": "block", "reason": "; ".join(problems)}
        ))
        return
    write_baseline(supergoal, current)  # clean turn: advance the baseline


def run_cli(argv):
    """--snapshot / --audit <agent> for the scheduler. Nonzero exit on failure."""
    supergoal = find_supergoal(".")
    if supergoal is None:
        print("subagent_audit: no .supergoal/ directory found from cwd", file=sys.stderr)
        return 1

    if argv[0] == "--snapshot":
        snap = snapshot(supergoal)
        if not write_baseline(supergoal, snap):
            print("subagent_audit: could not write baseline", file=sys.stderr)
            return 1
        print("baseline: {} file(s) under {}".format(len(snap), supergoal))
        return 0

    if argv[0] == "--audit" and len(argv) > 1:
        agent_type = argv[1]
        if agent_type not in WRITE_SCOPES:
            print(
                "subagent_audit: unknown agent {!r}; write-capable agents: {}".format(
                    agent_type, ", ".join(sorted(WRITE_SCOPES))
                ),
                file=sys.stderr,
            )
            return 1
        violations, current = audit(supergoal, agent_type)
        if violations is None:
            print("subagent_audit: no baseline; run --snapshot before the wave",
                  file=sys.stderr)
            return 1
        problems = []
        if violations:
            problems.append(block_reason(agent_type, violations))
        dupes = duplicate_ids(supergoal)
        if dupes:
            problems.append(
                "duplicate S/E-ID definitions in RESEARCH.md: {} - citations"
                " will resolve to the wrong row; renumber before design"
                " consumes them".format(", ".join(dupes))
            )
        if problems:
            print("; ".join(problems))
            return 1
        write_baseline(supergoal, current)
        print("write scope clean for {}".format(agent_type))
        return 0

    print("usage: subagent_audit.py [--snapshot | --audit <agent>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(run_cli(sys.argv[1:]))
    run_hook()
