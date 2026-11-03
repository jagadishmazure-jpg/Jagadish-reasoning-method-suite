#!/usr/bin/env python3
"""Run the full comparison and print the Reporter table.

Usage: ``python3 scripts/run_demo.py`` from the repo root.
All numbers printed here are computed live from the harness; the README
table is a copy of this output, regenerated after every real run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reasoning_suite import EvaluatorAgent, Harness, Reporter  # noqa: E402

if __name__ == "__main__":
    results = Harness().run()
    evaluations = EvaluatorAgent().evaluate_all(results)
    print(Reporter.markdown_table(evaluations))
    print()
    print(Reporter.summary(evaluations))
