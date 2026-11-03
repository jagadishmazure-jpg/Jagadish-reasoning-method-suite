# Implementation guide

## Adding a new method without breaking fairness

1. Add a `_run_<name>` function in `reasoning_suite/methods.py` that
   takes `(task, budget)` and returns a `RunResult`. It must:
   - count every node it visits through `_Walk.visit()` (never bypass
     the counter),
   - stop when the budget is exhausted,
   - set `solved=True` only when the walk actually reaches
     `task.goal_path` at full depth,
   - not read `task.goal_path` directly to choose its path (the noisy
     `node_signal` is the only hint available, and it is imperfect).
2. Register the name in `METHOD_NAMES` and `_RUNNERS`.
3. Add determinism and budget tests for it, and re-run the fairness
   tests: method-order swap, task-order swap, broken-control-last.
4. Regenerate the README table from `python3 scripts/run_demo.py` and
   update the demo test's exact numbers from that same run. Never
   hand-edit a number in the README or the demo test.

## Adding a new task

1. Add a spec row in `default_tasks()` in `reasoning_suite/tasks.py`
   (id, title, kind, difficulty, branching, depth, traps, budget).
2. Keep the budget the same for all methods — the harness applies the
   task's budget to every method automatically.
3. Re-run the full suite and regenerate the README table and demo test
   numbers. The task count in the README and in tests must match the
   real set (currently 12).

## Running offline

Everything runs on the standard library. No network, no API keys, no
model calls. `python3 -m pytest -q` from the repo root is the whole
verification story for a local run.
