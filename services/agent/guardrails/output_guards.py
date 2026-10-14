"""Deterministic output guardrails for TrackFlow CX support agent."""

from __future__ import annotations

import re
from typing import Tuple

from services.agent.guardrails.metrics import guardrail_metrics
from services.agent.guardrails.models import FailureType, GuardrailAction, GuardrailResult


class OutputGuard:
    """Validates model output before returning to user.

    Defends against:
    - Structural failures (empty output, malformed responses).
    - Security failures (system prompt leakage, internal delimiters exposure).
    - Content failures (leakage of sensitive carrier negotiated rates, internal warehouse routes).
    """

    name = "output_guard"

    # Leakage patterns of internal system instructions
    PROMPT_LEAK_PATTERNS = [
        r"<<<SYSTEM_INSTRUCTIONS>>>",
        r"<<</SYSTEM_INSTRUCTIONS>>>",
        r"eres\s+un\s+account\s+manager\s+y\s+representante",
        r"normas\s+estrictas\s+de\s+negocio\s+que\s+debes\s+cumplir\s+siempre",
        r"untrusted_external_content",
    ]

    # Sensitive business data patterns (forbidden from disclosure per CONTEXT-trackflow.es.md)
    SENSITIVE_DATA_PATTERNS = [
        # Carrier negotiated rates / confidential margins
        (
            r"(?:tarifa|descuento|margen)\s+(?:negociad[oa]|confidencial|secreto)\s+con\s+(?:ups|fedex|dhl|mrw|seur)",
            "Intento de divulgación de tarifas comerciales confidenciales negociadas con transportistas",
        ),
        (
            r"(?:acuerdo|contrato)\s+privado\s+de\s+precios\s+con\s+(?:ups|fedex|dhl|mrw|seur)",
            "Intento de divulgación de contratos privados de precios con carriers",
        ),
        # Internal warehouse routes / physical security layouts
        (
            r"(?:ruta|pasillo|acceso)\s+intern[oa]\s+de\s+seguridad\s+del\s+almac[ée]n",
            "Intento de revelación de rutas internas o seguridad física de almacenes",
        ),
        (
            r"plano\s+(?:de\s+seguridad|interno|f[íi]sico)\s+del\s+almac[ée]n\s+de\s+(?:los\s+[áa]ngeles|zaragoza)",
            "Intento de revelación de planos de seguridad física de almacenes",
        ),
    ]

    def validate(self, output_text: str) -> Tuple[str, GuardrailResult]:
        """Validate output text. Returns sanitized output text and evaluation result."""
        # 1. Structural check
        if not output_text or not isinstance(output_text, str) or not output_text.strip():
            reason = "Respuesta vacía o de formato no textual generada por el agente"
            guardrail_metrics.record_evaluation(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                failure_type=FailureType.STRUCTURAL,
                reason=reason,
                question_snippet="",
            )
            fallback = (
                "Disculpa, se produjo una incidencia estructural en la respuesta. "
                "Por favor formula tu consulta nuevamente sobre las operaciones de TrackFlow."
            )
            return fallback, GuardrailResult(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                passed=False,
                failure_type=FailureType.STRUCTURAL,
                reason=reason,
                response_message=fallback,
            )

        clean_output = output_text.strip()
        lower_output = clean_output.lower()

        # 2. System prompt leakage check
        for pattern in self.PROMPT_LEAK_PATTERNS:
            if re.search(pattern, clean_output, re.IGNORECASE):
                reason = f"Detección de posible filtración de system prompt o directivas internas: {pattern}"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    failure_type=FailureType.SECURITY,
                    reason=reason,
                    question_snippet=clean_output[:100],
                )
                safe_msg = (
                    "Por motivos de seguridad y confidencialidad, las instrucciones internas de la plataforma "
                    "no están disponibles. ¿En qué puedo asistirte respecto a tus envíos o devoluciones en TrackFlow?"
                )
                return safe_msg, GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    passed=False,
                    failure_type=FailureType.SECURITY,
                    reason=reason,
                    response_message=safe_msg,
                )

        # 3. Sensitive data check (Carrier negotiated rates, internal warehouse security)
        for pattern, desc in self.SENSITIVE_DATA_PATTERNS:
            if re.search(pattern, lower_output, re.IGNORECASE):
                reason = desc
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    question_snippet=clean_output[:100],
                )
                redacted_msg = (
                    "Información restringida: Por políticas de confidencialidad y seguridad operativa de "
                    "TrackFlow, los acuerdos de tarifas negociadas con carriers y los planos o rutas internas "
                    "de los centros de distribución son de acceso estrictamente reservado. "
                    "Para consultas comerciales, contacta a tu Account Manager asignado."
                )
                return redacted_msg, GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    passed=False,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    response_message=redacted_msg,
                )

        # All output checks passed
        return clean_output, GuardrailResult(guard_name=self.name, passed=True)


output_guard = OutputGuard()


def validate_agent_output(output_text: str) -> Tuple[str, GuardrailResult]:
    """Helper entrypoint for output guard validation."""
    return output_guard.validate(output_text)
