"""Deterministic input guardrails for TrackFlow CX support agent."""

from __future__ import annotations

import re
from typing import List, Optional

from services.agent.guardrails.metrics import guardrail_metrics
from services.agent.guardrails.models import FailureType, GuardrailAction, GuardrailResult

# Firm rejection message for jailbreak and instruction overrides
JAILBREAK_REJECTION_MESSAGE = (
    "Solicitud rechazada: Las directivas de seguridad y el system prompt de TrackFlow son "
    "estrictos e inmodificables. No está permitido omitir, anular o alterar las instrucciones operativas. "
    "Mi función exclusiva es brindar soporte de atención al cliente (CX) para TrackFlow en tracking, "
    "políticas de devolución e incidencias."
)

# Refusal and redirection for personal assistant misuse
PERSONAL_TASK_REJECTION_MESSAGE = (
    "Solicitud no admitida: Como agente de soporte de CX de TrackFlow, no puedo realizar tareas "
    "personales, redacción de ensayos, programación general ni asesoramiento personal. Mi servicio está "
    "dedicado exclusivamente a la operativa logística de TrackFlow: seguimiento de envíos, políticas "
    "de devolución, SLAs por país y gestión de incidencias. ¿Deseas consultar el estado de un envío "
    "o una política de devolución?"
)

# Refusal for unauthorized order access (Case 3 from CONTEXT)
UNAUTHORIZED_ORDER_MESSAGE = (
    "Acceso no autorizado: El pedido o número de seguimiento consultado no pertenece a tu sesión "
    "autenticada o no dispones de autorización para consultar sus datos. Por políticas de seguridad y "
    "protección de datos de TrackFlow, solo puedes consultar envíos vinculados a tu cuenta autenticada."
)

# Refusal for cross-country policy mixing (Case 4 from CONTEXT)
CROSS_COUNTRY_POLICY_MESSAGE = (
    "Operación no permitida: Las políticas de devolución y SLAs de TrackFlow están rigurosamente separadas "
    "por país. Los pedidos operados en Los Ángeles (Estados Unidos) se rigen exclusivamente por las normativas "
    "y SLAs de EE. UU., mientras que los pedidos en Zaragoza se rigen por las normativas de España. No es "
    "posible intercambiar o aplicar la política de España a envíos en Los Ángeles."
)


class JailbreakSecurityGuard:
    """Security Guard: Blocks prompt injection, jailbreaks and instruction override attempts."""

    name = "jailbreak_security_guard"

    PATTERNS = [
        # Direct instruction overrides
        r"ignore\s+(?:all\s+)?(?:your\s+)?previous\s+instructions",
        r"ignora\s+(?:todas\s+)?(?:tus\s+)?instrucciones(?:\s+anteriores)?",
        r"olvida\s+(?:todas\s+)?(?:tus\s+)?instrucciones",
        r"forget\s+(?:all\s+)?(?:your\s+)?instructions",
        # Unrestricted persona / no rules
        r"act\s+as\s+(?:an?\s+)?assistant\s+with\s+no\s+rules",
        r"act[úu]a\s+como\s+(?:un\s+)?asistente\s+sin\s+reglas",
        r"sin\s+filtros(?:\s+ni\s+reglas)?",
        r"without\s+any\s+restrictions",
        r"now\s+you\s+have\s+no\s+rules",
        r"you\s+are\s+now\s+(?:dan|unfiltered|free)",
        # Forgetting employer / identity
        r"olv[íi]date\s+de\s+trackflow",
        r"olvida\s+que\s+trabajas\s+para\s+(?:la\s+empresa|trackflow)",
        r"forget\s+(?:that\s+)?you\s+work\s+for\s+trackflow",
        # System prompt leakage / exfiltration
        r"(?:muestra|dime|revela|expon|print)\s+(?:tu\s+)?system\s*prompt",
        r"(?:revela|muestra)\s+(?:tus\s+)?instrucciones\s+(?:internas|del\s+sistema)",
        r"repeat\s+the\s+(?:text|instructions)\s+above",
        # Developer mode bypass
        r"(?:modo\s+desarrollador|developer\s+mode)\s+(?:activado|enabled|on)",
    ]

    def evaluate(self, question: str) -> GuardrailResult:
        q_clean = question.strip().lower()
        for pattern in self.PATTERNS:
            if re.search(pattern, q_clean, re.IGNORECASE):
                reason = f"Intento de inyección de prompt o anulación de instrucciones detectado: {pattern}"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    failure_type=FailureType.SECURITY,
                    reason=reason,
                    question_snippet=question,
                )
                return GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    passed=False,
                    failure_type=FailureType.SECURITY,
                    reason=reason,
                    response_message=JAILBREAK_REJECTION_MESSAGE,
                )

        return GuardrailResult(guard_name=self.name, passed=True)


