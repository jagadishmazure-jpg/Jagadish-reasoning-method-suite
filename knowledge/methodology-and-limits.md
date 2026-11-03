# Comparison methodology — and its limits

## Methodology

1. **One task set for all methods.** 12 synthetic tasks, fixed ids, fixed
   goal paths, fixed traps, fixed budgets (400 expansions each). The set
   is generated once by `default_tasks()` and shared, never regenerated
   per method.
2. **One scoring rule for all methods.** Solved = the walk reached the
   goal node within budget. Score 1.0 or 0.0 per task; solve rate and mean
   expansions are aggregates of those scores. The evaluator never sees a
   method's internals and never uses the node signal.
3. **One budget for all methods.** Expansions are counted identically:
   one node visit = one expansion, including trap nodes visited before
   pruning and checkpoint nodes visited during plan-then-solve.
4. **Independence.** Runs are pure functions of (method, task, budget).
   No shared state, no learning across runs, no output feeding another
   method's input.
5. **Ranking rule, fixed in advance.** Most tasks solved first, then
   fewest total expansions, then method name (deterministic tiebreak).
6. **Fairness tests, not just fairness claims.**
   - Method-order swap: identical per-(method, task) scores.
   - Task-order swap: identical per-(method, task) scores.
   - Broken control: 0/12, ranked last, on this task set.
   - Determinism: re-running a method on a task gives identical results.
   - Budget respect: no run exceeds its budget.

## Limits — read before quoting any number from this repo

- **Small and synthetic.** 12 tasks cannot support statistical claims.
  There are no confidence intervals here because the sample is far too
  small for them to mean anything; adding them would be false precision.
- **Simulated, not real.** The "methods" are deterministic tree walks,
  not language models. Nothing here says anything about how any real
  model reasons, and the method ranking must not be quoted as a ranking
  of real reasoning techniques.
- **The signal is a modelling choice.** The noisy node signal (goal child
  always 2, decoys 0–2 by hash) is invented for this harness. Change the
  signal's noise and the lookahead / plan-then-solve results change. The
  signal is documented in `tasks.py` so that sensitivity is visible.
- **Plan generation is not charged.** For algorithm-of-thoughts, only
  solving expansions are counted; enumerating and ordering checkpoints
  costs nothing in this harness. Its 12/12 result is real within the
  harness rules, but its expansion total is flattered relative to
  methods whose planning and solving are the same walk. A future version
  should charge checkpoint enumeration (Planned).
- **Traps are marked.** Rewound reasoning recognises trap markers that a
  real system would have to infer from failed checks. Its advantage is
  therefore an upper bound on what trap detection could buy, not a
  measured value of a real detector.
- **Budgets shape outcomes.** With a larger budget, breadth-first search
  would solve more tasks; with a smaller one, fewer methods would solve
  any. The budget (400) is a harness parameter, and results are
  conditional on it. Try `Harness(budget_override=...)` to see this.
- **No prompt, no model, no human judgement.** There is no prompt
  sensitivity, no judge bias, and no human evaluation in this instrument
  — by design, and also a reason its results cannot transfer to settings
  that have those things.
- **Overlap check not run.** All prose in this repo was written fresh for
  it and no source text was copied, but the formal 8-word overlap check
  against source material was not executed, so it is not claimed as passed.

## What would make this instrument stronger (Planned)

- A larger task set generated independently of the methods (so task
  authors cannot tune tasks to a favourite method).
- Charging plan-generation cost for plan-then-solve methods.
- Unmarked traps, where rewinding must be triggered by a failed check
  rather than a marker.
- A real-model adapter that keeps the same harness, scoring, and budget
  accounting while replacing simulated walks with model calls — with cost
  and latency reported alongside expansions.
