from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from trackflow_api.cache import api_cache
from trackflow_api.database import get_inventory_engine
from trackflow_api.models import TelemetryEventRecord
from trackflow_api.telemetry.analysis import (
    _to_iso_utc,
    auth_failure_rate,
    error_rate_by_type,
    events_per_day,
    generate_telemetry_report,
    latency_by_route,
)


@pytest.fixture(autouse=True)
def clean_cache():
    api_cache.clear()
    yield
    api_cache.clear()


def test_to_iso_utc_conversion():
    # String input with timezone offset
    iso = _to_iso_utc("2026-08-14T20:30:00+02:00")
    assert iso.endswith("+00:00") or iso.endswith("Z") or "18:30:00" in iso

    # Datetime input
    dt = datetime(2026, 8, 14, 18, 30, 0, tzinfo=timezone.utc)
    assert _to_iso_utc(dt) == "2026-08-14T18:30:00+00:00"

    # Invalid input
    with pytest.raises(ValueError):
        _to_iso_utc("invalid-date-string-xyz")


def test_analysis_metrics_empty_data():
    engine = get_inventory_engine()
    past_start = "2020-01-01T00:00:00Z"
    past_end = "2020-01-02T00:00:00Z"

    epd = events_per_day(past_start, past_end, engine=engine)
    assert isinstance(epd, list)
    assert len(epd) == 0

    err = error_rate_by_type(past_start, past_end, engine=engine)
    assert isinstance(err, list)
    assert len(err) == 0

    afr = auth_failure_rate(past_start, past_end, engine=engine)
    assert isinstance(afr, list)
    assert len(afr) == 0

    lat = latency_by_route(past_start, past_end, engine=engine)
    assert isinstance(lat, list)
    assert len(lat) == 0


def test_analysis_metrics_with_seeded_data():
    engine = get_inventory_engine()
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=10)).isoformat()
    end_date = (now + timedelta(days=1)).isoformat()

    # Test events_per_day
    epd = events_per_day(start_date, end_date, engine=engine)
    assert isinstance(epd, list)
    assert len(epd) > 0
    assert "date" in epd[0]
    assert "count" in epd[0]
    assert isinstance(epd[0]["count"], int)

    # Test error_rate_by_type
    err = error_rate_by_type(start_date, end_date, engine=engine)
    assert isinstance(err, list)
    if len(err) > 0:
        assert "event_type" in err[0]
        assert "count" in err[0]
        assert "total_events" in err[0]
        assert "error_rate" in err[0]

    # Test auth_failure_rate
    afr = auth_failure_rate(start_date, end_date, engine=engine)
    assert isinstance(afr, list)
    if len(afr) > 0:
        assert "date" in afr[0]
        assert "failed" in afr[0]
        assert "succeeded" in afr[0]
        assert "total_attempts" in afr[0]
        assert "failure_rate" in afr[0]
        assert afr[0]["total_attempts"] == afr[0]["failed"] + afr[0]["succeeded"]

    # Test latency_by_route
    lat = latency_by_route(start_date, end_date, engine=engine)
    assert isinstance(lat, list)
    if len(lat) > 0:
        assert "api_route" in lat[0]
        assert "method" in lat[0]
        assert "avg_latency_ms" in lat[0]
        assert "p95_latency_ms" in lat[0]


def test_get_telemetry_report_default_period(client: TestClient):
    response = client.get("/telemetry/report")
    assert response.status_code == 200
    data = response.json()

    assert "period" in data
    assert "from" in data["period"]
    assert "to" in data["period"]
    assert "metrics" in data
    assert "events_per_day" in data["metrics"]
    assert "error_rate_by_type" in data["metrics"]
    assert "auth_failure_rate" in data["metrics"]
    assert "latency_by_route" in data["metrics"]

    assert isinstance(data["metrics"]["events_per_day"], list)
    assert isinstance(data["metrics"]["error_rate_by_type"], list)
    assert isinstance(data["metrics"]["auth_failure_rate"], list)
    assert isinstance(data["metrics"]["latency_by_route"], list)


def test_get_telemetry_report_custom_dates(client: TestClient):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=3)).isoformat()
    end = now.isoformat()

    response = client.get("/telemetry/report", params={"start_date": start, "end_date": end})
    assert response.status_code == 200
    data = response.json()

    assert data["period"]["from"] == start
    assert data["period"]["to"] == end


def test_get_telemetry_report_invalid_date(client: TestClient):
    response = client.get("/telemetry/report?start_date=not-a-valid-date")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_get_telemetry_report_caching_60s(client: TestClient):
    start = "2026-08-10T00:00:00+00:00"
    end = "2026-08-18T00:00:00+00:00"

    # First request - caches result
    res1 = client.get(f"/telemetry/report?start_date={start}&end_date={end}")
    assert res1.status_code == 200

    # Patch pipeline to verify second request serves from cache without recomputing
    with patch(
        "trackflow_api.routes.telemetry.generate_telemetry_report"
    ) as mock_generate:
        res2 = client.get(f"/telemetry/report?start_date={start}&end_date={end}")
        assert res2.status_code == 200
        assert res2.json() == res1.json()
        mock_generate.assert_not_called()


def test_options_telemetry_report(client: TestClient):
    response = client.options("/telemetry/report")
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
