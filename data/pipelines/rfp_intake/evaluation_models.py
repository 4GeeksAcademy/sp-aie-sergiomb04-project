"""Structured EvaluationResult models for Milestone 9 - Part 2 (Response Generation & Evaluation)."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ReadabilityEvaluation(BaseModel):
    """Evaluation result for readability metrics."""

    pass_: bool = Field(..., alias="pass", description="Whether the draft meets readability thresholds.")
    score: float = Field(..., description="Flesch Reading Ease or primary readability score.")
    details: dict[str, Any] | str = Field(
        default_factory=dict,
        description="Detailed metrics (Flesch-Kincaid, Gunning Fog, word count, sentence count).",
    )

    model_config = {"populate_by_name": True}


class RelevanceEvaluation(BaseModel):
    """Evaluation result for relevance to the client RFP scope and key aspects."""

    pass_: bool = Field(..., alias="pass", description="Whether the draft covers requested scope and aspects.")
    missing_aspects: list[str] = Field(
        default_factory=list,
        description="Aspects or scope items requested in RFP that are missing from the draft.",
    )

    model_config = {"populate_by_name": True}


class ComplianceEvaluation(BaseModel):
    """Evaluation result for company business guidelines (§5 of BRIEFING)."""

    pass_: bool = Field(..., alias="pass", description="Whether the draft satisfies all 5 company rules.")
    rule_ids: list[str] = Field(
        default_factory=list,
        description="List of rule IDs checked against §5 of trackflow-BRIEFING.es.md.",
    )
    violations: list[str] = Field(
        default_factory=list,
        description="Specific violations found in the draft.",
    )

    model_config = {"populate_by_name": True}


class EvaluationResult(BaseModel):
    """Structured evaluation output conforming to Milestone 9 Part 2 contract.

    Schema:
      section_id / department_id: str
      readability: { pass: bool, score: float, details: dict | str }
      relevance: { pass: bool, missing_aspects: list[str] }
      compliance: { pass: bool, rule_ids: list[str], violations: list[str] }
      overall_pass: bool
      feedback_for_generator: str  # concrete and actionable
    """

    department_id: str = Field(..., description="Department identifier (warehouse, lastmile, reverse).")
    section_id: str | None = Field(default=None, description="DepartmentSection UUID if known.")
    readability: ReadabilityEvaluation = Field(..., description="Readability evaluation result.")
    relevance: RelevanceEvaluation = Field(..., description="Relevance evaluation result.")
    compliance: ComplianceEvaluation = Field(..., description="Compliance evaluation result.")
    overall_pass: bool = Field(..., description="True only if readability, relevance, and compliance all pass.")
    feedback_for_generator: str = Field(
        default="",
        description="Concrete and actionable feedback for the generator if any evaluation failed.",
    )

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to standard dictionary with 'pass' keys as expected by the spec."""
        return {
            "department_id": self.department_id,
            "section_id": self.section_id,
            "readability": {
                "pass": self.readability.pass_,
                "score": self.readability.score,
                "details": self.readability.details,
            },
            "relevance": {
                "pass": self.relevance.pass_,
                "missing_aspects": self.relevance.missing_aspects,
            },
            "compliance": {
                "pass": self.compliance.pass_,
                "rule_ids": self.compliance.rule_ids,
                "violations": self.compliance.violations,
            },
            "overall_pass": self.overall_pass,
            "feedback_for_generator": self.feedback_for_generator,
        }
