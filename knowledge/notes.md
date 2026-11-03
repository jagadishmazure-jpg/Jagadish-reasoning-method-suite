# Knowledge notes: reasoning strategies under one harness

Original notes. Method names are used as generic strategy labels, and every
claim below is about the simulated harness in this repo, not about any real
system.

## The five strategies, and what each one pays for

- **Tree search (depth-first).** Explores one branch to full depth before
  trying the next. Cheap when the goal sits on an early branch, expensive
  when it sits late, and it pays the full price of every trap subtree it
  enters: a dead end is only recognised after its whole subtree is walked.
  In this harness it solves 9/12 tasks.
- **Graph search (breadth-first, visited set).** Explores level by level,
  so it never goes deep down a wrong branch — but it visits every node
  shallower than the goal before reaching it. On deep tasks that breadth
  costs more than depth-first's wrong turns. In this harness it solves
  8/12, the weakest of the five real strategies, with the highest total
  expansions (2395).
- **Rewound reasoning (backtrack-and-retry).** Depth-first search plus one
  extra ability: when it steps onto a marked trap node, it records a
  retry and prunes that subtree after a single node instead of exhausting
  it. The retry count (8 across the task set) is the visible trace of
  that behaviour. It solves 9/12 like plain tree search but with fewer
  total expansions (1828 vs 1922) — the saving is exactly the pruned trap
  subtrees.
- **Lookahead search.** Orders children by a 2-step lookahead over a noisy
  signal (child signal plus best grandchild signal) before running
  depth-first. Because the signal is imperfect — some decoys score as
  highly as the goal child — it still explores decoys, but good ordering
  puts the goal early more often. It solves 10/12 and is cheapest per
  solved task (51.1 mean expansions).
- **Algorithm-of-thoughts style planning (plan-then-solve).** First
  enumerates mid-depth checkpoints in signal order (the plan), then runs
  a bounded depth-first search from each checkpoint in turn (the solve).
  The goal prefix is always among the checkpoints, so the search is
  exhaustive, and shallower levels are never re-explored once a
  checkpoint is chosen. It solves 12/12 here — but see the counting caveat
  in `methodology-and-limits.md`: plan generation itself is not charged
  as expansions, so its total (1362) is not strictly comparable to the
  others' totals.

## Why a broken control matters

A comparison instrument needs a result it can predict in advance. The
broken baseline — it stops one step short of full depth and never checks
its plan — must score 0/12 on any task set. If it ever scores above zero,
the harness or the scoring rule is broken, not the method. That single
assertion catches a whole class of harness bugs (for example, scoring a
partial path as solved, or leaking the goal into the result).

## What "solved" means here

Solved means the walk's final node equals the task's goal path and the
walk stayed within budget. Partial paths, near misses, and
signal-favoured prefixes do not count. Keeping the definition this strict
is what makes the evaluator neutral: it inspects only the walk's outcome,
never the method's internal reasoning.

## Strategy families

The strategy labels name common reasoning strategy families
— tree-structured search, graph-structured search, self-correction by
backtracking, lookahead-guided search, and planning a solution skeleton
before filling in steps. This repo implements small deterministic
simulations of those ideas; it does not reproduce, quote, or evaluate any
particular published system.
