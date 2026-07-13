#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from domain.analyzer import analyze_csv, render_report
from domain.exporter import write_export_csv


EXPECTED_CONTEXT_VALUES: Dict[str, Any] = {
    "total_records": 100,
    "valid_records": 95,
    "invalid_records": 5,
    "invalid_breakdown": {
        "invalid_tracking": 1,
        "invalid_carrier": 1,
        "invalid_category": 1,
        "invalid_email": 1,
        "closed_missing_score": 1,
    },
    "by_category": {
        "LOST_PARCEL": 14,
        "DELAYED_DELIVERY": 38,
        "WRONG_ADDRESS": 19,
        "RETURN_REQUEST": 17,
        "DAMAGE": 7,
    },
    "by_status": {
        "OPEN": 29,
        "CLOSED": 52,
        "DISCARDED": 14,
    },
    "by_country": {
        "US": 50,
        "ES": 45,
    },
    "satisfaction": {
        "scored_incidents": 52,
        "closed_incidents": 52,
        "average": 3.06,
        "counts": {
            "1": 6,
            "2": 11,
            "3": 15,
            "4": 14,
            "5": 6,
        },
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze TrackFlow incidents CSV and produce summary metrics."
    )
    parser.add_argument("csv_path", help="Path to input CSV file")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output JSON analysis to stdout",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip interactive export prompt",
    )
    parser.add_argument(
        "--export-path",
        type=str,
        help="Write export CSV to this path",
    )
    parser.add_argument(
        "--verify-context",
        action="store_true",
        help="Verify exact expected values defined in CONTEXT-company.md",
    )
    return parser


def compare_section(
    section_name: str,
    actual: Dict[str, Any],
    expected: Dict[str, Any],
    mismatches: List[str],
) -> None:
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            mismatches.append(
                f"{section_name}.{key}: expected={expected_value} actual={actual_value}"
            )


def verify_context_values(result_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    mismatches: List[str] = []

    for root_key in ["total_records", "valid_records", "invalid_records"]:
        expected_value = EXPECTED_CONTEXT_VALUES[root_key]
        actual_value = result_payload.get(root_key)
        if actual_value != expected_value:
            mismatches.append(
                f"{root_key}: expected={expected_value} actual={actual_value}"
            )

    compare_section(
        "invalid_breakdown",
        result_payload.get("invalid_breakdown", {}),
        EXPECTED_CONTEXT_VALUES["invalid_breakdown"],
        mismatches,
    )
    compare_section(
        "by_category",
        result_payload.get("by_category", {}),
        EXPECTED_CONTEXT_VALUES["by_category"],
        mismatches,
    )
    compare_section(
        "by_status",
        result_payload.get("by_status", {}),
        EXPECTED_CONTEXT_VALUES["by_status"],
        mismatches,
    )
    compare_section(
        "by_country",
        result_payload.get("by_country", {}),
        EXPECTED_CONTEXT_VALUES["by_country"],
        mismatches,
    )

    actual_satisfaction = result_payload.get("satisfaction", {})
    expected_satisfaction = EXPECTED_CONTEXT_VALUES["satisfaction"]
    for key in ["scored_incidents", "closed_incidents", "average"]:
        expected_value = expected_satisfaction[key]
        actual_value = actual_satisfaction.get(key)
        if actual_value != expected_value:
            mismatches.append(
                f"satisfaction.{key}: expected={expected_value} actual={actual_value}"
            )

    compare_section(
        "satisfaction.counts",
        {str(key): value for key, value in actual_satisfaction.get("counts", {}).items()},
        expected_satisfaction["counts"],
        mismatches,
    )

    return (len(mismatches) == 0, mismatches)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists() or not csv_path.is_file():
        print(f"Error: CSV file not found: {csv_path}")
        return 1

    try:
        result = analyze_csv(csv_path)
    except Exception as error:  # pragma: no cover - terminal entrypoint
        print(f"Error while analyzing CSV: {error}")
        return 1

    if args.export_path:
        write_export_csv(result, Path(args.export_path).resolve())

    if args.verify_context:
        result_payload = result.to_dict()
        is_valid, mismatches = verify_context_values(result_payload)
        if is_valid:
            print("CONTEXT VALIDATION: PASS")
            return 0

        print("CONTEXT VALIDATION: FAIL")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        return 2

    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=True))
        return 0

    print(render_report(result))

    if args.no_prompt:
        return 0

    answer = input("Export results to CSV? [y / n]: ").strip().lower()
    if answer == "y":
        destination = Path("incidents-analysis-results.csv").resolve()
        write_export_csv(result, destination)
        print(f"Exported CSV to: {destination}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
