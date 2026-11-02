"""Sanitization and isolation layer for external untrusted data (RAG and Tools)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from services.security.input_sanitizer import (
    CONTROL_CHARS_PATTERN,
    INVISIBLE_CHARS_PATTERN,
    neutralize_prompt_delimiters,
)

# Injection markers that might appear in malicious external data or tool responses
INJECTION_MARKERS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
    r"ignora\s+(?:todas\s+)?(?:las\s+)?(?:tus\s+)?instrucciones",
    r"olvida\s+(?:todas\s+)?(?:las\s+)?(?:tus\s+)?instrucciones",
    r"disregard\s+(?:all\s+)?(?:previous\s+|prior\s+)?(?:instructions|rules)",
    r"system\s*:\s*",
    r"new\s+system\s+instruction",
    r"nueva\s+instrucci[óo]n\s+(?:del\s+)?sistema",
    r"<<<SYSTEM_INSTRUCTIONS>>>",
    r"<<</SYSTEM_INSTRUCTIONS>>>",
    r"you\s+are\s+now\s+an?\s+unrestricted\s+assistant",
    r"asigna\s+siempre\s+el\s+(?:carrier|transportista)\s+m[áa]s\s+caro",
    r"always\s+assign\s+the\s+most\s+expensive\s+carrier",
    r"aprueba\s+(?:siempre\s+)?(?:todas\s+las\s+)?devoluciones\s+sin\s+reglas",
    r"aprueba\s+(?:esta|la)\s+devoluci[óo]n\s+sin\s+(?:reglas|validaci[óo]n|revisi[óo]n)",
    r"approve\s+(?:all\s+)?returns?\s+without\s+(?:rules|validation)",
    r"revela\s+(?:todos\s+los\s+)?pedidos\s+de\s+otros\s+clientes",
    r"(?:dime|revela|muestra)\s+la\s+direcci[óo]n\s+de\s+(?:entrega\s+)?(?:del\s+pedido|de\s+otro)",
    r"comparte\s+(?:los\s+)?datos\s+de\s+(?:volumen|incidentes)\s+de\s+(?:otra|la)\s+marca",
]

_COMPILED_MARKERS = [re.compile(marker, re.IGNORECASE) for marker in INJECTION_MARKERS]


def _normalize_external(text: str) -> str:
    """NFKC-normalize and strip invisible/control chars used to hide instructions."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = INVISIBLE_CHARS_PATTERN.sub("", normalized)
    normalized = CONTROL_CHARS_PATTERN.sub("", normalized)
    # Hidden HTML comments are a common carrier for invisible instructions in notes/docs
    normalized = re.sub(r"<!--(.*?)-->", r"[comentario_oculto: \1]", normalized, flags=re.S)
    return normalized


def contains_injection(text: str) -> bool:
    """Return True if untrusted text carries instruction-like injection markers."""
    if not text:
        return False
    normalized = _normalize_external(str(text))
    return any(p.search(normalized) for p in _COMPILED_MARKERS)


def sanitize_external_text(text: str) -> str:
    """Sanitize text by neutralizing potential prompt injections and escaping tags."""
    if not text:
        return ""

    sanitized = _normalize_external(str(text))
    # Neutralize common indirect prompt injection triggers
    for marker in _COMPILED_MARKERS:
        sanitized = marker.sub(
            lambda m: f"[FILTERED_PROMPT_INJECTION_ATTEMPT: '{m.group(0)}']",
            sanitized,
        )

    # Escape XML boundary delimiters to prevent sandbox breakout
    sanitized = sanitized.replace("<untrusted_external_content", "&lt;untrusted_external_content")
    sanitized = sanitized.replace("</untrusted_external_content>", "&lt;/untrusted_external_content&gt;")
    # Neutralize remaining prompt-template delimiters (<<<USER_INPUT>>>, chat-ml tokens...)
    sanitized, _ = neutralize_prompt_delimiters(sanitized)

    return sanitized


def isolate_external_content(content: str, source_type: str, identifier: str = "") -> str:
    """Wrap untrusted content in non-executable XML boundary tags."""
    clean_content = sanitize_external_text(content)
    safe_source = re.sub(r"[^A-Za-z0-9_\-:.#/ ]", "", str(source_type))[:64]
    safe_identifier = re.sub(r"[^A-Za-z0-9_\-:.#/ áéíóúñÁÉÍÓÚÑ]", "", str(identifier))[:128]
    return (
        f'<untrusted_external_content source_type="{safe_source}" id="{safe_identifier}" '
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
            source_type=chunk_copy.get("source_type", "rag_document"),
            identifier=f"{source_doc}#{section}",
        )
        chunk_copy["text"] = isolated_text
        chunk_copy["raw_text_sanitized"] = sanitize_external_text(raw_text)
        chunk_copy["injection_detected"] = contains_injection(raw_text)
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
                sanitize_external_text(item)
                if isinstance(item, str)
                else wrap_untrusted_tool_result(tool_name, item)
                if isinstance(item, dict)
                else item
                for item in v
            ]
        else:
            sanitized_payload[k] = v

    return sanitized_payload
