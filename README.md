# Jagadish-reasoning-method-suite

> **Disclaimer:** This project is an independent study project. It is not
> affiliated with, endorsed by, or connected to any company, vendor, or
> institution. All organisations, people, and tasks in this repo are
> fictional or synthetic. Nothing here uses real user data, real model
> outputs, or real business information.

## Recruiter summary

Comparing reasoning methods fairly is hard when every method is tested on
different problems with different scoring. This repo is a measurement
instrument, not another reasoning framework: one identical harness runs the
same 12 synthetic tasks through five deterministic simulated reasoning
methods plus a deliberately broken control, under the same budgets and the
same scoring rule. The output is a single comparison table, plus tests
proving the harness itself is fair (method order and task order cannot
change scores, and the broken control ranks last).

## What this is — and what it is not

This repo measures **simulated search strategies** (tree search, graph
search, rewound reasoning, lookahead search, algorithm-of-thoughts style
planning) on small synthetic search trees. It does **not** measure real
language models, and its numbers are **not** quality claims about any real
model or method. The task set is small (12 tasks) and synthetic, so the
results are regression checks for the harness: they show the instrument
works and the strategies behave differently, nothing more. See
[Methodology and limits](#methodology-and-limits) and
`knowledge/methodology-and-limits.md`.

## Comparison table (from a real run)

Run with `python3 scripts/run_demo.py` (Python 3.12, system `python3`,
stdlib only, no network). 12 tasks, budget 400 expansions per task:

| Method | Solved | Solve rate | Mean expansions (solved) | Total expansions | Retries |
| --- | ---: | ---: | ---: | ---: | ---: |
| algorithm-of-thoughts | 12/12 | 1.00 | 113.5 | 1362 | 0 |
| lookahead-search | 10/12 | 0.83 | 51.1 | 1311 | 0 |
| rewound-reasoning | 9/12 | 0.75 | 69.8 | 1828 | 8 |
| tree-search | 9/12 | 0.75 | 80.2 | 1922 | 0 |
| graph-search | 8/12 | 0.67 | 99.4 | 2395 | 0 |
| broken-baseline | 0/12 | 0.00 | n/a | 40 | 0 |

Best: algorithm-of-thoughts (12/12 solved, 1362 total expansions).
Worst: broken-baseline (0/12 solved, 40 total expansions).

Reading the table honestly: the plan-then-solve method solves every task
but is not the cheapest per solved task — lookahead search uses fewer
expansions on the tasks it solves (51.1 vs 113.5). Ranking is by tasks
solved first, then fewest total expansions; see `reasoning_suite/reporter.py`.

## How it works

```
Synthetic tasks (tasks.py) ──► Harness (harness.py, identical for all)
        │                              │
        ▼                              ▼
MethodRunner per method ──► EvaluatorAgent (evaluator.py, one rule)
(methods.py)                       │
                                   ▼
                          Reporter (reporter.py) ──► comparison table
```

1. **Tasks** — 12 synthetic planning puzzles for the fictional Zindlewick
   Labs. Each task is an implicit search tree: a goal path of `depth`
   choices, `branching` options per level, and trap subtrees (dead ends a
   naive walk must exhaust). Goal paths and traps derive deterministically
   from the task id, so every run sees the same problems.
2. **MethodRunner** — one runner per method, each a different traversal
   strategy over the same tree: depth-first (tree), breadth-first with a
   visited set (graph), depth-first with trap pruning and retry counting
   (rewound), signal-ordered depth-first with 2-step lookahead (lookahead),
   and plan-then-solve over mid-depth checkpoints (algorithm-of-thoughts).
   A deliberately broken control stops one step short and never solves.
3. **EvaluatorAgent** — scores a run 1.0 if and only if the walk actually
   reached the goal node within budget, else 0.0. It never uses the task's
   noisy node signal, so it cannot favour signal-using methods.
4. **Reporter** — formats evaluations as the table above. It formats only;
   it never re-scores.

Architecture diagrams: [`knowledge/architecture.md`](knowledge/architecture.md)
(harness flow, method strategies).

## How to run

```bash
python3 -m pytest -q          # full suite (stdlib only, no .venv needed)
python3 scripts/run_demo.py   # live comparison table
python3 scripts/brand_check.py  # real-name blocklist check (hashes only)
```

Example output (real output from `scripts/run_demo.py`):

```
| algorithm-of-thoughts | 12/12 | 1.00 | 113.5 | 1362 | 0 |
| lookahead-search | 10/12 | 0.83 | 51.1 | 1311 | 0 |
| broken-baseline | 0/12 | 0.00 | n/a | 40 | 0 |
```

## Methodology and limits

- **Same everything.** Same tasks, same scoring, same per-task budget
  (400 expansions) for every method. Runs are pure functions of (method,
  task, budget); no method's output feeds another's input.
- **Fairness is tested, not asserted.** Swapping method order does not
  change any score; swapping task order does not change any per-task
  score; the deliberately broken method scores worst (0/12).
- **The signal is noisy on purpose.** Lookahead and plan-then-solve order
  their search with a deterministic hint that scores the goal child 2 but
  also scores some decoys 2, so trusting it blindly still explores decoys.
  It is a model of a fallible heuristic, not knowledge of the answer, and
  scoring never uses it.
- **What is NOT counted.** For the plan-then-solve method, only solving
  expansions are counted; generating and ordering the plan checkpoints is
  not charged as expansions. That flatters that method slightly — see
  `knowledge/methodology-and-limits.md`.
- **Small, synthetic, simulated.** 12 tasks, no real models, no real
  prompts, no statistical significance. Do not generalise these numbers to
  real reasoning systems. A larger, independently generated task set and a
  real-model adapter are Planned, not Built.
- **Known behaviours kept visible.** Breadth-first search is the most
  expansion-hungry here because it visits every shallower node before
  reaching a deep goal — that is a property of level-order search on
  these trees, not a universal claim about graph search.

## Guardrails and security controls

- **PII redaction** (`reasoning_suite/guards.py`): email addresses, card
  numbers (plain, spaced, or dashed), phone numbers, and SSN-style numbers
  are all masked; clean text passes through unchanged.
- **Confirmation gates**: approvals must name a person, be single-use,
  match the requested scope exactly, and not be expired. Low-confidence
  approvals and self-contradicting consent (e.g. "yes, wait, no") are
  rejected. Bypass (no token), reject (wrong scope / expired / reused),
  and absent (no record) paths are all tested.
- **Cost/budget inputs reject negatives** (`validate_budget`), including
  harness budget overrides.
- **Brand/name check** (`scripts/brand_check.py`): the blocklist is stored
  as SHA-256 hashes, never plain names; a test asserts the blocklist is
  non-empty. The provisional example name was checked against the web
  and **replaced**: its first word is used by real firms, so
  the fictional example lab in this repo is "Zindlewick Labs" (no company
  found under that name; only an unrelated artist handle).
- **Hash-chained audit** (`reasoning_suite/audit.py`): harness runs can be
  logged append-only; tampering with a payload or a chain link breaks
  `verify()`.
- **Synthetic data only.** No real data, no network calls, no credentials.

## Built / Written-not-run / Planned

| Item | Status |
| --- | --- |
| 12-task synthetic set, 6 runners, identical harness, evaluator, reporter | Built, 52 tests green locally |
| Fairness tests (order invariance, broken-control-last) | Built |
| PII redaction, confirmation gates, budget validation, hash-chained audit, brand check | Built |
| CI workflow file (`.github/workflows/ci.yml`) | Written, **not run — CI NOT verified** |
| 8-word overlap check against source text | Not run — **not claimed** (all prose here is original; no source text was copied) |
| Larger independently generated task set, statistical reporting | Planned |
| Adapter for real-model runs (same harness, same scoring) | Planned |
| Deployment, packaging, releases | Planned (not built) |

## Test count

**52 tests, all passing locally** with system Python 3.12 / pytest
(`python3 -m pytest -q`). CI is **not verified** — the workflow file is
included but has never run on GitHub, so nothing here is claimed
CI-green. No deployment exists.

## Knowledge notes

- [`knowledge/notes.md`](knowledge/notes.md) — distilled notes on the five
  reasoning strategies and what each traversal choice costs.
- [`knowledge/architecture.md`](knowledge/architecture.md) — Mermaid
  diagrams: harness flow and per-method strategies.
- [`knowledge/methodology-and-limits.md`](knowledge/methodology-and-limits.md)
  — comparison methodology and its limits, in full.
- [`docs/implementation-guide.md`](docs/implementation-guide.md) — how to
  add a method or a task without breaking fairness.
- [`docs/threat-model.md`](docs/threat-model.md) — STRIDE-style notes and
  design decisions for this measurement instrument.

## License

MIT — see [LICENSE](LICENSE). Security policy: [SECURITY.md](SECURITY.md).
