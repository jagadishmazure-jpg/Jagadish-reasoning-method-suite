"""The identical harness every method runs on.

The harness owns the task list, the per-task budget, and the run order. It
gives every method the same ``Task`` objects and the same budget, runs each
method independently (no method's output feeds another's input), and records
a ``MethodResult`` per (method, task) pair. Because runs are pure functions
of (method, task, budget), the order methods are listed in cannot change
any score -- a property the fairness tests check directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .methods import METHOD_NAMES, MethodRunner, RunResult
from .tasks import Task, default_tasks, validate_budget


@dataclass(frozen=True)
class MethodResult:
    method: str
    task_id: str
    solved: bool
    expansions: int
    retries: int
    score: float  # 1.0 if solved else 0.0; efficiency is reported separately

    @classmethod
    def from_run(cls, run: RunResult) -> "MethodResult":
        return cls(
            method=run.method,
            task_id=run.task_id,
            solved=run.solved,
            expansions=run.expansions,
            retries=run.retries,
            score=1.0 if run.solved else 0.0,
        )


class Harness:
    """Run a set of methods over a set of tasks under identical budgets."""

    def __init__(
        self,
        tasks: list[Task] | None = None,
        methods: tuple[str, ...] | list[str] = METHOD_NAMES,
        budget_override: int | None = None,
    ) -> None:
        self.tasks = list(tasks) if tasks is not None else default_tasks()
        self.methods = list(methods)
        unknown = [m for m in self.methods if m not in METHOD_NAMES]
        if unknown:
            raise ValueError(f"unknown methods: {unknown}")
        if budget_override is not None:
            validate_budget(budget_override, "budget_override")
        self.budget_override = budget_override

    def run(self) -> list[MethodResult]:
        results: list[MethodResult] = []
        for method_name in self.methods:
            runner = MethodRunner(method_name)
            for task in self.tasks:
                budget = task.budget if self.budget_override is None else self.budget_override
                results.append(MethodResult.from_run(runner.run(task, budget)))
        return results

    def run_method(self, method: str) -> list[MethodResult]:
        if method not in self.methods:
            raise ValueError(f"method {method!r} not in this harness")
        runner = MethodRunner(method)
        out = []
        for task in self.tasks:
            budget = task.budget if self.budget_override is None else self.budget_override
            out.append(MethodResult.from_run(runner.run(task, budget)))
        return out


def run_all(
    tasks: list[Task] | None = None,
    methods: tuple[str, ...] | list[str] = METHOD_NAMES,
) -> list[MethodResult]:
    return Harness(tasks=tasks, methods=methods).run()
