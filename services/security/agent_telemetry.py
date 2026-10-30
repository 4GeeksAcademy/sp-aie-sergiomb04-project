"""Structured agent telemetry: reasoning, actions and tool calls (NIST Detect).

Emits one JSON line per event on logger `trackflow.agent.telemetry` so that it can
be shipped to the centralized logging stack and correlated by `run_id` / `thread_id`.
PII (emails, phone numbers, street addresses) is redacted before logging to comply
with RGPD data minimization and CCPA/CPRA.

Event types:
- `agent.run.start` / `agent.run.end`: run envelope with latency and outcome.
- `agent.reasoning`: routing decision and the deterministic rationale behind it.
- `agent.step`: every graph node executed (duration + output summary).
- `agent.tool_call`: tool invoked, validated arguments, validation result, latency.
- `agent.guardrail`: guardrail blocks / redirections.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

telemetry_logger = logging.getLogger("trackflow.agent.telemetry")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<![\w-])\+?\d[\d\s().-]{7,}\d(?![\w-])")
ADDRESS_PATTERN = re.compile(
    r"\b(?:calle|c/|avenida|avda\.?|av\.|plaza|paseo|street|st\.|avenue|ave\.|road|rd\.|blvd)\s+[^,\n]{2,60}",
    re.I,
)

MAX_FIELD_CHARS = 500

# In-memory ring buffer to allow tests and support staff to inspect recent events
_recent_events: List[Dict[str, Any]] = []
_MAX_RECENT = 500


def redact_pii(text: str) -> str:
    """Mask emails, phone numbers and street addresses."""
    if not isinstance(text, str):
        return text
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    text = ADDRESS_PATTERN.sub("[ADDRESS_REDACTED]", text)
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    return text


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        redacted = redact_pii(value)
        return redacted if len(redacted) <= MAX_FIELD_CHARS else redacted[:MAX_FIELD_CHARS] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(v) for v in list(value)[:50]]
    return value


def log_agent_event(
    event_type: str,
    *,
    run_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    level: int = logging.INFO,
    **fields: Any,
) -> Dict[str, Any]:
    """Emit a structured JSON telemetry event and return it."""
    event: Dict[str, Any] = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "thread_id": thread_id,
    }
    event.update({k: _sanitize_value(v) for k, v in fields.items()})
    telemetry_logger.log(level, json.dumps(event, ensure_ascii=False, default=str))
    _recent_events.append(event)
    if len(_recent_events) > _MAX_RECENT:
        del _recent_events[: len(_recent_events) - _MAX_RECENT]
    return event


def get_recent_events(
    event_type: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent telemetry events filtered by type and/or thread."""
    events = list(_recent_events)
    if event_type:
        events = [e for e in events if e.get("event") == event_type]
    if thread_id:
        events = [e for e in events if e.get("thread_id") == thread_id]
    return events


def clear_recent_events() -> None:
    _recent_events.clear()
