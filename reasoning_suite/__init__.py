"""Reasoning-method comparison suite.

A measurement instrument, not another reasoning framework: the same small
synthetic task set is run through several deterministic simulated reasoning
methods on one identical harness (same tasks, same scoring, same budgets).

All example organisations and people in this package are fictional.
"""

from .tasks import Task, default_tasks, validate_budget
from .methods import MethodRunner, METHOD_NAMES, build_method
from .harness import Harness, MethodResult, run_all
from .evaluator import EvaluatorAgent, Evaluation
from .reporter import Reporter
from .guards import redact_pii, ConfirmationGate, ApprovalError
from .audit import HashChainedAuditLog

__all__ = [
    "Task",
    "default_tasks",
    "validate_budget",
    "MethodRunner",
    "METHOD_NAMES",
    "build_method",
    "Harness",
    "MethodResult",
    "run_all",
    "EvaluatorAgent",
    "Evaluation",
    "Reporter",
    "redact_pii",
    "ConfirmationGate",
    "ApprovalError",
    "HashChainedAuditLog",
]
