"""PII redaction, confirmation-gate, and hash-chained audit tests."""

import pytest

from reasoning_suite import ApprovalError, ConfirmationGate, HashChainedAuditLog, redact_pii


# --- PII redaction: the checklist covers card + email, not just phone/SSN ---

def test_redacts_email_address():
    text = redact_pii("contact priya@example.org for details")
    assert "priya@example.org" not in text
    assert "[EMAIL]" in text


def test_redacts_card_number_plain():
    text = redact_pii("card 4111111111111111 charged")
    assert "4111111111111111" not in text
    assert "[CARD]" in text


def test_redacts_card_number_spaced_and_dashed():
    assert "[CARD]" in redact_pii("card 4111 1111 1111 1111 charged")
    assert "[CARD]" in redact_pii("card 4111-1111-1111-1111 charged")


def test_redacts_phone_number():
    text = redact_pii("call 555-123-4567 tomorrow")
    assert "555-123-4567" not in text
    assert "[PHONE]" in text


def test_redacts_ssn_style_number():
    text = redact_pii("ssn 123-45-6789 on file")
    assert "123-45-6789" not in text
    assert "[SSN]" in text


def test_redacts_all_pii_types_in_one_note():
    note = "Priya (priya@example.org, 555-123-4567, 123-45-6789) paid with 4111111111111111."
    redacted = redact_pii(note)
    for leaked in ("priya@example.org", "555-123-4567", "123-45-6789", "4111111111111111"):
        assert leaked not in redacted
    for placeholder in ("[EMAIL]", "[PHONE]", "[SSN]", "[CARD]"):
        assert placeholder in redacted


def test_clean_text_is_unchanged():
    assert redact_pii("The lab opens at nine.") == "The lab opens at nine."


# --- confirmation gate: bypass, reject, absent, low-confidence, contradiction ---

def _gate():
    return ConfirmationGate(ttl_seconds=300.0, min_confidence=0.7)


def test_gate_happy_path_returns_named_approval():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    approval = gate.confirm("tok-1", "publish-table", 0.9, "yes, publish it", now=1010.0)
    assert approval.approver == "Priya Nair"


def test_gate_bypass_with_no_token_is_rejected():
    gate = _gate()
    with pytest.raises(ApprovalError, match="bypass"):
        gate.confirm(None, "publish-table", 0.9, "yes", now=1000.0)
    with pytest.raises(ApprovalError, match="bypass"):
        gate.confirm("", "publish-table", 0.9, "yes", now=1000.0)


def test_gate_absent_approval_record_is_rejected():
    gate = _gate()
    with pytest.raises(ApprovalError, match="absent"):
        gate.confirm("never-issued", "publish-table", 0.9, "yes", now=1000.0)


def test_gate_wrong_scope_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError, match="scope"):
        gate.confirm("tok-1", "delete-table", 0.9, "yes", now=1010.0)


def test_gate_expired_approval_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError, match="expired"):
        gate.confirm("tok-1", "publish-table", 0.9, "yes", now=2000.0)


def test_gate_token_is_single_use():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    gate.confirm("tok-1", "publish-table", 0.9, "yes", now=1010.0)
    with pytest.raises(ApprovalError, match="already used"):
        gate.confirm("tok-1", "publish-table", 0.9, "yes", now=1020.0)


def test_gate_low_confidence_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError, match="low confidence"):
        gate.confirm("tok-1", "publish-table", 0.5, "yes", now=1010.0)


def test_gate_self_contradicting_consent_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError, match="self-contradicting"):
        gate.confirm("tok-1", "publish-table", 0.9, "yes, wait, no", now=1010.0)


def test_gate_yes_and_no_mix_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError, match="self-contradicting"):
        gate.confirm("tok-1", "publish-table", 0.9, "yes, but no", now=1010.0)


def test_gate_consent_without_affirmation_is_rejected():
    gate = _gate()
    gate.request("Priya Nair", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError):
        gate.confirm("tok-1", "publish-table", 0.9, "maybe later", now=1010.0)


def test_gate_requires_named_approver_and_scope():
    gate = _gate()
    with pytest.raises(ApprovalError):
        gate.request("", "publish-table", "tok-1", now=1000.0)
    with pytest.raises(ApprovalError):
        gate.request("Priya Nair", "", "tok-1", now=1000.0)


# --- hash-chained audit ----------------------------------------------------

def test_audit_chain_verifies_for_a_clean_log():
    log = HashChainedAuditLog()
    log.append("run", "tree-search", "t01", True)
    log.append("run", "graph-search", "t01", False)
    assert len(log.entries()) == 2
    assert log.verify() is True


def test_audit_tampered_payload_breaks_verification():
    log = HashChainedAuditLog()
    log.append("run", "tree-search", "t01", True)
    entry = log.entries()[0]
    object.__setattr__(entry, "payload", entry.payload.replace("true", "false"))
    assert log.verify() is False


def test_audit_broken_link_breaks_verification():
    log = HashChainedAuditLog()
    log.append("run", "tree-search", "t01", True)
    second = log.append("run", "graph-search", "t01", False)
    object.__setattr__(second, "prev_hash", "0" * 64)
    assert log.verify() is False


def test_audit_entry_indices_are_sequential_and_chained():
    log = HashChainedAuditLog()
    first = log.append("run", "tree-search", "t01", True)
    second = log.append("run", "tree-search", "t02", True)
    assert first.index == 0
    assert second.index == 1
    assert second.prev_hash == first.entry_hash
    assert log.verify() is True
