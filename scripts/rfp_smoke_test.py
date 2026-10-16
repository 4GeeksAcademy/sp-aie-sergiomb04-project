"""Standalone CLI for smoke testing and manual reprocessing of TrackFlow RFP PDFs (Milestone 9)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
for p in (str(PROJECT_ROOT), str(API_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.pipelines.rfp_intake import run_rfp_intake_pipeline  # noqa: E402
from scripts.generate_sample_rfps import generate_all_seed_pdfs  # noqa: E402


def process_single_pdf(pdf_source: Path, ticket_id: str | None = None) -> dict:
    """Copy a PDF into data/raw/<ticket_id>.pdf and execute the RFP intake pipeline."""
    tid = ticket_id or str(uuid4())
    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest_path = raw_dir / f"{tid}.pdf"
    shutil.copyfile(pdf_source, dest_path)

    rel_path = f"data/raw/{tid}.pdf"
    return run_rfp_intake_pipeline(
        ticket_id=tid,
        pdf_path=rel_path,
        original_filename=pdf_source.name,
    )


def run_all_smoke_tests() -> int:
    """Run smoke tests on all 3 official TrackFlow seed PDFs and verify outcomes."""
    generate_all_seed_pdfs()
    seed_dir = PROJECT_ROOT / "rfp-requests" / "trackflow"

    cases = [
        (
            "CONTEXT-trackflow-request-1.pdf",
            "analisis_completo",
            ["warehouse", "reverse"],
            "EUR",
        ),
        (
            "CONTEXT-trackflow-request-2.pdf",
            "analisis_completo",
            ["warehouse", "lastmile"],
            "USD",
        ),
        (
            "CONTEXT-trackflow-request-3.pdf",
            "descartado",
            [],
            None,
        ),
    ]

    summary_results = []
    for filename, expected_status, expected_depts, expected_currency in cases:
        pdf_path = seed_dir / filename
        result = process_single_pdf(pdf_path)
        actual_status = result.get("status")
        actual_depts = result.get("metadata", {}).get("departments_needed", [])
        actual_currency = result.get("metadata", {}).get("currency")

        assert actual_status == expected_status, (
            f"[{filename}] Expected status '{expected_status}', got '{actual_status}'"
        )
        if expected_status == "analisis_completo":
            assert set(actual_depts) == set(expected_depts), (
                f"[{filename}] Expected departments {expected_depts}, got {actual_depts}"
            )
            assert actual_currency == expected_currency, (
                f"[{filename}] Expected currency '{expected_currency}', got '{actual_currency}'"
            )
            assert result.get("handoff_payload", {}).get("ready_for_part_2") is True

        summary_results.append(
            {
                "file": filename,
                "ticket_id": result["ticket_id"],
                "status": actual_status,
                "client_name": result.get("metadata", {}).get("client_name"),
                "client_country": result.get("metadata", {}).get("client_country"),
                "currency": actual_currency,
                "departments_needed": actual_depts,
                "readability_flesch_kincaid": result.get("readability_metrics", {}).get(
                    "flesch_kincaid_grade"
                ),
            }
        )

    print(json.dumps({"smoke_test_status": "PASSED", "results": summary_results}, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TrackFlow RFP Intake Smoke Test & Reprocessing CLI")
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Optional path to a specific PDF file to process manually.",
    )
    parser.add_argument(
        "--ticket-id",
        type=str,
        default=None,
        help="Optional ticket_id to re-process.",
    )
    args = parser.parse_args()

    if args.pdf:
        src = Path(args.pdf)
        if not src.exists():
            print(f"Error: PDF file not found: {src}", file=sys.stderr)
            return 1
        res = process_single_pdf(src, ticket_id=args.ticket_id)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    return run_all_smoke_tests()


if __name__ == "__main__":
    raise SystemExit(main())
