"""Deterministic simulated reasoning methods.

Every method is a ``MethodRunner`` over the SAME implicit task tree (see
``tasks.py``): the same goal path, the same traps, the same budget. Methods
differ only in traversal strategy, so differences in the comparison table
come from strategy, not from different problems or different scoring.

Strategies, in plain terms:

- ``tree-search``: plain depth-first search, children in branch order.
  Exhausts trap subtrees fully before backtracking.
- ``graph-search``: breadth-first search with a visited set. Level order
  means it visits every node shallower than the goal before reaching it,
  which is expensive on deep tasks.
- ``rewound-reasoning``: depth-first search that detects a trap marker on
  entry, records one retry, and prunes that subtree after a single node
  instead of exhausting it (backtrack-and-retry).
- ``lookahead-search``: depth-first search whose children are ordered by a
  2-step lookahead over the task's noisy node signal (signal of the child
  plus the best grandchild signal, ties broken by branch index). The signal
  is imperfect, so this method still explores decoys.
- ``algorithm-of-thoughts``: plan-then-solve. It enumerates candidate
  mid-depth checkpoints in signal order and, for each, runs a bounded
  depth-first search to full depth. The goal prefix is always among the
  checkpoints, so the search is exhaustive; the saving comes from never
  re-exploring shallower levels once a checkpoint is chosen.
- ``broken-baseline``: a deliberately broken control. It stops one step
  short of full depth and never checks its plan, so it never reaches a goal
  node. It exists so the fairness tests have a method that must rank last.

No method sees the goal path directly except through the noisy signal
(lookahead, algorithm-of-thoughts) or through trap markers (rewound).
Scoring never uses the signal: a run counts as solved only if the walk
actually reaches the goal node within budget.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .tasks import Task, validate_budget

METHOD_NAMES = (
    "tree-search",
    "graph-search",
    "rewound-reasoning",
    "lookahead-search",
    "algorithm-of-thoughts",
    "broken-baseline",
)


@dataclass
class RunResult:
    method: str
    task_id: str
    solved: bool
    expansions: int
    retries: int = 0
    path: tuple[int, ...] | None = None


class _Walk:
    """Shared budget-counting walk over one task's implicit tree."""

    def __init__(self, task: Task, budget: int) -> None:
        self.task = task
        self.budget = validate_budget(budget, "budget")
        self.expansions = 0
        self.retries = 0

    def visit(self) -> bool:
        """Count one node expansion. False when the budget is exhausted."""
        if self.expansions >= self.budget:
            return False
        self.expansions += 1
        return True

    def is_goal(self, path: tuple[int, ...]) -> bool:
        return len(path) == self.task.depth and path == self.task.goal_path

    def is_trap(self, path: tuple[int, ...]) -> bool:
        return path in self.task.trap_paths

    def children(self, path: tuple[int, ...]) -> list[int]:
        return list(range(self.task.branching))


def _dfs(
    walk: _Walk,
    path: tuple[int, ...],
    order: list[int] | None = None,
    rewind_traps: bool = False,
) -> tuple[int, ...] | None:
    if not walk.visit():
        return None
    if walk.is_goal(path):
        return path
    if len(path) >= walk.task.depth:
        return None
    if rewind_traps and walk.is_trap(path):
        walk.retries += 1
        return None
    branches = order if order is not None else walk.children(path)
    for branch in branches:
        found = _dfs(walk, path + (branch,), None, rewind_traps)
        if found is not None:
            return found
        if walk.expansions >= walk.budget:
            return None
    return None


def _dfs_ordered(walk: _Walk, path: tuple[int, ...], order_fn) -> tuple[int, ...] | None:
    if not walk.visit():
        return None
    if walk.is_goal(path):
        return path
    if len(path) >= walk.task.depth:
        return None
    ordered = order_fn(walk.task, path)
    for branch in ordered:
        found = _dfs_ordered(walk, path + (branch,), order_fn)
        if found is not None:
            return found
        if walk.expansions >= walk.budget:
            return None
    return None


def _lookahead_order(task: Task, path: tuple[int, ...]) -> list[int]:
    def score(branch: int) -> tuple[int, int]:
        child = path + (branch,)
        best_grand = 0
        if len(child) < task.depth:
            best_grand = max(
                task.node_signal(child + (g,)) for g in range(task.branching)
            )
        return (-(task.node_signal(child) + best_grand), branch)

    return sorted(range(task.branching), key=score)


