#!/usr/bin/env python3
"""Self-check for stop_audit.py. Run: python hooks/test_stop_audit.py

Assert-based, no framework. Fails loudly if the hook's ledger-audit logic
drifts - especially the header-only SG matching that keeps body mentions
(plan-gate notes, "next step: SG3") from validating another subgoal's box.
"""
import tempfile
from pathlib import Path

from stop_audit import (
    journal_sections,
    has_pass,
    plan_problems,
    pending_runs,
    design_inspection_problems,
    stale_final_gate_problems,
)

JOURNAL = """# JOURNAL

## PLAN GATE 2026-07-05
- plan-review: GO - criterion checkable; riskiest first is SG2

## C1 2026-07-05 SG1
- design: hypothesis
- observe: exit 0
- reason: supported; next step: SG3
- review: PASS - reviewer, deterministic green

## C2 2026-07-05 SG2
- reason: refuted
- review: FAIL - counterexample: empty input crashes

## FINAL GATE 2026-07-05
- review: PASS - plan, ledger, diff audited
"""
SECTIONS = journal_sections(JOURNAL)

# --- has_pass: header-only matching -------------------------------------
assert has_pass(SECTIONS, r"\bSG1\b"), "SG1 header + review: PASS must pass"
assert not has_pass(SECTIONS, r"\bSG2\b"), "review: FAIL must not pass"
# SG3 appears only in C1's body ("next step: SG3") which logs a PASS:
assert not has_pass(SECTIONS, r"\bSG3\b"), "body mention must not validate SG3"
assert has_pass(SECTIONS, r"FINAL\s+GATE"), "FINAL GATE section must pass"
# SG1 must not prefix-match SG12:
assert not has_pass(journal_sections("## C1 x SG12\n- review: PASS"), r"\bSG1\b")

# --- anti-gaming: anchored PASS, multi-SG headers ----------------------
# Quoted prose containing "review: PASS" - e.g. the hook's own block message
# pasted into a cycle entry - must never validate a box:
quoted = journal_sections(
    "## C1 2026-07-07 SG1\n"
    "- observe: hook said \"so every checked box has its 'review: PASS' in\"\n"
    "- reason: the audit wants review: PASS logged\n"
)
assert not has_pass(quoted, r"\bSG1\b"), "quoted PASS text must not validate"
# The prescribed list-item form still validates (with or without indent):
assert has_pass(journal_sections("## C1 SG1\n- review: PASS - ok\n"), r"\bSG1\b")
assert has_pass(journal_sections("## C1 SG1\n  - review: PASS - ok\n"), r"\bSG1\b")
# A header naming more than one SG validates none of them:
multi = journal_sections("## C9 2026-07-07 SG1 SG2\n- review: PASS - both\n")
assert not has_pass(multi, r"\bSG1\b"), "multi-SG header must validate nothing"
assert not has_pass(multi, r"\bSG2\b"), "multi-SG header must validate nothing"

# --- plan_problems -------------------------------------------------------
plan_ok = "- [x] SG1: a | verify: `t` | done-when: d\n- [x] FINAL: gate PASS\n"
assert plan_problems(plan_ok, SECTIONS) == [], "clean plan must report nothing"

plan_bad = (
    "- [ ] SG9: open | verify: `t` | done-when: d\n"   # unchecked -> problem
    "- [x] SG2: b | verify: `t` | done-when: d\n"      # FAIL verdict -> problem
    "- [x] SG3: c | verify: `t` | done-when: d\n"      # body-only mention -> problem
    "- [!] SG4: blocked: upstream outage\n"            # escape hatch -> ignored
    "- [x] FINAL: gate PASS\n"
)
problems = plan_problems(plan_bad, SECTIONS)
text = " | ".join(problems)
assert "SG9" in text and "unchecked" in text
assert "SG2" in text and "SG3" in text, "unreviewed checked boxes must be named"
assert "SG4" not in text, "- [!] items are exempt"

missing_final = plan_problems("- [x] SG1: a\n", SECTIONS)
assert any("FINAL" in p for p in missing_final), "plan without FINAL line must block"

final_no_gate = plan_problems("- [x] FINAL: gate\n", journal_sections("## C1 x SG1\n- review: PASS"))
assert any("FINAL GATE" in p for p in final_no_gate), "checked FINAL needs its section"

