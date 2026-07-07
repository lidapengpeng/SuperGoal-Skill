#!/usr/bin/env python3
"""SuperGoal Stop hook: block session end while verifiable work remains.

Reads the Stop event JSON on stdin and cross-checks the .supergoal/ state files.
Blocks (decision: block) when any of these hold:

1. PLAN.md has unchecked subgoals (`- [ ]`).
2. PLAN.md has checkboxes but is missing the mandatory FINAL gate line.
3. A checked `- [x] SG<id>` has no JOURNAL.md section whose HEADER names
   SG<id> and whose body logs `review: PASS`. (Header-only matching:
   body mentions like "next step: SG3" or a PLAN GATE note must never
   validate another subgoal's box.)
4. The FINAL line is checked but JOURNAL.md has no `## FINAL GATE` section
   containing `review: PASS`.
5. EXPERIMENTS.md has PENDING runs.
6. A cluster mission (DESIGN.md present) that has passed Agree (PLAN.md
   present) has no `## FINAL DESIGN INSPECTION` section logging
   `implementation-ready: yes`. Keyed on DESIGN.md presence, not PLAN.md
   alone: small missions never create DESIGN.md, so this check does not fire
   for them; sessions ending pre-Agree (no PLAN.md) are never blocked by it.
   The LAST inspection section wins - re-inspection after a REVISE appends
   or overwrites, and an old failed block must not shadow a later pass.
7. BRIEF.md exists but PLAN.md does not: a mission that passed Agree always
   has both (the promotion writes PLAN.md first), so this state is either a
   crashed promotion or a dodge that would disable every other check.
   Pre-Agree states (DRAFT_BRIEF.md only) are unaffected.
8. The FINAL line is marked blocked (`- [!] FINAL`): every other box may be
   legitimately blocked, but the final gate has no legitimate blocked state -
   allowing it would be a one-character zero-gate session end.
9. A `## REOPEN <date>` entry postdates the newest `## FINAL GATE <date>`
   while FINAL is checked: a reopened mission must earn a fresh final gate,
   and the stale one must not cover it.

Anti-gaming notes: `review: PASS` only counts in its prescribed
list-item form at line start (`- review: PASS`), so quoted text - including
this hook's own block message pasted into the journal - can never validate a
box. A journal header naming more than one SG id validates none of them.

Blocked items marked "- [!] reason" are intentionally NOT counted (except
FINAL): that is the escape hatch for genuinely blocked work that must be
reported instead. Respects stop_hook_active so a single stop attempt is
nudged at most once - never an infinite loop.
"""
import json
import re
import sys
from pathlib import Path

MAX_LISTED = 5


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


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def journal_sections(journal_text):
    """Split JOURNAL.md into `## ` sections; each keeps header + body."""
    return re.split(r"(?m)^##\s+", journal_text)[1:]


# The prescribed journal form (loop-daor.md): a list item at line start.
# Anchoring prevents quoted prose - including this hook's own block message -
# from validating a checkbox.
PASS_LINE = re.compile(r"(?m)^\s*-\s*review:\s*PASS\b", re.I)


def has_pass(sections, name_pattern):
    """True if a section whose header line matches name_pattern logs `review: PASS`.

    Only the header line (e.g. `## C4 2026-07-05 SG2`) identifies the
    subject; matching bodies too would let incidental mentions of an SG id
    in another section validate that SG's checkbox. A header naming more
    than one SG id identifies nothing: one PASS must never validate several
    boxes at once.
    """
    name = re.compile(name_pattern)
    for section in sections:
        header = section.splitlines()[0] if section.strip() else ""
        if len(re.findall(r"\bSG\w+\b", header)) > 1:
            continue
        if name.search(header) and PASS_LINE.search(section):
            return True
    return False


def plan_problems(plan_text, sections):
    problems = []

    unchecked = [
        m.strip()
        for m in re.findall(r"^\s*[-*]\s*\[ \]\s*(.+)$", plan_text, re.M)
    ]
    if unchecked:
        listed = "; ".join(item[:120] for item in unchecked[:MAX_LISTED])
        extra = len(unchecked) - MAX_LISTED
        more = " (+{} more)".format(extra) if extra > 0 else ""
        problems.append(
            "PLAN.md has {} unchecked subgoal(s): {}{}".format(
                len(unchecked), listed, more
            )
        )

    has_checkbox = re.search(r"^\s*[-*]\s*\[[^\]]\]", plan_text, re.M)
    final_line = re.search(r"^\s*[-*]\s*\[[^\]]\]\s*FINAL\b", plan_text, re.M)
    if has_checkbox and not final_line:
        problems.append(
            "PLAN.md is missing its mandatory last line"
            " '- [ ] FINAL: adversarial final gate returned PASS ...'"
        )

    checked_sgs = re.findall(r"^\s*[-*]\s*\[[xX]\]\s*(SG\w+)", plan_text, re.M)
    unreviewed = [
        sg
        for sg in checked_sgs
        if not has_pass(sections, r"\b" + re.escape(sg) + r"\b")
    ]
    if unreviewed:
        problems.append(
            "checked subgoal(s) with no JOURNAL.md section headed by their"
            " SG id and logging 'review: PASS': "
            + ", ".join(unreviewed[:MAX_LISTED])
        )

    final_checked = re.search(r"^\s*[-*]\s*\[[xX]\]\s*FINAL\b", plan_text, re.M)
    if final_checked and not has_pass(sections, r"FINAL\s+GATE"):
        problems.append(
            "FINAL is checked but JOURNAL.md has no '## FINAL GATE' section"
            " with 'review: PASS' - the final adversarial review is not on"
            " record"
        )

    if re.search(r"^\s*[-*]\s*\[!\]\s*FINAL\b", plan_text, re.M):
        problems.append(
            "the FINAL line is marked blocked ('- [!] FINAL') - the final"
            " gate has no legitimate blocked state; run it, or leave FINAL"
            " unchecked and report the blocker"
        )

    if final_checked:
        problems.extend(stale_final_gate_problems(sections))

    return problems