class PersonalTaskGuard:
    """Content Guard: Blocks out-of-domain requests to use the agent as a personal assistant."""

    name = "personal_task_guard"

    PATTERNS = [
        # Academic / essays / homework
        r"(?:escribe|redacta|hazme|haz)\s+(?:un\s+)?ensayo",
        r"(?:ay[úu]dame\s+con\s+)?(?:mi\s+)?tarea\s+(?:de\s+(?:la\s+)?(?:universidad|colegio|escuela|instituto)|escolar|acad[ée]mica)",
        r"(?:escribe|hazme)\s+un\s+resumen\s+sobre\s+(?:la\s+segunda\s+guerra|historia|filosof[íi]a|literatura)",
        r"(?:escribe|redacta)\s+(?:una\s+)?tesis",
        # Creative writing / poetry / personal
        r"(?:escr[íi]beme|escribe|hazme|redacta)\s+(?:un\s+)?poema",
        r"(?:escr[íi]beme|escribe)\s+(?:una\s+)?carta\s+de\s+amor",
        r"(?:cu[ée]ntame|escribe)\s+(?:un\s+)?cuento(?:\s+para\s+niños)?",
        r"(?:escribe|compon)\s+(?:una\s+)?canci[óo]n",
        # Coding / general programming unrelated to TrackFlow
        r"(?:escribe|genera|hazme)\s+(?:c[óo]digo|un\s+script|una\s+funci[óo]n)\s+(?:en\s+|para\s+)(?:python|javascript|typescript|react|c\+\+|java)",
        r"(?:debuggea|arregla)\s+este\s+c[óo]digo",
        r"(?:programa|desarrolla)\s+(?:una\s+app|un\s+juego|una\s+web)",
        # Psychological / therapy / personal counseling
        r"(?:haz\s+de|act[úu]a\s+como)\s+(?:mi\s+)?(?:terapeuta|psic[óo]logo)",
        r"(?:dame\s+)?consejo\s+(?:sentimental|amoroso|de\s+pareja)",
        r"tengo\s+problemas\s+con\s+mi\s+pareja",
    ]

    def evaluate(self, question: str) -> GuardrailResult:
        q_clean = question.strip().lower()
        for pattern in self.PATTERNS:
            if re.search(pattern, q_clean, re.IGNORECASE):
                reason = f"Solicitud de uso como chatbot personal no relacionada con logística: {pattern}"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    question_snippet=question,
                )
                return GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.BLOCKED,
                    passed=False,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    response_message=PERSONAL_TASK_REJECTION_MESSAGE,
                )

        return GuardrailResult(guard_name=self.name, passed=True)


