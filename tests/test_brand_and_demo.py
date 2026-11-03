"""Brand-check blocklist tests and the live demo-table test.

The demo test asserts the exact comparison numbers produced by the real
harness run. Those numbers are filled in from the actual run output (see
README); they are not hand-estimated. If the harness changes, this test
must be regenerated from a fresh run, not edited to match a guess.
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from brand_check import BLOCKLIST_HASHES, find_blocklisted  # noqa: E402

from reasoning_suite import EvaluatorAgent, Harness, Reporter  # noqa: E402


def test_brand_blocklist_is_non_empty():
    assert len(BLOCKLIST_HASHES) > 0


def test_brand_blocklist_entries_are_sha256_hex():
    for entry in BLOCKLIST_HASHES:
        assert len(entry) == 64
        int(entry, 16)  # must parse as hex


def test_brand_check_mechanism_flags_a_blocklisted_phrase():
    phrase = "zqx testphrase"
    custom = {hashlib.sha256(phrase.encode("utf-8")).hexdigest()}
    assert find_blocklisted(f"mention of {phrase} here", blocklist=custom)
    assert find_blocklisted("clean fictional text here", blocklist=custom) == []


def test_brand_check_passes_on_clean_fictional_text():
    assert find_blocklisted("Zindlewick Labs runs a synthetic reasoning study") == []


def test_demo_table_matches_live_harness_run():
    """Exact numbers from the real run; regenerated, never estimated."""
    results = Harness().run()
    evaluations = {e.method: e for e in EvaluatorAgent().evaluate_all(results)}
    table = Reporter.markdown_table(list(evaluations.values()))
    # Solved counts asserted exactly; the table row for each method must agree.
    expected_solved = {
        "tree-search": DEMO_SOLVED["tree-search"],
        "graph-search": DEMO_SOLVED["graph-search"],
        "rewound-reasoning": DEMO_SOLVED["rewound-reasoning"],
        "lookahead-search": DEMO_SOLVED["lookahead-search"],
        "algorithm-of-thoughts": DEMO_SOLVED["algorithm-of-thoughts"],
        "broken-baseline": 0,
    }
    for method, solved in expected_solved.items():
        assert evaluations[method].solved == solved
        assert evaluations[method].total_expansions == DEMO_TOTAL_EXPANSIONS[method]
        assert f"| {method} | {solved}/12 |" in table


# Filled in from the actual run output (scripts/run_demo.py, 2026-11-03):
# AoT 12/12, lookahead 10/12, rewound 9/12, tree 9/12, graph 8/12, broken 0/12.
DEMO_SOLVED: dict[str, int] = {
    "tree-search": 9,
    "graph-search": 8,
    "rewound-reasoning": 9,
    "lookahead-search": 10,
    "algorithm-of-thoughts": 12,
}
DEMO_TOTAL_EXPANSIONS: dict[str, int] = {
    "tree-search": 1922,
    "graph-search": 2395,
    "rewound-reasoning": 1828,
    "lookahead-search": 1311,
    "algorithm-of-thoughts": 1362,
    "broken-baseline": 40,
}
