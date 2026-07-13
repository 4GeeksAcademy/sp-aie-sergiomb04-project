from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .constants import (
    CARRIERS_BY_COUNTRY,
    CATEGORIES,
    COUNTRIES,
    CUSTOMER_TYPES,
    INVALID_RULES,
    REPORT_RULE_ORDER,
    REQUIRED_FIELDS,
    STATUSES,
)

INCIDENT_ID_RE = re.compile(r"^TRF-\d{6}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class AnalysisResult:
    source_file: str
    total_records: int
    valid_records: int
    invalid_records: int
    invalid_breakdown: Dict[str, int]
    by_category: Dict[str, int]
    by_status: Dict[str, int]
    by_country: Dict[str, int]
    satisfaction_counts: Dict[int, int]
    scored_incidents: int
    closed_incidents: int
    average_satisfaction: float

    def to_dict(self) -> Dict[str, object]:
        category_percentages = compute_percentages(self.by_category, self.valid_records)
        status_percentages = compute_percentages(self.by_status, self.valid_records)
        country_percentages = compute_percentages(self.by_country, self.valid_records)

        return {
            "source_file": self.source_file,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "invalid_breakdown": self.invalid_breakdown,
            "by_category": self.by_category,
            "category_percentages": category_percentages,
            "by_status": self.by_status,
            "status_percentages": status_percentages,
            "by_country": self.by_country,
            "country_percentages": country_percentages,
            "satisfaction": {
                "counts": self.satisfaction_counts,
                "scored_incidents": self.scored_incidents,
                "closed_incidents": self.closed_incidents,
                "average": self.average_satisfaction,
            },
        }


def normalize(value: object) -> str:
    return str(value or "").strip()


def is_valid_email(value: str) -> bool:
    return bool(value) and "@" in value


def validate_row(row: Dict[str, str]) -> List[str]:
    issues: List[str] = []

    country = normalize(row.get("country"))
    customer_type = normalize(row.get("customer_type"))
    status = normalize(row.get("status"))
    category = normalize(row.get("category"))
    carrier = normalize(row.get("carrier"))
    tracking_number = normalize(row.get("tracking_number"))
    description = normalize(row.get("description"))
    email = normalize(row.get("customer_email"))
    incident_id = normalize(row.get("incident_id"))
    date = normalize(row.get("date"))
    score_raw = normalize(row.get("satisfaction_score"))

    if not country or country not in COUNTRIES:
        issues.append("invalid_country")

    if not customer_type or customer_type not in CUSTOMER_TYPES:
        issues.append("invalid_customer_type")

    if not status or status not in STATUSES:
        issues.append("invalid_status")

    if not category or category not in CATEGORIES:
        issues.append("invalid_category")

    if not tracking_number or len(tracking_number) < 8:
        issues.append("invalid_tracking")

    if not description or len(description) < 5:
        issues.append("invalid_description")

    if not is_valid_email(email):
        issues.append("invalid_email")

    if not incident_id or not INCIDENT_ID_RE.match(incident_id):
        issues.append("invalid_incident_id")

    if not date or not DATE_RE.match(date):
        issues.append("invalid_date")

    if country in CARRIERS_BY_COUNTRY:
        if not carrier or carrier not in CARRIERS_BY_COUNTRY[country]:
            issues.append("invalid_carrier")
    elif carrier:
        issues.append("invalid_carrier")

    if status == "CLOSED":
        if not score_raw:
            issues.append("closed_missing_score")
        else:
            try:
                score_value = int(score_raw)
                if score_value < 1 or score_value > 5:
                    issues.append("score_out_of_range")
            except ValueError:
                issues.append("score_out_of_range")
    elif score_raw:
        try:
            score_value = int(score_raw)
            if score_value < 1 or score_value > 5:
                issues.append("score_out_of_range")
        except ValueError:
            issues.append("score_out_of_range")

    return issues


def read_csv_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("El CSV no contiene encabezados")

        missing_headers = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
        if missing_headers:
            raise ValueError(
                "Faltan columnas requeridas en el CSV: " + ", ".join(missing_headers)
            )

        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({key: normalize(value) for key, value in row.items()})
        return rows


def analyze_rows(rows: List[Dict[str, str]], source_file: str) -> AnalysisResult:
    invalid_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    country_counter: Counter[str] = Counter()
    satisfaction_counter: Counter[int] = Counter()

    valid_count = 0
    invalid_count = 0
    closed_incidents = 0

    for row in rows:
        issues = validate_row(row)
        if issues:
            invalid_count += 1
            for issue in issues:
                if issue in INVALID_RULES:
                    invalid_counter[issue] += 1
            continue

        valid_count += 1
        category = row["category"]
        status = row["status"]
        country = row["country"]

        category_counter[category] += 1
        status_counter[status] += 1
        country_counter[country] += 1

        if status == "CLOSED":
            closed_incidents += 1
            score_value = int(row["satisfaction_score"])
            satisfaction_counter[score_value] += 1

    scored_incidents = sum(satisfaction_counter.values())
    weighted_score = sum(score * count for score, count in satisfaction_counter.items())
    average_score = (weighted_score / scored_incidents) if scored_incidents else 0.0

    invalid_breakdown: Dict[str, int] = {
        key: invalid_counter.get(key, 0)
        for key in REPORT_RULE_ORDER
        if invalid_counter.get(key, 0) > 0
    }

    for key in REPORT_RULE_ORDER:
        if key not in invalid_breakdown and key in {
            "invalid_tracking",
            "invalid_carrier",
            "invalid_category",
            "invalid_email",
            "closed_missing_score",
        }:
            invalid_breakdown[key] = 0

    by_category = {category: category_counter.get(category, 0) for category in CATEGORIES}
    by_status = {status: status_counter.get(status, 0) for status in ["OPEN", "CLOSED", "DISCARDED"]}
    by_country = {country: country_counter.get(country, 0) for country in ["US", "ES"]}
    satisfaction_counts = {score: satisfaction_counter.get(score, 0) for score in [1, 2, 3, 4, 5]}

    return AnalysisResult(
        source_file=source_file,
        total_records=len(rows),
        valid_records=valid_count,
        invalid_records=invalid_count,
        invalid_breakdown=invalid_breakdown,
        by_category=by_category,
        by_status=by_status,
        by_country=by_country,
        satisfaction_counts=satisfaction_counts,
        scored_incidents=scored_incidents,
        closed_incidents=closed_incidents,
        average_satisfaction=round(average_score, 2),
    )


def analyze_csv(csv_path: Path) -> AnalysisResult:
    rows = read_csv_rows(csv_path)
    return analyze_rows(rows, source_file=csv_path.name)


def compute_percentages(counter: Dict[object, int], total: int) -> Dict[str, float]:
    if total <= 0:
        return {str(key): 0.0 for key in counter}
    return {str(key): round((value / total) * 100, 1) for key, value in counter.items()}


def format_line(label: str, value: str) -> str:
    dots = "." * max(2, 34 - len(label))
    return f"  {label} {dots} {value}"


def format_percentage_line(label: str, value: int, percentage: float) -> str:
    padded_value = f"{value}".rjust(3)
    return f"  - {label.ljust(28, '.')} {padded_value}  ({percentage:>4.1f}%)"


def render_report(result: AnalysisResult) -> str:
    category_percentages = compute_percentages(result.by_category, result.valid_records)
    status_percentages = compute_percentages(result.by_status, result.valid_records)
    country_percentages = compute_percentages(result.by_country, result.valid_records)

    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  TRACKFLOW - INCIDENT REPORT ANALYSIS")
    lines.append(f"  Source file: {result.source_file}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(format_line("TOTAL RECORDS IN FILE", str(result.total_records)))
    lines.append(format_line("Valid records", str(result.valid_records)))
    lines.append(format_line("Invalid / incomplete", str(result.invalid_records)))
    lines.append("")

    lines.append("INVALID RECORDS BREAKDOWN")
    ordered_labels: List[Tuple[str, str]] = [
        ("invalid_tracking", "Invalid tracking number"),
        ("invalid_carrier", "Carrier/country mismatch"),
        ("invalid_category", "Invalid or missing category"),
        ("invalid_email", "Invalid or missing email"),
        ("closed_missing_score", "Closed incident, no score"),
        ("score_out_of_range", "Score out of range"),
        ("invalid_country", "Invalid or missing country"),
        ("invalid_description", "Invalid or missing description"),
    ]
    for key, label in ordered_labels:
        count = result.invalid_breakdown.get(key, 0)
        if count > 0:
            lines.append(format_line(label, str(count)))
    lines.append("")

    lines.append("BREAKDOWN BY CATEGORY (valid records)")
    for category, count in result.by_category.items():
        lines.append(format_percentage_line(category, count, category_percentages[str(category)]))
    lines.append("")

    lines.append("BREAKDOWN BY STATUS (valid records)")
    for status, count in result.by_status.items():
        lines.append(format_percentage_line(status, count, status_percentages[str(status)]))
    lines.append("")

    lines.append("BREAKDOWN BY COUNTRY (valid records) - recomendado")
    for country, count in result.by_country.items():
        lines.append(format_percentage_line(country, count, country_percentages[str(country)]))
    lines.append("")

    lines.append("SATISFACTION INDEX (closed incidents)")
    lines.append(
        f"  Scored incidents: {result.scored_incidents} of {result.closed_incidents}"
    )
    lines.append(f"  Average score: {result.average_satisfaction:.2f} / 5.00")
    for score in [1, 2, 3, 4, 5]:
        lines.append(format_line(f"Score {score}", str(result.satisfaction_counts.get(score, 0))))
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
