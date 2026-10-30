"""Explicit validation and sanitization of user input before it reaches the LLM context.

NIST Protect - Sanitización de Entradas. Applied to every user message that enters
the support agent (HTTP `/agent/query`, WebSocket chat and `/knowledge/query`).

Steps (deterministic, no LLM involved):
1. Type and length validation (rejects oversized payloads -> cost and DoS control).
2. Unicode NFKC normalization (folds full-width / compatibility homoglyphs).
3. Removal of invisible characters (zero-width, BOM, bidi overrides) used to hide
   instructions from human reviewers or to split keywords and evade guardrails.
4. Removal of ASCII control characters (except newline / tab).
5. Neutralization of prompt boundary delimiters used by the secure prompt template
   (`<<<SYSTEM_INSTRUCTIONS>>>`, `<<<USER_INPUT>>>`, `<untrusted_external_content>` ...),
   so a user can never close its own block and open a fake system block.
6. Whitespace collapsing.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List

DEFAULT_MAX_INPUT_CHARS = 2000

# Zero-width, BOM, word-joiner, soft hyphen and bidi override/isolate characters
INVISIBLE_CHARS_PATTERN = re.compile(
    "[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]"
)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Prompt boundary delimiters that only the system is allowed to emit
DELIMITER_PATTERNS = [
    re.compile(r"<<<\s*/?\s*(?:END[_\s]+)?(?:SYSTEM_INSTRUCTIONS|USER_INPUT|UNTRUSTED_REFERENCE_DATA)[^>]*>>>", re.I),
    re.compile(r"<<<\s*End\s+of\s+SYSTEM_INSTRUCTIONS\s*>>>", re.I),
    re.compile(r"</?\s*untrusted_external_content[^>]*>", re.I),
    re.compile(r"</?\s*(?:system|assistant|developer)\s*>", re.I),
    re.compile(r"\[/?(?:INST|SYS)\]", re.I),
    re.compile(r"<\|(?:im_start|im_end|system|endoftext)\|>", re.I),
]

NEUTRALIZED_DELIMITER = "[delimitador_neutralizado]"


class InputValidationError(ValueError):
    """Raised when user input violates hard validation rules (type, emptiness, size)."""


@dataclass
class SanitizedInput:
    """Result of sanitizing a user message."""

    text: str
    original_length: int
    removed_invisible_chars: int = 0
    removed_control_chars: int = 0
    neutralized_delimiters: int = 0
    flags: List[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return bool(self.flags)


def neutralize_prompt_delimiters(text: str) -> tuple[str, int]:
    """Replace reserved prompt delimiters with an inert marker. Returns (text, count)."""
    total = 0
    for pattern in DELIMITER_PATTERNS:
        text, count = pattern.subn(NEUTRALIZED_DELIMITER, text)
        total += count
    return text, total


def sanitize_user_input(
    raw: object,
    *,
    max_chars: int = DEFAULT_MAX_INPUT_CHARS,
    allow_empty: bool = False,
) -> SanitizedInput:
    """Validate and sanitize a raw user message before adding it to the LLM context.

    Raises:
        InputValidationError: if input is not a string, empty (unless allowed) or too long.
    """
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise InputValidationError("La consulta debe ser texto.")

    original_length = len(raw)
    if original_length > max_chars:
        raise InputValidationError(
            f"La consulta supera el máximo permitido de {max_chars} caracteres."
        )

    flags: List[str] = []
    text = unicodedata.normalize("NFKC", raw)
    if text != raw:
        flags.append("unicode_normalized")

    text, invisible = INVISIBLE_CHARS_PATTERN.subn("", text)
    if invisible:
        flags.append("invisible_chars_removed")

    text, control = CONTROL_CHARS_PATTERN.subn("", text)
    if control:
        flags.append("control_chars_removed")

    text, delimiters = neutralize_prompt_delimiters(text)
    if delimiters:
        flags.append("prompt_delimiters_neutralized")

    # Collapse horizontal whitespace, keep at most two consecutive newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text and not allow_empty:
        raise InputValidationError("La pregunta no puede estar vacía o contener solo espacios.")

    return SanitizedInput(
        text=text,
        original_length=original_length,
        removed_invisible_chars=invisible,
        removed_control_chars=control,
        neutralized_delimiters=delimiters,
        flags=flags,
    )
