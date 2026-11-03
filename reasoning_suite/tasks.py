"""The synthetic task set.

Each task describes a small, fully synthetic search problem: a goal path of
``depth`` choices through a tree with ``branching`` options per level, plus a
number of trap subtrees. A trap is a decoy branch whose subtree is a dead end
that a naive depth-first walk must exhaust before backtracking. Tasks are
invented planning puzzles for a fictional lab; they contain no real data.

The goal path and the trap positions are derived deterministically from the
task id, so every run of the harness sees exactly the same problems. The
tree itself is implicit: nodes are identified by their path tuple, children
are generated on demand, and no tree is ever materialised in full.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def validate_budget(value: int, name: str = "budget") -> int:
    """Return ``value`` unchanged, rejecting negative cost/budget inputs."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must not be negative, got {value}")
    return value


def _seed(task_id: str) -> int:
    return int(hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:8], 16)


@dataclass(frozen=True)
class Task:
    """One synthetic search task."""

    id: str
    title: str
    kind: str
    difficulty: int  # 1 (easy) .. 3 (hard)
    branching: int
    depth: int
    traps: int
    budget: int  # maximum node expansions allowed
    description: str = ""
    expected_answer: str = ""

    def __post_init__(self) -> None:
        if self.difficulty not in (1, 2, 3):
            raise ValueError(f"difficulty must be 1, 2 or 3, got {self.difficulty}")
        if self.branching < 2:
            raise ValueError("branching must be at least 2")
        if self.depth < 1:
            raise ValueError("depth must be at least 1")
        if self.traps < 0:
            raise ValueError("traps must not be negative")
        validate_budget(self.budget, "budget")

    @property
    def goal_path(self) -> tuple[int, ...]:
        """The deterministic solution path for this task."""
        seed = _seed(self.id)
        path = []
        state = seed
        for _ in range(self.depth):
            state = (state * 1103515245 + 12345) % (2**31)
            path.append(state % self.branching)
        return tuple(path)

    @property
    def trap_paths(self) -> frozenset[tuple[int, ...]]:
        """Trap nodes: decoy prefixes at depth 2 that lead to dead ends.

        A trap is a path of length 2 whose first step is a decoy (not the
        goal's first step). Up to ``traps`` of them are marked, in branch
        order. Entering a trap subtree without early dead-end detection
        costs a full subtree walk; a rewound method prunes it after one node.
        """
        if self.depth < 2 or self.traps == 0:
            return frozenset()
        goal_first = self.goal_path[0]
        decoys = [b for b in range(self.branching) if b != goal_first]
        chosen = decoys[: self.traps]
        return frozenset((first, 0) for first in chosen)

    def node_signal(self, path: tuple[int, ...]) -> int:
        """A deterministic, imperfect hint about a node's promise.

        The goal child always scores 2, but decoys score 0-2 from a hash of
        their path, so the signal is useful yet fallible: a lookahead method
        that trusts it blindly still explores decoys. This is deliberately
        not an oracle -- it models a noisy heuristic, not knowledge of the
        answer. The evaluator never uses this signal for scoring.
        """
        if not path:
            return 0
        if self.goal_path[: len(path)] == path:
            return 2
        digest = hashlib.sha256(f"{self.id}:{path}".encode("utf-8")).hexdigest()
        return int(digest[:2], 16) % 3


def default_tasks() -> list[Task]:
    """The 12-task synthetic set used by every comparison in this repo."""
    specs = [
        ("t01", "Roster the night shift", "schedule-plan", 1, 2, 3, 0, 400),
        ("t02", "Route the sample courier", "route-plan", 1, 2, 3, 1, 400),
        ("t03", "Balance the lab budget lines", "arithmetic-plan", 1, 3, 3, 1, 400),
        ("t04", "Order the assay pipeline", "sorting-plan", 2, 3, 4, 1, 400),
        ("t05", "Chain the safety approvals", "logic-chain", 2, 3, 4, 2, 400),
        ("t06", "Allocate bench time", "resource-plan", 2, 4, 4, 1, 400),
        ("t07", "Sequence the field survey", "route-plan", 2, 4, 4, 2, 400),
        ("t08", "Reconcile the inventory counts", "arithmetic-plan", 3, 3, 5, 2, 400),
        ("t09", "Plan the multi-site rollout", "schedule-plan", 3, 4, 5, 2, 400),
        ("t10", "Trace the fault through the rig", "logic-chain", 3, 4, 5, 3, 400),
        ("t11", "Pack the cold-chain shipment", "resource-plan", 3, 4, 6, 2, 400),
        ("t12", "Schedule the full trial week", "schedule-plan", 3, 4, 6, 3, 400),
    ]
    tasks = []
    for tid, title, kind, diff, branching, depth, traps, budget in specs:
        tasks.append(
            Task(
                id=tid,
                title=title,
                kind=kind,
                difficulty=diff,
                branching=branching,
                depth=depth,
                traps=traps,
                budget=budget,
                description=(
                    f"Synthetic {kind} puzzle for the fictional Zindlewick Labs: "
                    f"find the {depth}-step plan among {branching} options per step."
                ),
                expected_answer=f"goal path {'.'.join(str(x) for x in Task(id=tid, title=title, kind=kind, difficulty=diff, branching=branching, depth=depth, traps=traps, budget=budget).goal_path)}",
            )
        )
    return tasks