# --- anti-gaming: '- [!] FINAL' has no legitimate blocked state --------------------
bang_final = plan_problems("- [x] SG1: a\n- [!] FINAL: blocked: no time\n", SECTIONS)
assert any("FINAL" in p and "blocked" in p for p in bang_final), \
    "- [!] FINAL must block; it was a one-character zero-gate exit"

# --- anti-gaming: stale FINAL GATE after a REOPEN ----------------------------------
reopened = journal_sections(
    "## FINAL GATE 2026-07-05\n- review: PASS - audited\n"
    "## REOPEN 2026-07-07\n- defect: regression against success criterion\n"
)
assert stale_final_gate_problems(reopened), \
    "REOPEN postdating the newest FINAL GATE must be reported"
# and it reaches plan_problems only when FINAL is checked:
stale = plan_problems("- [x] FINAL: gate\n", reopened)
assert any("REOPEN" in p for p in stale), "checked FINAL + later REOPEN must block"
# a fresh gate after the reopen clears it:
regated = journal_sections(
    "## FINAL GATE 2026-07-05\n- review: PASS - audited\n"
    "## REOPEN 2026-07-06\n- defect: x\n"
    "## FINAL GATE 2026-07-07\n- review: PASS - re-audited\n"
)
assert stale_final_gate_problems(regated) == [], "fresh gate must clear the reopen"
assert stale_final_gate_problems(SECTIONS) == [], "no REOPEN -> nothing to report"

# --- pending_runs --------------------------------------------------------
exp = "| run-001 | SG2 | h | none | val 0.7 | SUPPORTED |\n| run-002 | SG3 | h | d | - | PENDING |"
assert len(pending_runs(exp)) == 1, "exactly one PENDING row expected"

# --- design_inspection_problems (cluster design gate) --------------------
# Keyed on DESIGN.md presence so tiering stays intact: a small mission has a
# PLAN.md but no DESIGN.md and must never be blocked by this check.
with tempfile.TemporaryDirectory() as _d:
    dp = Path(_d)

    # small mission: PLAN present, no DESIGN.md -> not blocked
    assert design_inspection_problems(dp, plan_present=True) == [], \
        "small mission (no DESIGN.md) must not be blocked by the design gate"

    # cluster mission mid-design: DESIGN.md drafts but no PLAN.md -> not blocked
    (dp / "DESIGN.md").write_text(
        "## DESIGN DRAFT v1\n- approach: x\n", encoding="utf-8"
    )
    assert design_inspection_problems(dp, plan_present=False) == [], \
        "pre-Agree design (no PLAN.md) must not be blocked"

    # cluster mission past Agree, inspection missing -> blocked
    blocked = design_inspection_problems(dp, plan_present=True)
    assert blocked and "FINAL DESIGN INSPECTION" in blocked[0], \
        "cluster mission with DESIGN.md but no inspection must block"

    # inspection present but not implementation-ready -> blocked
    (dp / "DESIGN.md").write_text(
        "## DESIGN DRAFT v1\n- approach: x\n"
        "## FINAL DESIGN INSPECTION 2026-07-07\n"
        "- design-final: REVISE - gaps remain\n"
        "- implementation-ready: no\n",
        encoding="utf-8",
    )
    not_ready = design_inspection_problems(dp, plan_present=True)
    assert not_ready and "implementation-ready" in not_ready[0], \
        "inspection present but not ready must block"

    # inspection present and ready -> passes
    (dp / "DESIGN.md").write_text(
        "## DESIGN DRAFT v1\n- approach: x\n"
        "## FINAL DESIGN INSPECTION 2026-07-07\n"
        "- design-final: GO - complete\n"
        "- implementation-ready: yes\n",
        encoding="utf-8",
    )
    assert design_inspection_problems(dp, plan_present=True) == [], \
        "ready inspection must pass"

    # anti-gaming: the LAST inspection wins - a failed block followed by a passed
    # re-inspection must not permanently block Close
    (dp / "DESIGN.md").write_text(
        "## DESIGN DRAFT v1\n- approach: x\n"
        "## FINAL DESIGN INSPECTION 2026-07-06\n"
        "- design-final: REVISE - gap\n- implementation-ready: no\n"
        "## DESIGN DRAFT v2\n- approach: y\n"
        "## FINAL DESIGN INSPECTION 2026-07-07\n"
        "- design-final: GO - resolved\n- implementation-ready: yes\n",
        encoding="utf-8",
    )
    assert design_inspection_problems(dp, plan_present=True) == [], \
        "re-inspection pass must clear the earlier failed block"

print("stop_audit self-check: all assertions passed")
