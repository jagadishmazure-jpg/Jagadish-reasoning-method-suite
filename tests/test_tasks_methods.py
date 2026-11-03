"""Tasks, methods, harness fairness, evaluator, and reporter tests."""

import pytest

from reasoning_suite import (
    METHOD_NAMES,
    EvaluatorAgent,
    Harness,
    MethodRunner,
    Reporter,
    build_method,
    default_tasks,
    validate_budget,
)
from reasoning_suite.tasks import Task


# --- tasks ---------------------------------------------------------------

def test_default_task_set_has_twelve_tasks_with_unique_ids():
    tasks = default_tasks()
    assert len(tasks) == 12
    assert len({t.id for t in tasks}) == 12


def test_goal_path_length_matches_depth_and_branches_in_range():
    for task in default_tasks():
        assert len(task.goal_path) == task.depth
        assert all(0 <= b < task.branching for b in task.goal_path)


def test_goal_path_is_deterministic():
    tasks = default_tasks()
    again = default_tasks()
    assert [t.goal_path for t in tasks] == [t.goal_path for t in again]


def test_trap_paths_are_decoys_of_length_two():
    for task in default_tasks():
        assert len(task.trap_paths) <= task.traps
        for trap in task.trap_paths:
            assert len(trap) == 2
            assert trap[0] != task.goal_path[0]


def test_node_signal_goal_child_scores_two_and_range_is_bounded():
    task = default_tasks()[0]
    assert task.node_signal(task.goal_path[:1]) == 2
    for depth in range(1, task.depth + 1):
        assert 0 <= task.node_signal(task.goal_path[:depth]) <= 2


def test_validate_budget_rejects_negatives_and_accepts_zero():
    assert validate_budget(0) == 0
    assert validate_budget(400) == 400
    with pytest.raises(ValueError):
        validate_budget(-1)
    with pytest.raises(TypeError):
        validate_budget(1.5)


def test_task_rejects_bad_difficulty_branching_and_traps():
    base = dict(id="x", title="x", kind="k", difficulty=1, branching=2, depth=2, traps=0, budget=10)
    with pytest.raises(ValueError):
        Task(**{**base, "difficulty": 4})
    with pytest.raises(ValueError):
        Task(**{**base, "branching": 1})
    with pytest.raises(ValueError):
        Task(**{**base, "traps": -1})


# --- methods -------------------------------------------------------------

def test_all_five_methods_plus_broken_baseline_are_registered():
    assert set(METHOD_NAMES) == {
        "tree-search",
        "graph-search",
        "rewound-reasoning",
        "lookahead-search",
        "algorithm-of-thoughts",
        "broken-baseline",
    }


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        build_method("no-such-method")


def test_every_method_respects_its_budget():
    for name in METHOD_NAMES:
        for task in default_tasks():
            result = build_method(name).run(task)
            assert result.expansions <= task.budget
            assert isinstance(result.solved, bool)


def test_every_method_run_is_deterministic():
    for name in METHOD_NAMES:
        runner = build_method(name)
        for task in default_tasks():
            first = runner.run(task)
            second = runner.run(task)
            assert (first.solved, first.expansions, first.retries) == (
                second.solved,
                second.expansions,
                second.retries,
            )


def test_solved_run_path_equals_goal_path():
    for name in ("tree-search", "graph-search", "rewound-reasoning", "lookahead-search", "algorithm-of-thoughts"):
        for task in default_tasks():
            result = build_method(name).run(task)
            if result.solved:
                assert result.path == task.goal_path


def test_rewound_method_records_retries_on_trap_tasks():
    trap_tasks = [t for t in default_tasks() if t.traps > 0]
    assert trap_tasks
    retries = [build_method("rewound-reasoning").run(t).retries for t in trap_tasks]
    assert sum(retries) > 0


