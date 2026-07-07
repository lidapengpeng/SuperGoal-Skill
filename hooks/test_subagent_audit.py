#!/usr/bin/env python3
"""Self-check for subagent_audit.py. Run: python hooks/test_subagent_audit.py

Assert-based, no framework. Covers the snapshot/diff/scope logic on real temp
files; the stdin-event plumbing is exercised by the end-to-end run documented
in the hook's docstring. Fails loudly if an agent's allow-list, the hash diff,
or the payload parsing drifts.

Regression anchor: the first revision diffed `git status --short`, which is
blind when `.supergoal/` is untracked (the whole tree collapses to one `??`
line and content edits never change status output). The cross-write and
content-edit cases below fail on any mechanism with that blind spot.
"""
import tempfile
from pathlib import Path

from subagent_audit import (
    WRITE_SCOPES,
    audit,
    changed_paths,
    describe_scope,
    duplicate_ids,
    find_supergoal,
    get_agent_type,
    read_baseline,
    scope_violations,
    snapshot,
    write_baseline,
)

with tempfile.TemporaryDirectory() as _d:
    dp = Path(_d) / ".supergoal"
    (dp / "tmp").mkdir(parents=True)
    (dp / "DESIGN.md").write_text("v1", encoding="utf-8")
    (dp / "tmp" / "scratch.txt").write_text("junk", encoding="utf-8")

    # --- snapshot: hashes files, excludes tmp/ and archive/ ---------------
    # hardening: archive/ exclusion kills the post-archive mass-false-block and the
    # O(project-history) hashing cost per hook fire.
    (dp / "archive" / "20260101-old").mkdir(parents=True)
    (dp / "archive" / "20260101-old" / "JOURNAL.md").write_text(
        "old mission", encoding="utf-8"
    )
    snap = snapshot(dp)
    assert set(snap) == {"DESIGN.md"}, \
        f"tmp/ and archive/ must be excluded, got {set(snap)}"
    assert len(snap["DESIGN.md"]) == 64, "sha256 hex digest expected"

    # --- changed_paths: create / modify / delete all count ---------------
    (dp / "DEBATE.md").write_text("R1", encoding="utf-8")
    assert changed_paths(snap, snapshot(dp)) == ["DEBATE.md"], "creation detected"

    base2 = snapshot(dp)
    (dp / "DEBATE.md").write_text("R1 rewritten", encoding="utf-8")
    assert changed_paths(base2, snapshot(dp)) == ["DEBATE.md"], \
        "content edit detected (the git-status revision missed this)"

    base3 = snapshot(dp)
    (dp / "DEBATE.md").unlink()
    assert changed_paths(base3, snapshot(dp)) == ["DEBATE.md"], "deletion detected"

    # --- scope_violations per agent ---------------------------------------
    base = snapshot(dp)  # {DESIGN.md} on disk
    (dp / "DESIGN.md").write_text("v2", encoding="utf-8")
    cur = snapshot(dp)
    assert scope_violations("designer", base, cur) == [], \
        "designer editing DESIGN.md is clean"
    (dp / "RESEARCH.md").write_text("planted", encoding="utf-8")
    cur = snapshot(dp)
    assert scope_violations("designer", base, cur) == ["RESEARCH.md"], \
        "designer creating RESEARCH.md is a violation"
    assert scope_violations("researcher", base, cur) == ["DESIGN.md"], \
        "researcher is charged with the DESIGN.md change, not RESEARCH.md"
    # worker owns no .supergoal document at all
    assert scope_violations("worker", base, cur) == ["DESIGN.md", "RESEARCH.md"]
    assert scope_violations("researcher", {}, {"RESEARCH.md": "x"}) == []
    assert scope_violations("synthesizer", {}, {"DEBATE.md": "x"}) == []

    # --- baseline roundtrip + audit ---------------------------------------
    assert read_baseline(dp) is None, "no baseline written yet"
    assert audit(dp, "designer") == (None, None), "no baseline -> no audit"
    assert write_baseline(dp, base)
    assert read_baseline(dp) == base, "baseline roundtrips"
    violations, current = audit(dp, "designer")
    assert violations == ["RESEARCH.md"] and current == cur, "audit finds the plant"
    # malformed baseline degrades to no-audit, never a crash or a block
    (dp / "tmp" / ".write-audit-baseline").write_text("{not json", encoding="utf-8")
    assert read_baseline(dp) is None and audit(dp, "designer") == (None, None)

    # --- hardening: duplicate S/E-ID detection ------------------------------------
    assert duplicate_ids(dp) == [], "no RESEARCH.md -> no duplicates"
    (dp / "RESEARCH.md").write_text(
        "## RESEARCH CONTRACT 2026-07-07\n"
        "| S001 | 2026-07-01 | F1 | a | u | high | current | read | n |\n"
        "| S002 | 2026-07-02 | F2 | b | u | high | current | read | n |\n"
        "## Claims\n### E001 (Q1)\n- claim: x\n### E002 (Q1)\n- claim: y\n",
        encoding="utf-8",
    )
    assert duplicate_ids(dp) == [], "unique IDs are clean"
    (dp / "RESEARCH.md").write_text(
        "| S001 | ... |\n| S002 | ... |\n| S001 | rerun minted again |\n"
        "## Claims\n### E001 (Q1)\n### E001 (Q2)\n",
        encoding="utf-8",
    )
    dupes = duplicate_ids(dp)
    assert dupes == ["S001", "E001"], f"both duplicate kinds found, got {dupes}"

# --- get_agent_type: tolerate several payload shapes ----------------------
assert get_agent_type({"agent_type": "designer"}) == "designer"
assert get_agent_type({"subagent_type": "researcher"}) == "researcher"
assert get_agent_type({"subagent": {"name": "verifier"}}) == "verifier"
assert get_agent_type({"agent": {"type": "worker"}}) == "worker"
assert get_agent_type({"nothing": 1}) is None

# --- describe_scope --------------------------------------------------------
assert "DESIGN.md" in describe_scope("designer")
assert describe_scope("worker") == "only .supergoal/tmp/"

# --- roster sanity: matches the SubagentStop matcher in hooks.json --------
assert set(WRITE_SCOPES) == {
    "researcher", "designer", "synthesizer", "worker"
}, "write-capable roster must match the SubagentStop matcher"

# --- find_supergoal -------------------------------------------------------
with tempfile.TemporaryDirectory() as _d:
    root = Path(_d)
    sg = root / ".supergoal"
    nested = root / "src" / "pkg"
    sg.mkdir()
    nested.mkdir(parents=True)
    assert find_supergoal(nested) == sg, "walk up to the .supergoal state dir"

print("subagent_audit self-check: all assertions passed")
