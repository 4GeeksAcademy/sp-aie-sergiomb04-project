"""Sanitization and isolation layer for external untrusted data (RAG and Tools)."""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Injection markers that might appear in malicious external data or tool responses
INJECTION_MARKERS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
    r"ignora\s+(?:todas\s+)?(?:las\s+)?instrucciones",
    r"system\s*:\s*",
    r"new\s+system\s+instruction",
    r"<<<SYSTEM_INSTRUCTIONS>>>",
    r"<<</SYSTEM_INSTRUCTIONS>>>",
    r"you\s+are\s+now\s+an?\s+unrestricted\s+assistant",
]


def sanitize_external_text(text: str) -> str:
    """Sanitize text by neutralizing potential prompt injections and escaping tags."""
    if not text:
        return ""

    sanitized = text
    # Neutralize common indirect prompt injection triggers
    for marker in INJECTION_MARKERS:
        sanitized = re.sub(
            marker,
            lambda m: f"[FILTERED_PROMPT_INJECTION_ATTEMPT: '{m.group(0)}']",
            sanitized,
            flags=re.IGNORECASE,
        )

    # Escape XML boundary delimiters to prevent sandbox breakout
    sanitized = sanitized.replace("<untrusted_external_content", "&lt;untrusted_external_content")
    sanitized = sanitized.replace("</untrusted_external_content>", "&lt;/untrusted_external_content&gt;")

    return sanitized


def isolate_external_content(content: str, source_type: str, identifier: str = "") -> str:
    """Wrap untrusted content in non-executable XML boundary tags."""
    clean_content = sanitize_external_text(content)
    return (
        f'<untrusted_external_content source_type="{source_type}" id="{identifier}" '
        f'executable="false" role="reference_only">\n'
        f"{clean_content}\n"
        f"</untrusted_external_content>"
    )


def wrap_untrusted_context(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize and isolate chunks retrieved from RAG knowledge base.

    Ensures retrieved text is treated strictly as reference data, never as system instructions.
    """
    sanitized_chunks = []
    for idx, chunk in enumerate(chunks, 1):
        chunk_copy = dict(chunk)
        raw_text = chunk_copy.get("text", "")
        source_doc = chunk_copy.get("source_document", "unknown")
        section = chunk_copy.get("section", "General")

        isolated_text = isolate_external_content(
            content=raw_text,
            source_type="rag_document",
            identifier=f"{source_doc}#{section}",
        )
        chunk_copy["text"] = isolated_text
        chunk_copy["raw_text_sanitized"] = sanitize_external_text(raw_text)
        sanitized_chunks.append(chunk_copy)

    return sanitized_chunks


def wrap_untrusted_tool_result(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and isolate output from external tools (e.g. MCP Server, incidents, inventory)."""
    if not isinstance(payload, dict):
        return {"data": sanitize_external_text(str(payload))}

    sanitized_payload = {}
    for k, v in payload.items():
        if isinstance(v, str):
            sanitized_payload[k] = sanitize_external_text(v)
        elif isinstance(v, dict):
            sanitized_payload[k] = wrap_untrusted_tool_result(tool_name, v)
        elif isinstance(v, list):
            sanitized_payload[k] = [
                sanitize_external_text(item) if isinstance(item, str) else item for item in v
            ]
        else:
            sanitized_payload[k] = v

    return sanitized_payload
