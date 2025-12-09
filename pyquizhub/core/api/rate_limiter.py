"""
Rate limiting middleware for FastAPI.

Implements token bucket algorithm for rate limiting with per-role configuration.
Tracks both per-minute and per-hour limits with burst support.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status
from typing import Dict, Tuple

from pyquizhub.config.settings import RateLimitSettings


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int  # Maximum tokens (burst size)
    tokens: float  # Current tokens
    rate: float  # Tokens added per second
    last_update: float  # Last update timestamp

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Returns:
            True if tokens were consumed, False if rate limit exceeded
        """
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """
    Rate limiter implementing token bucket algorithm.

    Maintains separate buckets for per-minute and per-hour limits.
    """

    def __init__(self):
        # "user_id:role" -> (minute_bucket, hour_bucket, last_seen)
        self._buckets: Dict[str, Tuple[TokenBucket, TokenBucket, float]] = {}
        self._cleanup_interval = 3600  # Clean up every hour
        self._last_cleanup = time.time()

    def _get_or_create_buckets(
        self, user_id: str, role: str, limits: RateLimitSettings
    ) -> Tuple[TokenBucket, TokenBucket]:
        """Get or create rate limit buckets for a user+role combination."""

        # Check if we need to clean up old entries
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries()
            self._last_cleanup = now

        # Use user_id:role as key to separate buckets by role
        key = f"{user_id}:{role}"

        if key not in self._buckets:
            # Create new buckets
            minute_bucket = TokenBucket(
                capacity=limits.burst_size,
                tokens=float(limits.burst_size),
                rate=limits.requests_per_minute / 60.0,  # tokens per second
                last_update=now
            )

            hour_bucket = TokenBucket(
                capacity=limits.requests_per_hour,
                tokens=float(limits.requests_per_hour),
                rate=limits.requests_per_hour / 3600.0,  # tokens per second
                last_update=now
            )

            self._buckets[key] = (minute_bucket, hour_bucket, now)

        minute_bucket, hour_bucket, _ = self._buckets[key]
        # Update last_seen timestamp
        self._buckets[key] = (minute_bucket, hour_bucket, now)
        return minute_bucket, hour_bucket

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory growth."""
        now = time.time()
        to_remove = []

        for key, (_, _, last_seen) in self._buckets.items():
            # Remove if not accessed in last 24 hours
            if now - last_seen > 86400:
                to_remove.append(key)

        for key in to_remove:
            del self._buckets[key]

    def check_rate_limit(
        self, user_id: str, role: str, limits: RateLimitSettings
    ) -> None:
        """
        Check if request is within rate limits.

        Args:
            user_id: User identifier
            role: User role (admin, creator, user)
            limits: Rate limit settings for the role

        Raises:
            HTTPException: If rate limit exceeded
        """
        minute_bucket, hour_bucket = self._get_or_create_buckets(
            user_id, role, limits
        )

        # Check per-minute limit
        if not minute_bucket.consume():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit_type": "per_minute",
                    "limit": limits.requests_per_minute,
                    "retry_after": int((1.0 - minute_bucket.tokens) / minute_bucket.rate)
                }
            )

        # Check per-hour limit
        if not hour_bucket.consume():
            # Refund the minute bucket token since we're rejecting
            minute_bucket.tokens = min(minute_bucket.capacity, minute_bucket.tokens + 1)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit_type": "per_hour",
                    "limit": limits.requests_per_hour,
                    "retry_after": int((1.0 - hour_bucket.tokens) / hour_bucket.rate)
                }
            )

    def get_remaining(
        self, user_id: str, role: str, limits: RateLimitSettings
    ) -> Dict[str, int]:
        """
        Get remaining requests for a user+role combination.

        Returns:
            Dictionary with remaining per_minute and per_hour counts
        """
        key = f"{user_id}:{role}"

        if key not in self._buckets:
            return {
                "per_minute": limits.requests_per_minute,
                "per_hour": limits.requests_per_hour
            }

        minute_bucket, hour_bucket, _ = self._buckets[key]

        # Update tokens before reporting
        now = time.time()

        minute_elapsed = now - minute_bucket.last_update
        minute_tokens = min(
            minute_bucket.capacity,
            minute_bucket.tokens + minute_elapsed * minute_bucket.rate
        )

        hour_elapsed = now - hour_bucket.last_update
        hour_tokens = min(
            hour_bucket.capacity,
            hour_bucket.tokens + hour_elapsed * hour_bucket.rate
        )

        return {
            "per_minute": int(minute_tokens),
            "per_hour": int(hour_tokens)
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter
