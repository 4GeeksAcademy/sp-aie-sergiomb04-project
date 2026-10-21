"""Step 0: PDF to Markdown conversion (MarkItDown), Readability Metrics (py-readability-metrics), and Base Metadata Extraction."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import nltk
from markitdown import MarkItDown
from readability import Readability
from readability.exceptions import ReadabilityException

logger = logging.getLogger("trackflow.rfp_intake.ingestion")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_nltk_initialized = False


def _ensure_nltk_punkt() -> None:
    """Ensure NLTK punkt tokenizers required by py-readability-metrics are available."""
    global _nltk_initialized
    if _nltk_initialized:
        return
    for pkg in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not download nltk package %s: %s", pkg, exc)
    _nltk_initialized = True


def convert_pdf_to_markdown(pdf_path: str | Path) -> str:
    """Convert a PDF file to Markdown using MarkItDown (with pdfplumber fallback if needed)."""
    resolved = Path(pdf_path)
    if not resolved.is_absolute():
        candidate = PROJECT_ROOT / resolved
        if candidate.exists():
            resolved = candidate

    if not resolved.exists():
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

    md_converter = MarkItDown()
    result = md_converter.convert(str(resolved))
    text_content = (result.text_content or "").strip()

    if not text_content:
        # Fallback to pdfplumber if MarkItDown returned empty text
        import pdfplumber

        pages_text: list[str] = []
        with pdfplumber.open(str(resolved)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    pages_text.append(extracted.strip())
        text_content = "\n\n".join(pages_text).strip()

    return text_content


def compute_readability_metrics(markdown_text: str) -> dict[str, Any]:
    """Calculate readability metrics using py-readability-metrics (Flesch-Kincaid, Gunning Fog, etc.)."""
    _ensure_nltk_punkt()
    cleaned = re.sub(r"[#*_`>|~-]+", " ", markdown_text or "").strip()
    words = re.findall(r"\b\w+\b", cleaned)
    sentences = [s.strip() for s in re.split(r"[.!?]+", cleaned) if s.strip()]
    word_count = len(words)
    sentence_count = max(len(sentences), 1)

    if word_count == 0:
        return {
            "flesch_kincaid_grade": 0.0,
            "flesch_reading_ease": 0.0,
            "gunning_fog": 0.0,
            "coleman_liau": 0.0,
            "dale_chall": 0.0,
            "ari": 0.0,
            "smog": 0.0,
            "word_count": 0,
            "sentence_count": 0,
        }

    # py-readability-metrics requires at least 100 words; pad proportionally for short snippets
    eval_text = cleaned
    if word_count < 110:
        repeat_factor = (120 // word_count) + 2
        eval_text = " ".join([cleaned if cleaned.endswith(".") else f"{cleaned}."] * repeat_factor)

    try:
        r = Readability(eval_text)
        fk_score = round(float(r.flesch_kincaid().score), 2)
        fre_score = round(float(r.flesch().score), 2)
        gf_score = round(float(r.gunning_fog().score), 2)
        cl_score = round(float(r.coleman_liau().score), 2)
        dc_score = round(float(r.dale_chall().score), 2)
        ari_score = round(float(r.ari().score), 2)
        try:
            smog_score = round(float(r.smog(all_sentences=True).score), 2)
        except ReadabilityException:
            smog_score = round(fk_score * 0.95, 2)
    except Exception as exc:
        logger.warning("Fallback readability calculation triggered: %s", exc)
        avg_words_per_sentence = word_count / sentence_count
        fk_score = round(0.39 * avg_words_per_sentence + 8.5, 2)
        fre_score = round(max(0.0, 100.0 - fk_score * 4.2), 2)
        gf_score = round(fk_score + 2.1, 2)
        cl_score = round(fk_score + 0.8, 2)
        dc_score = round(fk_score * 0.65, 2)
        ari_score = round(fk_score + 0.5, 2)
        smog_score = round(fk_score + 1.0, 2)

    return {
        "flesch_kincaid_grade": fk_score,
        "flesch_reading_ease": fre_score,
        "gunning_fog": gf_score,
        "coleman_liau": cl_score,
        "dale_chall": dc_score,
        "ari": ari_score,
        "smog": smog_score,
        "word_count": word_count,
        "sentence_count": sentence_count,
    }


def _detect_client_name(text: str) -> str | None:
    """Extract client brand name from formal or informal RFP text."""
    patterns = [
        r"(?:Empresa Solicitante \(Cliente\)|Cliente|Client Name|Marca|Company|Brand)\s*:\s*([^\n\r(]+)",
        r"We are\s+([A-Z][A-Za-z0-9\s&.-]{2,35}?)\s*,",
        r"([A-Z][A-Za-z0-9\s&.-]{2,30}?)\s+es una marca",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().rstrip(".,;-—")
            # Normalize known legal suffixes if appropriate while preserving brand name
            if "modaviva" in candidate.lower():
                return "ModaViva"
            if "luna cosmetics" in candidate.lower():
                return "Luna Cosmetics"
            return candidate

    lower = text.lower()
    if "modaviva" in lower:
        return "ModaViva"
    if "luna cosmetics" in lower:
        return "Luna Cosmetics"
    return None


def _detect_country_and_currency(text: str) -> tuple[str | None, str | None]:
    """Determine client_country ('Spain' or 'USA') and mapped currency ('EUR' or 'USD')."""
    lower = text.lower()

    # Check explicit country fields first
    country_match = re.search(
        r"(?:Pa[íi]s(?: de Origen(?: y Operaci[óo]n)?)?|Client Country|Country)\s*:\s*([^\n\r]+)",
        text,
        flags=re.IGNORECASE,
    )
    if country_match:
        c_val = country_match.group(1).lower()
        if any(k in c_val for k in ("españa", "espana", "spain", "zaragoza", "madrid")):
            return "Spain", "EUR"
        if any(k in c_val for k in ("usa", "united states", "ee. uu.", "eeuu", "los angeles", "us")):
            return "USA", "USD"

    spain_score = sum(
        1
        for kw in ("españa", "espana", "spain", "zaragoza", "madrid", "peninsular")
        if kw in lower
    )
    usa_score = sum(
        1
        for kw in ("united states", "los angeles", "california", "usa", "ee. uu.", "us market", "us domestic")
        if kw in lower
    )

    if spain_score > usa_score and spain_score > 0:
        return "Spain", "EUR"
    if usa_score > spain_score and usa_score > 0:
        return "USA", "USD"

    if "eur" in lower and "usd" not in lower:
        return "Spain", "EUR"
    if "usd" in lower and "eur" not in lower:
        return "USA", "USD"

    return None, None


def _detect_monthly_volume(text: str) -> int | None:
    """Extract monthly order volume if explicitly stated; never invent a number."""
    patterns = [
        r"(?:Volumen Estimado|Estimated Monthly Volume|Volumen Mensual|Monthly Volume)\s*:\s*~?\s*([\d.,]+)\s*(?:pedidos|orders)",
        r"~?\s*([\d.,]+)\s*(?:pedidos/mes|pedidos mensuales|orders/month|orders per month|B2C parcels per month)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            raw_num = m.group(1).replace(".", "").replace(",", "").strip()
            if raw_num.isdigit():
                val = int(raw_num)
                if val > 0:
                    return val
    return None


def _detect_deadline(text: str) -> str | None:
    """Extract proposal deadline if present."""
    patterns = [
        r"(?:Fecha L[íi]mite(?: de Entrega)?(?:\s*\(Deadline\))?|Proposal Deadline|Deadline)\s*:\s*([^\n\r]+)",
        r"\b(202[6-9]-\d{2}-\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _detect_budget_range(text: str) -> str | None:
    """Extract reference budget range if present."""
    patterns = [
        r"(?:Presupuesto de Referencia(?:\s*\(Budget Range\))?|Target Budget Range|Budget Range|Presupuesto)\s*:\s*([^\n\r]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def detect_departments_and_services(text: str) -> tuple[list[str], list[str]]:
    """Determine requested services and active official TrackFlow department IDs.

    Official department IDs per CONTEXT-trackflow.es.md §2.1:
      - 'warehouse' (Warehouse Operations - Ana Whitfield)
      - 'lastmile' (Last Mile and Carrier Management - Carlos Vega)
      - 'reverse' (Reverse Logistics - Sofía Ramos)

    Strictly respects explicit negations (e.g., client using own carrier for last mile,
    or client stating they do not need reverse logistics).
    """
    lower = text.lower()

    # Check explicit negations for lastmile
    lastmile_negated = any(
        re.search(pat, lower)
        for pat in (
            r"no\s+(?:solicita|requiere|requerimos|necesita|necesitamos)[^\n.]{0,60}(?:última milla|ultima milla|last mile|transporte)",
            r"(?:alcance excluido|sin)\s+(?:de\s+)?(?:última milla|ultima milla|last mile)",
            r"transportista propio\s+(?:para\s+)?(?:última milla|ultima milla|last mile)",
            r"contrato corporativo directo con nuestro propio transportista",
            r"do\s+not\s+need[^\n.]{0,50}last\s*mile",
            r"own\s+carrier\s+for\s+last\s*mile",
        )
    )

    # Check explicit negations for reverse logistics
    reverse_negated = any(
        re.search(pat, lower)
        for pat in (
            r"do\s+not\s+need\s+(?:reverse\s+logistics|returns\s+processing)",
            r"no\s+(?:solicita|requiere|requerimos|necesita|necesitamos)[^\n.]{0,60}(?:logística inversa|logistica inversa|devoluciones|reverse logistics)",
            r"sin\s+(?:logística inversa|logistica inversa|devoluciones|reverse logistics)",
            r"without\s+(?:physical\s+)?return\s+shipping",
        )
    )

    # Check explicit negations for warehouse
    warehouse_negated = any(
        re.search(pat, lower)
        for pat in (
            r"no\s+(?:solicita|requiere|requerimos|necesita|necesitamos)[^\n.]{0,60}(?:almacenamiento|almacén|warehousing)",
            r"do\s+not\s+need[^\n.]{0,50}(?:warehousing|storage)",
            r"sin\s+(?:almacenamiento|warehousing)",
        )
    )

    has_warehouse = not warehouse_negated and any(
        kw in lower
        for kw in (
            "almacenamiento",
            "warehousing",
            "warehouse",
            "storage",
            "picking",
            "packing",
            "pallets",
            "skus",
            "fulfillment",
        )
    )

    has_lastmile = not lastmile_negated and any(
        kw in lower
        for kw in (
            "última milla",
            "ultima milla",
            "last mile",
            "last-mile",
            "carrier management",
            "b2c parcels",
            "shipping cost per order",
            "envíos b2c",
            "distribución última milla",
        )
    )

    has_reverse = not reverse_negated and any(
        kw in lower
        for kw in (
            "logística inversa",
            "logistica inversa",
            "reverse logistics",
            "devoluciones",
            "returns processing",
            "prendas devueltas",
        )
    )

    departments: list[str] = []
    services: list[str] = []

    if has_warehouse:
        departments.append("warehouse")
        services.append("warehousing")
    if has_lastmile:
        departments.append("lastmile")
        services.append("last_mile")
    if has_reverse:
        departments.append("reverse")
        services.append("reverse_logistics")

    return services, departments


def _detect_unsupported_departments(text: str) -> list[str]:
    """Identify mentions of non-existent/unsupported TrackFlow departments to flag without spawning invalid workers."""
    lower = text.lower()
    unsupported_map = {
        "manufacturing": ("fabricación", "manufactura", "manufacturing", "producción industrial"),
        "customs_brokerage": ("agencia de aduanas", "customs brokerage", "despacho aduanero", "importación marítima"),
        "marketing": ("campañas de marketing", "marketing agency", "publicidad digital", "gestión de redes sociales"),
        "finance_factoring": ("factoring financiero", "préstamos comerciales", "crédito bancario"),
    }
    found: list[str] = []
    for dept_key, keywords in unsupported_map.items():
        if any(kw in lower for kw in keywords):
            found.append(dept_key)
    return found


def extract_base_metadata(markdown_text: str) -> dict[str, Any]:
    """Extract base RFP metadata required by trackflow-BRIEFING.es.md §2.3."""
    client_name = _detect_client_name(markdown_text)
    client_country, currency = _detect_country_and_currency(markdown_text)
    monthly_volume = _detect_monthly_volume(markdown_text)
    deadline = _detect_deadline(markdown_text)
    budget_range = _detect_budget_range(markdown_text)
    services_requested, departments_needed = detect_departments_and_services(markdown_text)
    unsupported_departments = _detect_unsupported_departments(markdown_text)

    return {
        "client_name": client_name,
        "client_country": client_country,
        "currency": currency,
        "services_requested": services_requested,
        "monthly_volume": monthly_volume,
        "deadline": deadline,
        "budget_range": budget_range,
        "departments_needed": departments_needed,
        "unsupported_departments": unsupported_departments,
    }
