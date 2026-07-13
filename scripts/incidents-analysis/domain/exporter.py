from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from .analyzer import AnalysisResult, compute_percentages


def build_export_rows(result: AnalysisResult) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    rows.extend(
        [
            {"section": "totals", "metric": "total_records", "value": str(result.total_records)},
            {"section": "totals", "metric": "valid_records", "value": str(result.valid_records)},
            {"section": "totals", "metric": "invalid_records", "value": str(result.invalid_records)},
        ]
    )

    for rule, value in result.invalid_breakdown.items():
        rows.append(
            {
                "section": "invalid_breakdown",
                "metric": rule,
                "value": str(value),
            }
        )

    category_percentages = compute_percentages(result.by_category, result.valid_records)
    for category, value in result.by_category.items():
        rows.append(
            {
                "section": "category",
                "metric": category,
                "value": str(value),
                "percentage": f"{category_percentages[str(category)]:.1f}",
            }
        )

    status_percentages = compute_percentages(result.by_status, result.valid_records)
    for status, value in result.by_status.items():
        rows.append(
            {
                "section": "status",
                "metric": status,
                "value": str(value),
                "percentage": f"{status_percentages[str(status)]:.1f}",
            }
        )

    country_percentages = compute_percentages(result.by_country, result.valid_records)
    for country, value in result.by_country.items():
        rows.append(
            {
                "section": "country",
                "metric": country,
                "value": str(value),
                "percentage": f"{country_percentages[str(country)]:.1f}",
            }
        )

    rows.extend(
        [
            {
                "section": "satisfaction",
                "metric": "scored_incidents",
                "value": str(result.scored_incidents),
            },
            {
                "section": "satisfaction",
                "metric": "closed_incidents",
                "value": str(result.closed_incidents),
            },
            {
                "section": "satisfaction",
                "metric": "average_satisfaction",
                "value": f"{result.average_satisfaction:.2f}",
            },
        ]
    )

    for score, value in result.satisfaction_counts.items():
        rows.append(
            {
                "section": "satisfaction_distribution",
                "metric": f"score_{score}",
                "value": str(value),
            }
        )

    return rows


def write_export_csv(result: AnalysisResult, destination: Path) -> None:
    rows = build_export_rows(result)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["section", "metric", "value", "percentage"]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
