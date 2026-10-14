"""Data models and failure classifications for TrackFlow agent guardrails."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class FailureType(str, Enum):
    """Categorization of agent failure modes according to harness specification."""

    STRUCTURAL = "ESTRUCTURAL"
    CONTENT = "CONTENIDO"
    SECURITY = "SEGURIDAD"


class GuardrailAction(str, Enum):
    """Action taken by a guardrail upon inspecting input or output."""

    PASSED = "PASSED"
    REDIRECTED = "REDIRECTED"
    BLOCKED = "BLOCKED"


class GuardrailResult(BaseModel):
    """Result of a guardrail inspection."""

    action: GuardrailAction = Field(default=GuardrailAction.PASSED)
    passed: bool = Field(default=True)
    failure_type: Optional[FailureType] = Field(default=None)
    guard_name: str = Field(..., description="Identifier of the guardrail")
    reason: Optional[str] = Field(default=None, description="Explanation of block or redirection")
    response_message: Optional[str] = Field(
        default=None, description="Standard response returned to the user when not passed"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "passed": self.passed,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "guard_name": self.guard_name,
            "reason": self.reason,
            "response_message": self.response_message,
            "metadata": self.metadata,
        }
