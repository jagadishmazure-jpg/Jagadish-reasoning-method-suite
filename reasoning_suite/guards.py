"""Guardrails: PII redaction and human-approval gates.

PII redaction checklist (all of these, not just phone/SSN): phone numbers,
SSN-style numbers, card numbers (13-19 digit sequences, spaced or dashed),
and email addresses. Redaction replaces each match with a fixed placeholder;
it never echoes the matched value back.

Confirmation gates: an approval is valid only when it names a person, is
single-use, matches the requested scope exactly, and has not expired. The
gate additionally rejects low-confidence approvals and self-contradicting
consent such as "yes, wait, no". Every rejection path -- bypass (no
approval presented), reject (wrong scope / expired / already used), and
absent (no approval record at all) -- is covered by tests.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def redact_pii(text: str) -> str:
    """Mask email, card, phone, and SSN values in ``text``."""
    redacted = _EMAIL_RE.sub("[EMAIL]", text)
    redacted = _SSN_RE.sub("[SSN]", redacted)
    # Card numbers before phone numbers: a long digit run is a card, not a phone.
    redacted = _CARD_RE.sub("[CARD]", redacted)
    redacted = _PHONE_RE.sub("[PHONE]", redacted)
    return redacted


class ApprovalError(ValueError):
    """Raised whenever a confirmation gate refuses an action."""


@dataclass
class Approval:
    approver: str  # named person, e.g. "Priya Nair"
    scope: str
    token: str
    expires_at: float
    used: bool = False


def _is_self_contradicting(consent_text: str) -> bool:
    lowered = consent_text.strip().lower()
    has_yes = bool(re.search(r"\byes\b", lowered))
    has_no = bool(re.search(r"\bno\b", lowered))
    has_wait = bool(re.search(r"\bwait\b", lowered))
    # "yes, wait, no" and any yes+no mix in one utterance contradict themselves.
    return (has_yes and has_no) or (has_yes and has_wait and has_no) or (has_wait and has_no and has_yes)


class ConfirmationGate:
    """A named-person, single-use, scoped, expiring approval gate."""

    def __init__(self, ttl_seconds: float = 300.0, min_confidence: float = 0.7) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        self.ttl_seconds = ttl_seconds
        self.min_confidence = min_confidence
        self._approvals: dict[str, Approval] = {}

    def request(self, approver: str, scope: str, token: str, now: float | None = None) -> Approval:
        if not approver or not approver.strip():
            raise ApprovalError("approval requires a named approver")
        if not scope or not scope.strip():
            raise ApprovalError("approval requires a non-empty scope")
        if not token:
            raise ApprovalError("approval requires a token")
        approval = Approval(
            approver=approver.strip(),
            scope=scope.strip(),
            token=token,
            expires_at=(time.time() if now is None else now) + self.ttl_seconds,
        )
        self._approvals[token] = approval
        return approval

    def confirm(
        self,
        token: str | None,
        scope: str,
        confidence: float,
        consent_text: str,
        now: float | None = None,
    ) -> Approval:
        """Validate one approval. Raises ApprovalError on any failure."""
        if token is None or token == "":
            raise ApprovalError("bypass rejected: no approval token presented")
        approval = self._approvals.get(token)
        if approval is None:
            raise ApprovalError("absent approval: no approval record for this token")
        if approval.used:
            raise ApprovalError("rejected: approval token already used (single-use)")
        current = time.time() if now is None else now
        if current > approval.expires_at:
            raise ApprovalError("rejected: approval expired")
        if approval.scope != scope:
            raise ApprovalError(
                f"rejected: approval scope {approval.scope!r} does not match requested scope {scope!r}"
            )
        if confidence < self.min_confidence:
            raise ApprovalError(
                f"rejected: low confidence {confidence} below threshold {self.min_confidence}"
            )
        if _is_self_contradicting(consent_text):
            raise ApprovalError(
                "rejected: self-contradicting consent (contains both agreement and refusal)"
            )
        lowered = consent_text.strip().lower()
        if not re.search(r"\byes\b", lowered):
            raise ApprovalError("rejected: consent text does not contain an affirmation")
        approval.used = True
        return approval
