"""Cross-cutting AI security controls for TrackFlow (NIST AI RMF / CSF 2.0 alignment).

Modules:
- `secret_store`: strict secret loading from environment / vault (no hardcoded fallbacks).
- `input_sanitizer`: validation and sanitization of user input before the LLM context.
- `rate_limiter`: request + token budget limiting for LLM-backed endpoints.
- `tool_call_validator`: schema/safety validation of model-generated tool calls and SQL.
- `hitl`: Human-in-the-Loop gate for irreversible actions (briefing section 5).
- `agent_telemetry`: structured, PII-redacted logs of agent reasoning, actions and tool calls.

See `docs/NIST-AUDIT.md` for the full assessment.
"""
