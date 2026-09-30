"""Explicit intention classifier for pending memory proposal responses.

Classifies user replies into APPROVE, REJECT, EDIT, or AMBIGUOUS_OR_UNRELATED without naive substring matching.
Extracts remaining substantive queries when the user responds to a proposal and asks a new question in the same turn.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field

from services.agent.memory.models import ProposalIntent

logger = logging.getLogger("trackflow.agent.memory.classifier")


class IntentClassificationResult(BaseModel):
    """Result of classifying a user's response to a pending memory proposal."""

    intent: ProposalIntent = Field(..., description="Classified intent.")
    confidence: float = Field(..., description="Confidence score [0.0 - 1.0].")
    edited_content: Optional[str] = Field(None, description="Modified rule text if user edited.")
    remaining_query: Optional[str] = Field(
        None, description="Subsequent question or command if user chained an action."
    )
    explanation: str = Field(..., description="Explanation of classification rationale.")


class ProposalIntentClassifier:
    """Classifies user messages against pending memory proposals using deterministic semantic rules."""

    # Explicit affirmative indicators (must not be preceded by negation words like 'no', 'nunca', 'jamás')
    APPROVE_PATTERNS = [
        r"^(?:sí|si|claro|afirmativo|de\s+acuerdo|confirmo|correcto|adelante|aprobado|guárdalo|guardalo|recuérdalo|recuerdalo|por\s+favor\s+recuérdalo|perfecto\s+recuérdalo)\b",
        r"\b(?:sí|si),\s*(?:por\s+favor|recuérdalo|guardalo|adelante|hazlo)\b",
        r"\b(?:recuérdalo|guardalo|aprobado)\b",
    ]

    # Ambiguity / uncertainty indicators (must be checked before reject)
    AMBIGUOUS_PATTERNS = [
        r"\b(?:no\s+s[ée]|no\s+estoy\s+segur[oa]|tal\s+vez|quiz[áa]s|no\s+lo\s+s[ée]|ni\s+idea|depende|ya\s+veremos)\b",
    ]

    # Explicit negative indicators
    REJECT_PATTERNS = [
        r"^(?:no|negativo|cancela|cancelar|descarta|descartalo|descártalo|olvídalo|olvidalo|para\s+nada|rechazado)\b",
        r"\b(?:no\s+lo\s+(?:recuerdes|guardes|anotes)|no\s+hace\s+falta|no\s+es\s+necesario|no,\s*gracias)\b",
    ]

    # Edit indicators
    EDIT_PATTERNS = [
        r"\b(?:sí\s+pero|si\s+pero|cámbialo\s+a|cambialo\s+a|edítalo\s+como|editalo\s+como|mejor\s+guarda|mejor\s+recuerda|solo\s+si)\b",
    ]

    def classify(self, message: str, proposed_summary: str = "") -> IntentClassificationResult:
        """Classify user's message against a pending memory proposal.

        Enforces:
        - Naive matches like 'sí' inside 'así' or 'no' inside 'notificación' are strictly rejected via word boundaries.
        - Negative intent overrides affirmative words (e.g. 'No, no lo recuerdes' is classified as REJECT, not APPROVE).
        - If ambiguous, off-topic, or silence -> AMBIGUOUS_OR_UNRELATED with default discard.
        """
        clean = message.strip()
        lower = clean.lower()

        # Check for explicit ambiguity/uncertainty first
        for pat in self.AMBIGUOUS_PATTERNS:
            if re.search(pat, lower):
                return IntentClassificationResult(
                    intent=ProposalIntent.AMBIGUOUS_OR_UNRELATED,
                    confidence=0.90,
                    edited_content=None,
                    remaining_query=clean,
                    explanation="User expressed uncertainty or ambiguity; resolves to default discard.",
                )

        # Check for rejection to prevent negative phrases with affirmative words from misclassifying
        for pat in self.REJECT_PATTERNS:
            if re.search(pat, lower):
                # Check if there is a remaining query after the rejection
                # e.g., "No, no hace falta. ¿Cuál es el stock de CLT-SNK-W-42?"
                remaining = self._extract_remaining_query(clean, is_affirmative=False)
                return IntentClassificationResult(
                    intent=ProposalIntent.REJECT,
                    confidence=0.95,
                    edited_content=None,
                    remaining_query=remaining,
                    explanation="User explicitly rejected memory proposal.",
                )

        # Check for edit
        for pat in self.EDIT_PATTERNS:
            match = re.search(pat, lower)
            if match:
                edit_text = clean[match.end():].strip().lstrip(":-,")
                return IntentClassificationResult(
                    intent=ProposalIntent.EDIT,
                    confidence=0.90,
                    edited_content=edit_text or clean,
                    remaining_query=None,
                    explanation="User requested an edit to the memory proposal.",
                )

        # Check for approval
        for pat in self.APPROVE_PATTERNS:
            if re.search(pat, lower):
                # Ensure no negation phrase was present earlier in the sentence
                if not re.search(r"\bno\b", lower[:15]):
                    remaining = self._extract_remaining_query(clean, is_affirmative=True)
                    return IntentClassificationResult(
                        intent=ProposalIntent.APPROVE,
                        confidence=0.95,
                        edited_content=None,
                        remaining_query=remaining,
                        explanation="User explicitly approved memory proposal.",
                    )

        # Ambiguous or completely unrelated (e.g. user changed topic or asked a new question directly)
        return IntentClassificationResult(
            intent=ProposalIntent.AMBIGUOUS_OR_UNRELATED,
            confidence=0.85,
            edited_content=None,
            remaining_query=clean,  # The whole message is treated as the new question/topic
            explanation="User did not clearly approve or reject; topic change or ambiguity resolves to default discard.",
        )

    def _extract_remaining_query(self, message: str, is_affirmative: bool) -> Optional[str]:
        """Split confirmation/rejection prefix from any trailing question or task."""
        # Split by punctuation or line breaks
        parts = re.split(r"[.!?\n]+", message)
        if len(parts) > 1:
            candidate = ".".join(parts[1:]).strip()
            # If candidate contains meaningful content
            if len(candidate) > 4:
                return candidate

        # Check for common conjunctions: "Sí, por favor, y además dime..."
        conjunction_split = re.split(r",?\s*(?:y\s+ahora|y\s+además|además|por\s+cierto|dime|cuál|cuanto|cuánto)\b", message, flags=re.IGNORECASE)
        if len(conjunction_split) > 1:
            trailing = message[len(conjunction_split[0]):].strip().lstrip(",. ")
            if len(trailing) > 4:
                return trailing

        return None


# Singleton classifier
intent_classifier = ProposalIntentClassifier()
