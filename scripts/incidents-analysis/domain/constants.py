from __future__ import annotations

from typing import Dict, List, Set

COUNTRIES: Set[str] = {"US", "ES"}
CUSTOMER_TYPES: Set[str] = {"B2B", "B2C"}
STATUSES: Set[str] = {"OPEN", "CLOSED", "DISCARDED"}

CATEGORIES: List[str] = [
    "LOST_PARCEL",
    "DELAYED_DELIVERY",
    "WRONG_ADDRESS",
    "RETURN_REQUEST",
    "DAMAGE",
]

CARRIERS_BY_COUNTRY: Dict[str, Set[str]] = {
    "US": {"UPS", "FEDEX", "DHL_US"},
    "ES": {"MRW", "SEUR", "DHL_ES", "LOCAL_ES"},
}

REQUIRED_FIELDS: List[str] = [
    "incident_id",
    "date",
    "country",
    "customer_type",
    "tracking_number",
    "carrier",
    "category",
    "description",
    "status",
    "customer_email",
]

INVALID_RULES = {
    "invalid_country": "country faltante o invalido",
    "invalid_carrier": "carrier faltante o invalido",
    "invalid_tracking": "tracking_number faltante o invalido",
    "invalid_category": "category faltante o invalida",
    "invalid_description": "description vacia o muy corta",
    "invalid_email": "customer_email faltante o invalido",
    "closed_missing_score": "status=CLOSED sin satisfaction_score",
    "score_out_of_range": "satisfaction_score fuera de rango",
}

REPORT_RULE_ORDER: List[str] = [
    "invalid_tracking",
    "invalid_carrier",
    "invalid_category",
    "invalid_email",
    "closed_missing_score",
    "score_out_of_range",
    "invalid_country",
    "invalid_description",
]
