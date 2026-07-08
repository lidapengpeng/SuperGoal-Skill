# ML experiment playbook

For tasks involving datasets, training, or evaluation runs - vision models,
3D generation, and similar engineering projects - and for research missions
whose contribution is a mechanism claim (a new module, loss, or training
signal), which additionally follow the research design contract below.

## Dataset analysis before training

The first PLAN.md subgoals for any training task, before touching the model:

```markdown
- [ ] SG1: dataset inventory | verify: `<analysis script/notebook>` | done-when: sample counts, label/class distribution, split sizes quoted in JOURNAL
- [ ] SG2: integrity scan | verify: `<scan command>` | done-when: corrupt/duplicate/outlier counts quoted; blockers filed
- [ ] SG3: label spot-check | verify: manual N-per-class sample | done-when: error-rate estimate recorded
- [ ] SG4: preprocessing & augmentation audit | verify: config diff vs paper/README | done-when: mismatches listed or none
- [ ] SG5: leakage check | verify: `<overlap check>` | done-when: cross-split overlap = 0 or documented
```

## Baseline before improvement

Reproduce the reference configuration end-to-end once (or the shortest
faithful proxy) and record: commit, resolved config, seed, dataset version,
metric with variance if known. No model changes before a baseline number
exists - without it every later claim is unfalsifiable.

## Run discipline

- Naming: `run-<seq>-<sg>-<slug>` (e.g. `run-007-SG3-lr-warmup`); one output
  directory per run.
- Config snapshot: dump the fully resolved config into the run directory at
  launch.
- Logging: metrics must land machine-parseable (CSV, JSONL, TensorBoard).
  The Observe phase quotes parsed numbers; screenshots and impressions are
  not observations.
- Smoke first: tiny subset, few steps, reduced resolution; assert the loss
  moves and IO shapes are sane before any full run.
- Long runs: record the checkpoint path and exact resume command in the
  EXPERIMENTS.md row at launch time, not after a crash.

## EXPERIMENTS.md ledger

One row per run. A row is created as PENDING at launch and MUST be concluded
with evidence before the task can end (the Stop hook blocks on PENDING).

```markdown
| run | sg | hypothesis | delta vs baseline | metrics | verdict |
|-----|----|------------|-------------------|---------|---------|
| run-001-SG2-baseline | SG2 | reproduce README mIoU 0.74 | none (baseline) | val mIoU 0.738 | SUPPORTED |
| run-002-SG3-warmup | SG3 | warmup fixes early divergence | +500-step warmup (only) | val loss 0.412 vs 0.437 | SUPPORTED |
| run-003-SG3-bigger-lr | SG3 | 2x LR converges faster | lr 1e-3 -> 2e-3 (only) | diverged @ step 1.2k | REFUTED |
```

Verdict values: `PENDING` / `SUPPORTED` / `REFUTED` / `INCONCLUSIVE`.
Refuted rows are evidence, not embarrassment - never delete them.

A row may legitimately stay PENDING across sessions while its run executes.
The Stop hook will nudge about it at session end: acknowledge by restating
the waiting state (run id, ETA, resume command) in one line - never by
fabricating a conclusion before the metrics exist.

## Hyperparameter discipline

- One variable (or one pre-declared orthogonal group) per run.
- Write the expected direction before launching; a change without an
  expectation is a lottery ticket, not an experiment.
- Coarse-to-fine: order-of-magnitude sweeps on proxies first, fine steps
  only near a promising region.
- Every trial - including failures - gets a ledger row.

## Research design contract (new module / loss / mechanism)

Applies whenever the contribution is a mechanism claim. A design draft - or
any mid-loop redesign - proposing one is INVALID until it states all seven
below under a `## Research design contract` heading with the labeled lines
in `config/designer.toml` (failure-mode, tensor-mechanism, equation,
gradient-intuition, novelty, ablation-matrix, kill-criteria). The Stop hook
checks **presence** of those labels when `RESEARCH.md` has a `## Novelty`
section; debate reviewers attack substance; the plan gate re-checks derived
subgoals. This is the anti-laziness gate: it converts "be innovative" into a
constrained search the model cannot answer with a buzzword.

1. **Failure mode** - the observed, evidenced failure the mechanism
   addresses: an error analysis, a cited claim (E-ID), or a journal/
   Observe-0 finding. "Improve robustness" is not a failure mode;
   "cross-attention mixes tokens across object boundaries (per E014's
   boundary-F analysis)" is.
2. **Mechanism at tensor level** - what tensor changes, input/output
   shapes, the insertion point in the computational graph, training-only
   or inference-time, parameter and compute overhead. A module idea is not
   real until it can be located in the graph.
3. **Equation or tensor operation** - the mathematical form (e.g.
   `softmax(QK^T/sqrt(d) + lambda*B_geo) V`), never a name. "Adaptive
   multi-scale fusion" is a phrase, not a mechanism.
4. **Gradient intuition** (loss terms) - which predictions are pushed
   together or apart, what signal supervises the term, how it interacts
   with the existing losses, and the weighting schedule.
5. **Prior-work basis and novelty check** - the idea-atom claims it
   composes (E-IDs), plus a novelty-search verdict from the researcher:
   `already-done | minor-variant | similar-mechanism-other-task |
   possibly-novel`. An unchecked novelty claim does not survive the design
   debate; an `already-done` verdict kills the idea and earns an `L-`
   lesson so it is never re-proposed.
6. **Ablation matrix** - baseline; each component toggled independently;
   and a parameter/compute-matched control. A gain that disappears under
   matched parameters was capacity, not mechanism; a gain that needs the
   extra supervision signal in the baseline too is the signal, not the
   mechanism. "The module works" means the delta exceeds the noise band
   (multi-seed when in doubt) - not "the run finished" and not "the curve
   looks better".
7. **Kill criteria** - the observations that abandon the idea (e.g. no
   gain over the matched control across the proxy budget, unstable
   gradients, gain not robust across seeds). They become EXPERIMENTS.md
   verdicts and feed the stop rules; an idea without kill criteria cannot
   be falsified, only defended.

## Proxy evaluation strategy

Filter hypotheses on cheap proxies: data subset, short schedule, reduced
resolution, smaller backbone. Promote only surviving hypotheses to full
training, within the mission's agreed budget (default: at most 2 full runs
unless the contract says otherwise). Record the proxy-to-full correlation
whenever both exist - a proxy that stops predicting full results is itself a
finding to log.
