"""Observability and metrics tracking for TrackFlow agent guardrails."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.agent.guardrails.models import FailureType, GuardrailAction

logger = logging.getLogger("trackflow.agent.guardrails")


class GuardrailMetricsTracker:
    """Thread-safe tracker for guardrail activations, blocks and redirections."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_checks: int = 0
        self._total_passed: int = 0
        self._total_blocked: int = 0
        self._total_redirected: int = 0
        self._activations_by_failure_type: Dict[str, int] = {
            FailureType.STRUCTURAL.value: 0,
            FailureType.CONTENT.value: 0,
            FailureType.SECURITY.value: 0,
        }
        self._activations_by_guard: Dict[str, int] = {}
        self._events: List[Dict[str, Any]] = []

    def record_evaluation(
        self,
        guard_name: str,
        action: GuardrailAction,
        failure_type: Optional[FailureType] = None,
        reason: Optional[str] = None,
        question_snippet: Optional[str] = None,
    ) -> None:
        """Record an evaluation event and log accordingly."""
        with self._lock:
            self._total_checks += 1
            if action == GuardrailAction.PASSED:
                self._total_passed += 1
                return

            if action == GuardrailAction.BLOCKED:
                self._total_blocked += 1
            elif action == GuardrailAction.REDIRECTED:
                self._total_redirected += 1

            # Count by guard
            self._activations_by_guard[guard_name] = (
                self._activations_by_guard.get(guard_name, 0) + 1
            )

            # Count by failure type
            if failure_type:
                ft_val = failure_type.value
                self._activations_by_failure_type[ft_val] = (
                    self._activations_by_failure_type.get(ft_val, 0) + 1
                )

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guard_name": guard_name,
                "action": action.value,
                "failure_type": failure_type.value if failure_type else None,
                "reason": reason,
                "question_snippet": question_snippet[:100] if question_snippet else "",
            }
            self._events.append(event)

            # Log with structured prefix for observability
            logger.warning(
                "[GUARDRAIL_ACTIVATION] action=%s guard=%s failure_type=%s reason=%s snippet=%r",
                action.value,
                guard_name,
                failure_type.value if failure_type else "NONE",
                reason,
                question_snippet[:80] if question_snippet else "",
            )

    def get_summary(self) -> Dict[str, Any]:
        """Return a structured summary of guardrail activations."""
        with self._lock:
            return {
                "total_checks": self._total_checks,
                "total_passed": self._total_passed,
                "total_blocked": self._total_blocked,
                "total_redirected": self._total_redirected,
                "activations_by_failure_type": dict(self._activations_by_failure_type),
                "activations_by_guard": dict(self._activations_by_guard),
                "recent_events": list(self._events[-50:]),
            }

    def reset(self) -> None:
        """Reset metrics (useful for testing sessions)."""
        with self._lock:
            self._total_checks = 0
            self._total_passed = 0
            self._total_blocked = 0
            self._total_redirected = 0
            self._activations_by_failure_type = {
                FailureType.STRUCTURAL.value: 0,
                FailureType.CONTENT.value: 0,
                FailureType.SECURITY.value: 0,
            }
            self._activations_by_guard.clear()
            self._events.clear()


# Global singleton instance
guardrail_metrics = GuardrailMetricsTracker()
