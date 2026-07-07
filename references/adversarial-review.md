# Adversarial review protocol (Gate)

Maker and checker must be different contexts. A model reviewing its own work
converges on self-agreement; the stop condition must depend on the checker's
verdict, not the maker's belief.

## Gates

1. **Plan gate** (tiered) - fires once, right after Agree and before cycle
   1: the reviewer attacks the contract itself - is this the right problem,
   is the success criterion checkable and hard to game, which subgoal is
   most likely to refute the plan? The inner loop can satisfy a spec but
   never fix a wrong one. Skip only when the mission is small (tier
   definitions live in SKILL.md's Tier check). Verdicts and logging
   are deliberately different from the completion gates: log a
   `## PLAN GATE <ISO-date>` section in JOURNAL.md with
   `plan-review: GO - <one line>`, `plan-review: REVISE - <objection>`, or
   `plan-review: SKIPPED (small mission) - <one line>`. Never write
   `review: PASS` in this section - the Stop hook treats that string as
   completion evidence for any `SG<id>` the section happens to name.
   REVISE goes back to the user: amend the contract at Agree, then re-gate.
   On standard/high-risk (cluster) missions the contract was already attacked
   by four reviewers across the design loop and the final design inspection,
   so the plan gate is covered: when the user replied `go` unchanged, log
   `plan-review: SKIPPED (covered by design gates R1-R<n> and final
   inspection) - <one line>`; only when the user corrected a contract line at
   Agree does the plan gate run on the corrected contract before cycle 1.
   Either way the section quotes the user's Agree reply verbatim, so the
   skip condition is auditable rather than self-certified.
2. **Subgoal gate** (always) - fires whenever a subgoal claims done, before
   its PLAN.md box is checked.
3. **Final gate** (always) - fires before Close concludes: the reviewer
   audits the whole plan, ledger, and diff against BRIEF.md, including that
   Observe-0 baseline evidence exists and budgets were respected. The final
   gate is wired into machinery: PLAN.md's last line is the
   `- [ ] FINAL: ...` item, and the Stop hook only accepts it checked when
   JOURNAL.md contains a `## FINAL GATE` section logging `review: PASS`.

## Design gates (cluster missions only)

Standard/high-risk missions add a whole design-review layer before Agree,
detailed in `references/super-agent-cluster.md`: four differentiated reviewers
(`design-reviewer`, `risk-reviewer`, `verifier`, `leanness-reviewer`) debate
the design for 1-3 bounded rounds, `synthesizer` adjudicates any REVISE round,
and `reviewer` in *design mode* runs an independent final inspection. These
verdicts use markers deliberately disjoint from the completion gates so the
Stop hook never mistakes a design verdict for completion evidence: debate
rounds use `GO|REVISE|BLOCK`; the final inspection logs `design-final:` and
`implementation-ready:` in `DESIGN.md`. Neither may ever contain the string
`review: PASS`, which stays reserved for completion.

Same `reviewer` agent, two modes: design mode (the final design inspection -
audits `DESIGN.md` with a fresh context that never saw the debate) and
completion mode (subgoal and final gates below, unchanged; its code checklist
includes the leanness dimension - file count, patchwork, dead code,
`ponytail:` comments).

## Reviewer requirement

Every claim gets a logged verdict from the required `reviewer` subagent.
Tiering changes which gates run, not whether completion claims are reviewed.

- **Plan gate:** may be skipped for small missions, but the skip must be
  logged with `plan-review: SKIPPED (small mission)`.
- **Subgoal gate:** always use the isolated `reviewer` subagent before a PLAN
  box is checked.
- **Final gate:** always use the isolated `reviewer` subagent.
- **Reviewer unavailable:** stop and repair Setup. Do not replace the reviewer
  with self-review.

## How to spawn the reviewer

Explicitly spawn the custom `reviewer` agent (read-only, high reasoning
effort, defined in `config/reviewer.toml`). Hand it:

- the claim under review, framed as an allegation to attack - never as an
  established fact;
- the verify command and its logged output;
- relevant JOURNAL.md / EXPERIMENTS.md excerpts;
- the constraints section of BRIEF.md.

Do NOT hand it a curated diff or changed-file list: the reviewer derives the
diff itself (`git diff` / `git status` from its own read-only sandbox), so an
omitted file - say, the one where a failing assertion was deleted - cannot be
laundered out of review by the packet.

Do not include your own conclusions or justifications beyond the raw claim
and evidence; a persuaded reviewer is a broken reviewer.

## Reviewer checklist

The operative checklist lives in `config/reviewer.toml` - the copy the agent
is guaranteed to load; it covers the code dimension (correctness, regressions,
security, test honesty, generative checks, over-broad diffs, leanness) and
the experiment dimension for ML claims (baseline comparability, leakage,
metric parsing, noise vs seed variance, ablation isolation, quoted-log
conclusions). This file does not restate it: two copies of a checklist is
drift, not safety.

## Verdict protocol (exactly one)

- **PASS** - no blocking counterexample found; non-blocking notes listed
  separately.
- **FAIL** - at least one concrete counterexample or broken claim; must
  include the minimal reproduction or reasoning, and what evidence would
  flip the verdict.
- **CANNOT-VERIFY** - required evidence is missing; must name the exact
  missing command, log, or experiment.

## Handling verdicts

- Every verdict lands in JOURNAL.md (`review:` field) - no silent reviews.
  The exact marker format and the Stop hook's header-matching rules live in
  `references/loop-daor.md` (journal format section); an unlogged PASS is
  mechanically indistinguishable from no review.
- FAIL reopens the subgoal: back to Design with the counterexample as input.
  The maker may not override or re-litigate a FAIL; only the user can,
  explicitly.
- CANNOT-VERIFY adds the missing-evidence work as a new PLAN.md subgoal (or
  a PENDING EXPERIMENTS.md row) before the claim can return to review.
- Two FAILs on the same subgoal for the same root cause: hard rule 4 fires -
  return to first principles, no third patch.

## If subagents fail

Subagents are required for SuperGoal's review gates. If the `reviewer`
agent cannot be spawned, stop the mission at the current checkpoint, report
the Setup failure, and do not check any PLAN boxes until the reviewer is
available.
