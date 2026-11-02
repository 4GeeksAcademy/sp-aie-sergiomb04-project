"""Request and token rate limiting for LLM-backed endpoints (NIST Protect).

Prevents runaway LLM costs and abuse of the 24/7 support agent. Uses an in-memory
sliding window per client key, enforcing simultaneously:
- a maximum number of requests per window, and
- a maximum estimated token budget per window (input + reserved completion tokens).

The limiter is process-local; a multi-replica deployment should move the counters to
Redis (already available in docker-compose) - tracked as residual risk in
`docs/NIST-AUDIT.md`.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Optional, Tuple

logger = logging.getLogger("trackflow.security.rate_limiter")

# Rough heuristic used by OpenAI tokenizers for Spanish/English text (~4 chars per token)
CHARS_PER_TOKEN = 4
DEFAULT_COMPLETION_TOKENS_RESERVED = 512


def estimate_tokens(text: str, completion_reserve: int = DEFAULT_COMPLETION_TOKENS_RESERVED) -> int:
    """Estimate tokens consumed by one LLM call: prompt tokens + reserved completion tokens."""
    prompt_tokens = math.ceil(len(text or "") / CHARS_PER_TOKEN)
    return prompt_tokens + max(0, completion_reserve)


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a rate-limit check."""

    allowed: bool
    key: str
    reason: Optional[str] = None
    retry_after_seconds: int = 0
    remaining_requests: int = 0
    remaining_tokens: int = 0


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window limiter on requests and estimated tokens per key."""

    def __init__(
        self,
        *,
        max_requests: int,
        max_tokens: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        name: str = "llm",
    ) -> None:
        if max_requests <= 0 or max_tokens <= 0 or window_seconds <= 0:
            raise ValueError("Rate limiter parameters must be positive.")
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.window_seconds = float(window_seconds)
        self.name = name
        self._clock = clock
        self._events: Dict[str, Deque[Tuple[float, int]]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[Tuple[float, int]]:
        events = self._events.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while events and events[0][0] <= cutoff:
            events.popleft()
        return events

    def check(self, key: str, tokens: int = 1) -> RateLimitDecision:
        """Register a request for `key` consuming `tokens` if within limits."""
        tokens = max(1, int(tokens))
        with self._lock:
            now = self._clock()
            events = self._prune(key, now)
            used_requests = len(events)
            used_tokens = sum(t for _, t in events)

            reason: Optional[str] = None
            if used_requests + 1 > self.max_requests:
                reason = "request_limit_exceeded"
            elif used_tokens + tokens > self.max_tokens:
                reason = "token_budget_exceeded"

            if reason:
                retry_after = 1
                if events:
                    retry_after = max(1, math.ceil(events[0][0] + self.window_seconds - now))
                logger.warning(
                    "[RATE_LIMIT] limiter=%s key=%s decision=blocked reason=%s used_requests=%d "
                    "used_tokens=%d requested_tokens=%d retry_after=%ds",
                    self.name,
                    key,
                    reason,
                    used_requests,
                    used_tokens,
                    tokens,
                    retry_after,
                )
                return RateLimitDecision(
                    allowed=False,
                    key=key,
                    reason=reason,
                    retry_after_seconds=retry_after,
                    remaining_requests=max(0, self.max_requests - used_requests),
                    remaining_tokens=max(0, self.max_tokens - used_tokens),
                )

            events.append((now, tokens))
            return RateLimitDecision(
                allowed=True,
                key=key,
                remaining_requests=self.max_requests - used_requests - 1,
                remaining_tokens=self.max_tokens - used_tokens - tokens,
            )

    def reset(self, key: Optional[str] = None) -> None:
        """Reset counters for one key or for all keys."""
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("[RATE_LIMIT] invalid integer for %s, using default=%d", name, default)
        return default


def build_agent_rate_limiter() -> SlidingWindowRateLimiter:
    """Create the limiter for LLM endpoints using env configuration."""
    return SlidingWindowRateLimiter(
        max_requests=_env_int("AGENT_RATE_LIMIT_REQUESTS", 20),
        max_tokens=_env_int("AGENT_RATE_LIMIT_TOKENS", 20000),
        window_seconds=_env_int("AGENT_RATE_LIMIT_WINDOW_SECONDS", 60),
        name="agent_llm",
    )


agent_rate_limiter = build_agent_rate_limiter()