def _newest_date(sections, header_pattern):
    """Newest ISO date found on headers matching the pattern, or None."""
    pat = re.compile(header_pattern)
    newest = None
    for section in sections:
        header = section.splitlines()[0] if section.strip() else ""
        if not pat.search(header):
            continue
        for date in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", header):
            if newest is None or date > newest:
                newest = date
    return newest


def stale_final_gate_problems(sections):
    """A REOPEN dated after the newest FINAL GATE means the gate is stale.

    lifecycle.md requires reopen to uncheck FINAL so the mission earns a
    fresh, dated gate; this closes the lazy path that leaves FINAL checked
    and lets the old gate silently cover the reopened defect. ISO dates
    compare correctly as strings; undated headers are skipped (no false
    blocks on legacy journals).
    """
    reopen = _newest_date(sections, r"^REOPEN\b")
    gate = _newest_date(sections, r"^FINAL\s+GATE\b")
    if reopen and gate and reopen > gate:
        return [
            "a '## REOPEN {}' entry postdates the newest '## FINAL GATE {}'"
            " while FINAL is checked - a reopened mission must uncheck FINAL"
            " and earn a fresh final gate".format(reopen, gate)
        ]
    return []


def pending_runs(experiments_text):
    return [
        line.strip()
        for line in experiments_text.splitlines()
        if re.search(r"\|\s*PENDING\s*\|?\s*$", line, re.I)
    ]


def design_inspection_problems(supergoal, plan_present):
    """Cluster missions must clear the final design inspection before Close.

    Fires only when the mission both passed Agree (PLAN.md present) and is a
    cluster mission (DESIGN.md present). Small missions never create DESIGN.md,
    so an absent DESIGN.md is not a violation - that is what keeps tiering
    intact. A cluster mission reaches PLAN.md only after W7 wrote the
    inspection, so a present DESIGN.md without a passed inspection is a real
    gap, not a mid-design pause (those have no PLAN.md yet).
    """
    design = supergoal / "DESIGN.md"
    if not (plan_present and design.is_file()):
        return []
    # The LAST inspection section wins: re-inspection after a REVISE must not
    # be shadowed by the earlier failed block.
    last = None
    for section in re.split(r"(?m)^##\s+", read_text(design))[1:]:
        header = section.splitlines()[0] if section.strip() else ""
        if header.startswith("FINAL DESIGN INSPECTION"):
            last = section
    if last is not None:
        if re.search(r"implementation-ready:\s*yes\b", last, re.I):
            return []
        return [
            "DESIGN.md's latest '## FINAL DESIGN INSPECTION' section is"
            " not 'implementation-ready: yes' - the cluster design gate has"
            " not passed"
        ]
    return [
        "DESIGN.md is present (cluster mission) but has no '## FINAL DESIGN"
        " INSPECTION' section with 'implementation-ready: yes' - the design"
        " gate is not on record"
    ]


def main():
    try:
        event = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except (json.JSONDecodeError, ValueError):
        return  # malformed input: never block

    if event.get("stop_hook_active"):
        return  # this stop attempt was already continued once; let it end

    supergoal = find_supergoal(event.get("cwd", "."))
    if supergoal is None:
        return

    journal = supergoal / "JOURNAL.md"
    sections = journal_sections(read_text(journal)) if journal.is_file() else []

    problems = []

    plan = supergoal / "PLAN.md"
    if plan.is_file():
        problems.extend(plan_problems(read_text(plan), sections))
    elif (supergoal / "BRIEF.md").is_file():
        problems.append(
            "BRIEF.md exists but PLAN.md does not - a mission past Agree"
            " always has both (promotion writes PLAN.md first); re-derive"
            " PLAN.md from the agreed contract before ending the session"
        )

    problems.extend(design_inspection_problems(supergoal, plan.is_file()))

    experiments = supergoal / "EXPERIMENTS.md"
    if experiments.is_file():
        pending = pending_runs(read_text(experiments))
        if pending:
            problems.append(
                "EXPERIMENTS.md has {} PENDING run(s): {}".format(
                    len(pending), "; ".join(row[:120] for row in pending[:3])
                )
            )

    if not problems:
        return

    reason = (
        "SuperGoal completion audit: verifiable work remains. "
        + " | ".join(problems)
        + " If you were about to declare the task done, do not: continue the"
        " DAOR loop instead - finish each subgoal, re-run its verify command,"
        " conclude PENDING experiment rows with evidence, and run the"
        " adversarial review so every checked box has its 'review: PASS' in"
        " JOURNAL.md (final gate: a '## FINAL GATE' section). A checked box"
        " without its logged PASS must be unchecked or its review run now."
        " EXCEPTIONS, do not push past them: if this turn intentionally"
        " paused at a user checkpoint (clarifying question, Agree"
        " confirmation, stop-rule pause) or is waiting for a long-running"
        " run to finish, restate the pending question or waiting state in"
        " one line and stop - never answer for the user and never fabricate"
        " a run conclusion. If an item is genuinely blocked, mark it"
        " '- [!] <reason>' in PLAN.md and report the blocker instead of"
        " silently stopping."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
