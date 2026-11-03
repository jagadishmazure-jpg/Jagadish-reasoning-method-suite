"""Reporter: turns evaluations into the comparison table.

Ranking rule, stated once and applied to every method: most tasks solved
first, then fewest total expansions. The table is plain text/markdown so it
can be pasted into the README without any tooling, and the numbers in it
are exactly the numbers the evaluator computed -- the reporter formats, it
never re-scores.
"""

from __future__ import annotations

from .evaluator import Evaluation


class Reporter:
    """Render evaluations as a markdown comparison table."""

    @staticmethod
    def rank(evaluations: list[Evaluation]) -> list[Evaluation]:
        return sorted(
            evaluations, key=lambda e: (-e.solved, e.total_expansions, e.method)
        )

    @staticmethod
    def markdown_table(evaluations: list[Evaluation]) -> str:
        ranked = Reporter.rank(evaluations)
        lines = [
            "| Method | Solved | Solve rate | Mean expansions (solved) | Total expansions | Retries |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for e in ranked:
            mean_exp = f"{e.mean_expansions_solved:.1f}" if e.mean_expansions_solved is not None else "n/a"
            lines.append(
                f"| {e.method} | {e.solved}/{e.tasks} | {e.solve_rate:.2f} | "
                f"{mean_exp} | {e.total_expansions} | {e.total_retries} |"
            )
        return "\n".join(lines)

    @staticmethod
    def summary(evaluations: list[Evaluation]) -> str:
        ranked = Reporter.rank(evaluations)
        best = ranked[0]
        worst = ranked[-1]
        return (
            f"Best: {best.method} ({best.solved}/{best.tasks} solved, "
            f"{best.total_expansions} total expansions). "
            f"Worst: {worst.method} ({worst.solved}/{worst.tasks} solved, "
            f"{worst.total_expansions} total expansions)."
        )
