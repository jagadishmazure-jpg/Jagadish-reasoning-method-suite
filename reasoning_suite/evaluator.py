"""EvaluatorAgent: scores harness runs with one rule for every method.

A run scores 1.0 if and only if the walk actually reached the task's goal
node within budget; otherwise 0.0. The evaluator recomputes nothing about
the method's internal strategy and never uses the task's noisy node signal,
so it cannot favour a method that happens to use that signal well. It also
reports efficiency (mean expansions on solved tasks) separately from
correctness, so a fast-but-wrong method cannot outrank a slower correct one
on the headline metric.
"""

from __future__ import annotations

from dataclasses import dataclass

from .harness import MethodResult


@dataclass(frozen=True)
class Evaluation:
    method: str
    tasks: int
    solved: int
    solve_rate: float
    mean_expansions_solved: float | None
    total_expansions: int
    total_retries: int
    mean_score: float


class EvaluatorAgent:
    """Aggregate per-method results into one comparable evaluation."""

    def evaluate(self, results: list[MethodResult], method: str) -> Evaluation:
        rows = [r for r in results if r.method == method]
        if not rows:
            raise ValueError(f"no results for method {method!r}")
        solved_rows = [r for r in rows if r.solved]
        mean_exp = (
            sum(r.expansions for r in solved_rows) / len(solved_rows)
            if solved_rows
            else None
        )
        return Evaluation(
            method=method,
            tasks=len(rows),
            solved=len(solved_rows),
            solve_rate=len(solved_rows) / len(rows),
            mean_expansions_solved=mean_exp,
            total_expansions=sum(r.expansions for r in rows),
            total_retries=sum(r.retries for r in rows),
            mean_score=sum(r.score for r in rows) / len(rows),
        )

    def evaluate_all(self, results: list[MethodResult]) -> list[Evaluation]:
        methods = sorted({r.method for r in results})
        return [self.evaluate(results, m) for m in methods]