class SessionOrderAuthGuard:
    """Content Guard: Ensures tracking/order inquiries belong to the authenticated session (Case 3)."""

    name = "session_order_auth_guard"

    # Regex detecting order / tracking inquiries
    ORDER_PATTERN = re.compile(
        r"(?:pedido|order|env[íi]o|tracking|seguimiento)\s*(?:#|n[úu]mero|num)?\s*([a-zA-Z0-9\-]{4,15})",
        re.IGNORECASE,
    )

    def evaluate(
        self,
        question: str,
        authorized_orders: Optional[List[str]] = None,
        session_user: Optional[str] = None,
    ) -> GuardrailResult:
        match = self.ORDER_PATTERN.search(question)
        if not match:
            return GuardrailResult(guard_name=self.name, passed=True)

        extracted_order = match.group(1).strip().upper()
        # Clean potential prefix '#'
        clean_order_id = extracted_order.lstrip("#")

        # If authorized_orders is explicitly configured, check inclusion
        # By default, if an order ID is queried without corresponding session authorization, block it!
        auth_list = [str(o).strip().upper().lstrip("#") for o in (authorized_orders or [])]

        if clean_order_id and clean_order_id not in auth_list:
            reason = (
                f"Consulta de pedido #{clean_order_id} no autorizado para la sesión "
                f"autenticada '{session_user or 'anonymous'}'"
            )
            guardrail_metrics.record_evaluation(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                failure_type=FailureType.CONTENT,
                reason=reason,
                question_snippet=question,
            )
            return GuardrailResult(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                passed=False,
                failure_type=FailureType.CONTENT,
                reason=reason,
                response_message=UNAUTHORIZED_ORDER_MESSAGE,
            )

        return GuardrailResult(guard_name=self.name, passed=True)


class CrossCountryPolicyGuard:
    """Content Guard: Blocks attempts to cross or mix Spain vs US policies (Case 4)."""

    name = "cross_country_policy_guard"

    def evaluate(self, question: str) -> GuardrailResult:
        q_lower = question.lower()

        # Check for attempt to apply Spain policies to Los Angeles / US or vice versa
        applies_spain_to_la = (
            ("españa" in q_lower or "spain" in q_lower or "zaragoza" in q_lower)
            and ("los ángeles" in q_lower or "los angeles" in q_lower or "ee.uu" in q_lower or "estados unidos" in q_lower or "usa" in q_lower)
            and ("aplica" in q_lower or "aplicar" in q_lower or "cambia" in q_lower or "conviene" in q_lower or "usar" in q_lower)
        )

        if applies_spain_to_la:
            reason = "Intento de aplicar o mezclar políticas de devolución/SLA entre España y Los Ángeles (EE. UU.)"
            guardrail_metrics.record_evaluation(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                failure_type=FailureType.CONTENT,
                reason=reason,
                question_snippet=question,
            )
            return GuardrailResult(
                guard_name=self.name,
                action=GuardrailAction.BLOCKED,
                passed=False,
                failure_type=FailureType.CONTENT,
                reason=reason,
                response_message=CROSS_COUNTRY_POLICY_MESSAGE,
            )

        return GuardrailResult(guard_name=self.name, passed=True)