def test_tree_search_uses_more_expansions_than_rewound_on_trap_tasks():
    # Rewound prunes trap subtrees; plain DFS exhausts them. Aggregate check
    # only: per-task ordering is not guaranteed for every task shape.
    trap_tasks = [t for t in default_tasks() if t.traps > 0]
    tree_total = sum(build_method("tree-search").run(t).expansions for t in trap_tasks)
    rewound_total = sum(build_method("rewound-reasoning").run(t).expansions for t in trap_tasks)
    assert rewound_total < tree_total


# --- harness fairness (the point of this repo) ----------------------------

def test_swapping_method_order_does_not_change_scores():
    tasks = default_tasks()
    forward = Harness(tasks=tasks, methods=list(METHOD_NAMES)).run()
    reversed_ = Harness(tasks=tasks, methods=list(reversed(METHOD_NAMES))).run()
    forward_map = {(r.method, r.task_id): (r.solved, r.score, r.expansions) for r in forward}
    reversed_map = {(r.method, r.task_id): (r.solved, r.score, r.expansions) for r in reversed_}
    assert forward_map == reversed_map


def test_swapping_task_order_does_not_change_per_task_scores():
    tasks = default_tasks()
    forward = Harness(tasks=tasks).run()
    backward = Harness(tasks=list(reversed(tasks))).run()
    forward_map = {(r.method, r.task_id): (r.solved, r.score) for r in forward}
    backward_map = {(r.method, r.task_id): (r.solved, r.score) for r in backward}
    assert forward_map == backward_map


def test_deliberately_broken_method_scores_worst():
    results = Harness().run()
    evaluations = {e.method: e for e in EvaluatorAgent().evaluate_all(results)}
    broken = evaluations["broken-baseline"]
    assert broken.solved == 0
    assert all(broken.solved <= e.solved for e in evaluations.values())
    assert broken.solved < max(e.solved for e in evaluations.values())


def test_harness_rejects_unknown_methods_and_negative_budget_override():
    with pytest.raises(ValueError):
        Harness(methods=["nope"])
    with pytest.raises(ValueError):
        Harness(budget_override=-5)


def test_harness_budget_override_is_applied_to_every_run():
    results = Harness(budget_override=10).run()
    assert all(r.expansions <= 10 for r in results)


# --- evaluator and reporter ----------------------------------------------

def test_evaluator_counts_solved_and_rates_correctly():
    results = Harness().run()
    evaluation = EvaluatorAgent().evaluate(results, "tree-search")
    rows = [r for r in results if r.method == "tree-search"]
    assert evaluation.tasks == len(rows) == 12
    assert evaluation.solved == sum(1 for r in rows if r.solved)
    assert evaluation.solve_rate == pytest.approx(evaluation.solved / 12)
    assert evaluation.mean_score == pytest.approx(evaluation.solve_rate)


def test_evaluator_mean_expansions_is_none_when_nothing_solved():
    results = Harness().run()
    evaluation = EvaluatorAgent().evaluate(results, "broken-baseline")
    assert evaluation.solved == 0
    assert evaluation.mean_expansions_solved is None


def test_evaluator_raises_for_method_with_no_results():
    with pytest.raises(ValueError):
        EvaluatorAgent().evaluate([], "tree-search")


def test_reporter_ranks_by_solved_then_fewest_expansions():
    results = Harness().run()
    ranked = Reporter.rank(EvaluatorAgent().evaluate_all(results))
    keys = [(-e.solved, e.total_expansions) for e in ranked]
    assert keys == sorted(keys)
    assert ranked[-1].method == "broken-baseline"


def test_reporter_table_lists_every_method():
    results = Harness().run()
    table = Reporter.markdown_table(EvaluatorAgent().evaluate_all(results))
    for name in METHOD_NAMES:
        assert name in table
    assert table.startswith("| Method |")


def test_reporter_summary_names_best_and_worst():
    results = Harness().run()
    summary = Reporter.summary(EvaluatorAgent().evaluate_all(results))
    ranked = Reporter.rank(EvaluatorAgent().evaluate_all(results))
    assert ranked[0].method in summary
    assert ranked[-1].method in summary
