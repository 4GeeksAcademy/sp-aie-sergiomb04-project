"""Automated test cases for Rate Limiting and Token Budget enforcement (NIST AI RMF / CSF 2.0).

Verifies request and token limits on LLM-backed endpoints to prevent Denial of Service (DoS)
and runaway operational costs, fulfilling section 3 of TASK.md.
"""

from unittest.mock import patch
import pytest
from services.security.rate_limiter import (
    SlidingWindowRateLimiter,
    estimate_tokens,
)


class FakeClock:
    """Controllable clock for deterministic sliding window testing."""

    def __init__(self, start: float = 1000.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class TestRateLimiterCore:
    """Unit tests for sliding window rate and token limiting logic."""

    def test_request_limit_enforced_strictly(self):
        """Limiter blocks requests exceeding max_requests within sliding window."""
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(
            max_requests=3,
            max_tokens=10000,
            window_seconds=60.0,
            clock=clock,
            name="test_requests",
        )

        # 3 requests allowed
        for i in range(3):
            decision = limiter.check("client_a", tokens=10)
            assert decision.allowed is True
            assert decision.remaining_requests == 2 - i

        # 4th request blocked
        blocked = limiter.check("client_a", tokens=10)
        assert blocked.allowed is False
        assert blocked.reason == "request_limit_exceeded"
        assert blocked.retry_after_seconds == 60

        # After advancing window past 60s, requests are allowed again
        clock.advance(60.1)
        recovered = limiter.check("client_a", tokens=10)
        assert recovered.allowed is True
        assert recovered.remaining_requests == 2

    def test_token_budget_limit_enforced(self):
        """Limiter blocks large requests exceeding the aggregate token budget."""
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(
            max_requests=10,
            max_tokens=1000,
            window_seconds=60.0,
            clock=clock,
            name="test_tokens",
        )

        # 1st request with 600 tokens allowed
        d1 = limiter.check("client_b", tokens=600)
        assert d1.allowed is True
        assert d1.remaining_tokens == 400

        # 2nd request requesting 500 tokens exceeds 1000 token limit
        d2 = limiter.check("client_b", tokens=500)
        assert d2.allowed is False
        assert d2.reason == "token_budget_exceeded"
        assert d2.retry_after_seconds > 0

    def test_client_key_isolation(self):
        """Limits for client_a do not starve or impact client_b."""
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(
            max_requests=1,
            max_tokens=5000,
            window_seconds=30.0,
            clock=clock,
        )

        assert limiter.check("tenant_alpha", tokens=50).allowed is True
        assert limiter.check("tenant_alpha", tokens=50).allowed is False

        # tenant_beta can still make requests
        assert limiter.check("tenant_beta", tokens=50).allowed is True

    def test_token_estimation_heuristic(self):
        """Token estimator computes prompt tokens + completion reservation."""
        prompt = "Consulta de tracking para mi pedido en Los Ángeles"
        estimated = estimate_tokens(prompt, completion_reserve=256)
        # prompt is ~53 chars -> ~14 prompt tokens + 256 reserve -> ~270 tokens
        assert estimated > 256
        assert estimated < 300


class TestRateLimiterIntegration:
    """Integration test verifying HTTP 429 response on rate limited API calls."""

    def test_endpoint_returns_429_on_rate_limit(self):
        """Simulates rate limiter rejection on FastAPI router and verifies status 429 and Retry-After."""
        from services.security.rate_limiter import agent_rate_limiter
        from trackflow_api.main import app
        from fastapi.testclient import TestClient

        test_client = TestClient(app)

        # Reset limiter for clean test
        agent_rate_limiter.reset("session_test_429")

        # Fill up quota
        limit = agent_rate_limiter.max_requests
        with patch("trackflow_api.routes.agent.run_support_agent") as mock_agent:
            mock_agent.return_value = {
                "answer": "Test response",
                "thread_id": "thread_429",
                "run_id": "run_429",
                "is_valid": True,
                "nodes_executed": ["receive_question"],
                "error": None,
                "context": [],
                "trace": [],
            }

            for _ in range(limit):
                resp = test_client.post(
                    "/agent/query",
                    json={"question": "¿Dónde está mi paquete?", "session_user": "session_test_429"},
                )
                assert resp.status_code == 200

            # Exceeded request must return HTTP 429
            blocked_resp = test_client.post(
                "/agent/query",
                json={"question": "¿Dónde está mi paquete?", "session_user": "session_test_429"},
            )
            assert blocked_resp.status_code == 429
            assert "excedido" in blocked_resp.json()["detail"].lower()
            assert "Retry-After" in blocked_resp.headers
            assert int(blocked_resp.headers["Retry-After"]) >= 1

        # Clean up
        agent_rate_limiter.reset("session_test_429")