class CasualScopeGuard:
    """Scope Guard: Allows brief casual chat / general logistics but obligatorily redirects to TrackFlow."""

    name = "casual_scope_guard"

    GREETINGS_PATTERNS = [
        r"^(?:hola|buenos\s+d[íi]as|buenas\s+tardes|buenas\s+noches|saludos|hello|hi)[!.]*$",
        r"^(?:c[óo]mo\s+est[áa]s|qu[ée]\s+tal|how\s+are\s+you)[?.]*$",
    ]

    TRIVIA_PATTERNS = [
        r"qu[ée]\s+hora\s+es\s+en\s+([a-zA-ZáéíóúÁÉÍÓÚ\s]+)",
        r"qu[ée]\s+tiempo\s+hace\s+en",
    ]

    GENERAL_LOGISTICS_PATTERNS = [
        r"qu[ée]\s+es\s+la\s+log[íi]stica\s+inversa",
        r"qu[ée]\s+significa\s+sla",
        r"definici[óo]n\s+de\s+log[íi]stica\s+inversa",
    ]

    def evaluate(self, question: str) -> GuardrailResult:
        q_clean = question.strip().lower()

        # Check greetings
        for pattern in self.GREETINGS_PATTERNS:
            if re.search(pattern, q_clean, re.IGNORECASE):
                reason = "Saludo o small talk breve: respuesta cordial y reconducción obligatoria a TrackFlow"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    question_snippet=question,
                )
                msg = (
                    "¡Hola! Soy el asistente de atención al cliente (CX) de TrackFlow. "
                    "Estoy a tu disposición para ayudarte con el seguimiento de tus pedidos, "
                    "políticas de devolución en España o Estados Unidos, y gestión de incidencias. "
                    "¿En qué te puedo colaborar hoy con tus envíos?"
                )
                return GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    passed=True,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    response_message=msg,
                )

        # Check trivia (e.g. ¿qué hora es en Tokio?)
        for pattern in self.TRIVIA_PATTERNS:
            match = re.search(pattern, q_clean, re.IGNORECASE)
            if match:
                city = match.group(1).strip().title() if match.groups() else "esa ubicación"
                reason = f"Consulta de trivia/cultura general ({city}): respuesta breve y reconducción a TrackFlow"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    question_snippet=question,
                )
                msg = (
                    f"Respecto a la hora o huso horario en {city}, como asistente de soporte en tiempo "
                    f"real no monitoreo husos horarios externos en vivo. No obstante, te recuerdo que en "
                    f"TrackFlow operamos activamente bajo los husos horarios de nuestros almacenes centrales: "
                    f"PST (Pacífico) en Los Ángeles y CET (Centroeuropa) en Zaragoza para todos los despachos. "
                    f"¿Deseas consultar los plazos de entrega o el estado de un envío para alguno de estos destinos?"
                )
                return GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    passed=True,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    response_message=msg,
                )

        # Check general logistics (e.g. ¿qué es la logística inversa?)
        for pattern in self.GENERAL_LOGISTICS_PATTERNS:
            if re.search(pattern, q_clean, re.IGNORECASE):
                reason = "Pregunta de concepto logístico general: respuesta breve y reconducción a la operativa TrackFlow"
                guardrail_metrics.record_evaluation(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    question_snippet=question,
                )
                msg = (
                    "La logística inversa comprende el conjunto de procesos para la recogida, transporte, "
                    "inspección y reintegración o disposición de productos devueltos por el cliente final. "
                    "En TrackFlow aplicamos este concepto gestionando devoluciones B2B y B2C desde nuestros almacenes "
                    "de Los Ángeles y Zaragoza, con ventanas de 30 días e inspección especializada. "
                    "¿Deseas conocer la política de devolución específica para tu país o consultar un caso en particular?"
                )
                return GuardrailResult(
                    guard_name=self.name,
                    action=GuardrailAction.REDIRECTED,
                    passed=True,
                    failure_type=FailureType.CONTENT,
                    reason=reason,
                    response_message=msg,
                )

        return GuardrailResult(guard_name=self.name, passed=True)


# Instantiate guards
jailbreak_guard = JailbreakSecurityGuard()
personal_task_guard = PersonalTaskGuard()
session_order_auth_guard = SessionOrderAuthGuard()
cross_country_guard = CrossCountryPolicyGuard()
casual_scope_guard = CasualScopeGuard()


def evaluate_input_guards(
    question: str,
    *,
    authorized_orders: Optional[List[str]] = None,
    session_user: Optional[str] = None,
) -> GuardrailResult:
    """Evaluate all input guardrails sequentially.

    Order of evaluation:
    1. Security Guard: Jailbreak / instruction override (P0 - firm block)
    2. Content Guard: Personal task abuse (P1 - refusal + redirect)
    3. Content Guard: Cross-country policy mixing (P1 - refusal + clear country policy)
    4. Content Guard: Session order authorization (P1 - unauthorized order block)
    5. Scope Guard: Casual / small talk / general logistics (P2 - allowed + redirect)
    """
    # 1. Security Guard
    res = jailbreak_guard.evaluate(question)
    if not res.passed:
        return res

    # 2. Personal Task Guard
    res = personal_task_guard.evaluate(question)
    if not res.passed:
        return res

    # 3. Cross-Country Policy Guard
    res = cross_country_guard.evaluate(question)
    if not res.passed:
        return res

    # 4. Session Order Auth Guard
    res = session_order_auth_guard.evaluate(
        question, authorized_orders=authorized_orders, session_user=session_user
    )
    if not res.passed:
        return res

    # 5. Casual Scope Guard
    res = casual_scope_guard.evaluate(question)
    if res.action == GuardrailAction.REDIRECTED:
        return res

    return GuardrailResult(guard_name="input_guardrails_suite", passed=True)