def _run_tree(task: Task, budget: int) -> RunResult:
    walk = _Walk(task, budget)
    found = _dfs(walk, ())
    return RunResult("tree-search", task.id, found is not None, walk.expansions, 0, found)


def _run_graph(task: Task, budget: int) -> RunResult:
    walk = _Walk(task, budget)
    queue: deque[tuple[int, ...]] = deque([()])
    visited = {()}
    while queue:
        path = queue.popleft()
        if not walk.visit():
            break
        if walk.is_goal(path):
            return RunResult("graph-search", task.id, True, walk.expansions, 0, path)
        if len(path) >= task.depth:
            continue
        for branch in walk.children(path):
            child = path + (branch,)
            if child not in visited:
                visited.add(child)
                queue.append(child)
    return RunResult("graph-search", task.id, False, walk.expansions, 0, None)


def _run_rewound(task: Task, budget: int) -> RunResult:
    walk = _Walk(task, budget)
    found = _dfs(walk, (), rewind_traps=True)
    return RunResult(
        "rewound-reasoning", task.id, found is not None, walk.expansions, walk.retries, found
    )


def _run_lookahead(task: Task, budget: int) -> RunResult:
    walk = _Walk(task, budget)
    found = _dfs_ordered(walk, (), _lookahead_order)
    return RunResult(
        "lookahead-search", task.id, found is not None, walk.expansions, 0, found
    )


def _run_algorithm_of_thoughts(task: Task, budget: int) -> RunResult:
    """Plan-then-solve: enumerate mid-depth checkpoints, solve from each."""
    walk = _Walk(task, budget)
    mid = task.depth // 2 or 1
    # Phase 1 (planning): order all mid-depth prefixes by their signal sum.
    prefixes: list[tuple[int, ...]] = [()]

    def _expand(prefixes: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
        out = []
        for prefix in prefixes:
            for branch in range(task.branching):
                out.append(prefix + (branch,))
        return out

    for _ in range(mid):
        prefixes = _expand(prefixes)

    def _signal_sum(path: tuple[int, ...]) -> int:
        return sum(task.node_signal(path[: i + 1]) for i in range(len(path)))

    prefixes.sort(key=lambda p: (-_signal_sum(p), p))
    # Phase 2 (solving): bounded DFS from each checkpoint, in plan order.
    for checkpoint in prefixes:
        if walk.expansions >= walk.budget:
            break
        # Count the checkpoint itself once if it was not visited before.
        found = _dfs_from(walk, checkpoint)
        if found is not None:
            return RunResult(
                "algorithm-of-thoughts", task.id, True, walk.expansions, 0, found
            )
    return RunResult("algorithm-of-thoughts", task.id, False, walk.expansions, 0, None)


def _dfs_from(walk: _Walk, start: tuple[int, ...]) -> tuple[int, ...] | None:
    """DFS from ``start`` downward; the checkpoint node counts as visited."""
    if not walk.visit():
        return None
    if walk.is_goal(start):
        return start
    if len(start) >= walk.task.depth:
        return None
    for branch in walk.children(start):
        found = _dfs_from(walk, start + (branch,))
        if found is not None:
            return found
        if walk.expansions >= walk.budget:
            return None
    return None


def _run_broken(task: Task, budget: int) -> RunResult:
    # Deliberately broken control: it stops one step short of full depth and
    # never checks its partial plan, so it can never reach a goal node. It
    # must therefore score worst on every task set, which is what the
    # fairness tests assert. Its expansions stay small by construction.
    walk = _Walk(task, budget)
    for _ in range(max(task.depth - 1, 0)):
        if not walk.visit():
            break
    return RunResult("broken-baseline", task.id, False, walk.expansions, 0, None)


_RUNNERS = {
    "tree-search": _run_tree,
    "graph-search": _run_graph,
    "rewound-reasoning": _run_rewound,
    "lookahead-search": _run_lookahead,
    "algorithm-of-thoughts": _run_algorithm_of_thoughts,
    "broken-baseline": _run_broken,
}


class MethodRunner:
    """Runs one named method on one task under a fixed budget."""

    def __init__(self, method: str) -> None:
        if method not in _RUNNERS:
            raise ValueError(f"unknown method {method!r}; known: {sorted(_RUNNERS)}")
        self.method = method

    def run(self, task: Task, budget: int | None = None) -> RunResult:
        return _RUNNERS[self.method](task, task.budget if budget is None else budget)


def build_method(method: str) -> MethodRunner:
    return MethodRunner(method)
