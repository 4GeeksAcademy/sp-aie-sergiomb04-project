"""Tests for Human-in-the-Loop (HITL) gate and Tool Call / SQL validation (NIST Protect & Respond).

Covers section 5 of trackflow-BRIEFING.es.md (irreversible action controls).
"""

import pytest
from services.security.hitl import (
    ActionStatus,
    ApprovalPermissionError,
    CriticalActionType,
    HumanApprovalGate,
    HumanApprovalRequiredError,
)
from services.security.tool_call_validator import (
    validate_generated_code,
    validate_generated_sql,
    validate_tool_call,
)


class TestHumanInTheLoop:
    """Verifies that irreversible actions cannot execute autonomously."""

    def test_return_above_threshold_requires_human_approval(self):
        """Returns above the monetary threshold require explicit human sign-off."""
        gate = HumanApprovalGate()
        record = gate.submit(
            CriticalActionType.RETURN_APPROVAL,
            {"order_id": "ORD-123", "amount": 250.0, "currency": "EUR"},
            requested_by="agent:cx",
        )
        assert record.requires_human is True
        assert record.status == ActionStatus.PENDING_HUMAN_APPROVAL

        executed = False

        def do_execute(payload):
            nonlocal executed
            executed = True
            return "refund_issued"

        # Attempt to execute without approval -> blocked
        with pytest.raises(HumanApprovalRequiredError):
            gate.execute(record.action_id, do_execute)
        assert executed is False

        # Human operator approves
        gate.approve(record.action_id, approver="sofia.ramos@trackflow.tech", note="Devolución validada")
        result = gate.execute(record.action_id, do_execute)
        assert result == "refund_issued"
        assert executed is True

    def test_automated_actor_cannot_approve(self):
        """Automated agents / engines cannot approve their own or other critical actions."""
        gate = HumanApprovalGate()
        record = gate.submit(
            CriticalActionType.HIGH_VALUE_DISPATCH,
            {"shipment_id": "SHP-999", "declared_value": 5000.0},
            requested_by="engine:carrier",
        )
        with pytest.raises(ApprovalPermissionError):
            gate.approve(record.action_id, approver="agent:support-agent")

    def test_four_eyes_principle_enforced(self):
        """The requester cannot be the approver."""
        gate = HumanApprovalGate()
        record = gate.submit(
            CriticalActionType.CARRIER_CHANGE,
            {"shipment_id": "SHP-100", "shipment_status": "in_transit"},
            requested_by="operator.carlos@trackflow.tech",
        )
        with pytest.raises(ApprovalPermissionError):
            gate.approve(record.action_id, approver="operator.carlos@trackflow.tech")


class TestToolCallAndSQLValidation:
    """Verifies safety filters on model-generated tool calls, code and SQL."""

    def test_critical_tools_redirect_to_hitl(self):
        """Model cannot directly invoke approve_return or confirm_dispatch."""
        res = validate_tool_call("approve_return", {"amount": 500})
        assert res.allowed is False
        assert res.requires_human_approval is True
        assert res.critical_action_type == "return_approval"

    def test_malicious_tool_arguments_blocked(self):
        """Dangerous shell / command injection payloads inside tool arguments are rejected."""
        malicious = {
            "action": "get",
            "incident_id": "TRF-001; rm -rf /; $(cat /etc/passwd)",
        }
        res = validate_tool_call("manage_incidents", malicious)
        assert res.allowed is False
        assert any("peligroso" in err for err in res.errors)

    def test_sql_validation_only_allows_single_select(self):
        """Rejects multi-statement or non-SELECT queries."""
        valid, _ = validate_generated_sql("SELECT id, status FROM incidents WHERE id = 1")
        assert valid is True

        # Drop statement
        invalid_drop, _ = validate_generated_sql("DROP TABLE users")
        assert invalid_drop is False

        # Multi-statement injection
        invalid_multi, _ = validate_generated_sql("SELECT 1; UPDATE users SET role = 'admin'")
        assert invalid_multi is False

    def test_code_execution_disabled_by_policy(self):
        """Agent has zero code execution privileges."""
        allowed, reason = validate_generated_code("import os; os.system('ls')")
        assert allowed is False
        assert "deshabilitada" in reason
