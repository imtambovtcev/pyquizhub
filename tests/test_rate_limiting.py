"""
Tests for rate limiting functionality.

Tests the token bucket algorithm and rate limit enforcement
across different endpoints and user roles.
"""

from __future__ import annotations

import pytest
import time
from pyquizhub.core.api.rate_limiter import RateLimiter, TokenBucket
from pyquizhub.config.settings import RateLimitSettings
from fastapi import HTTPException


class TestTokenBucket:
    """Test the token bucket implementation."""

    def test_token_bucket_initialization(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(
            capacity=10,
            tokens=10.0,
            rate=5.0,  # 5 tokens per second
            last_update=time.time()
        )
        assert bucket.tokens == 10.0
        assert bucket.capacity == 10

    def test_token_bucket_consume_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(
            capacity=10,
            tokens=10.0,
            rate=5.0,
            last_update=time.time()
        )
        assert bucket.consume(1) is True
        assert bucket.tokens == 9.0

    def test_token_bucket_consume_failure(self):
        """Test token consumption fails when insufficient tokens."""
        bucket = TokenBucket(
            capacity=10,
            tokens=0.5,
            rate=5.0,
            last_update=time.time()
        )
        assert bucket.consume(1) is False
        # Tokens may have increased slightly due to time elapsed, but should be
        # close to 0.5
        assert 0.49 < bucket.tokens < 0.51

    def test_token_bucket_refill(self):
        """Test tokens refill over time."""
        now = time.time()
        bucket = TokenBucket(
            capacity=10,
            tokens=0.0,
            rate=10.0,  # 10 tokens per second
            last_update=now - 0.5  # 0.5 seconds ago
        )
        # After 0.5 seconds at 10 tokens/sec, should have 5 tokens
        assert bucket.consume(1) is True
        # Should have ~4 tokens left (5 - 1)
        assert 3.9 < bucket.tokens < 4.1

    def test_token_bucket_max_capacity(self):
        """Test tokens don't exceed capacity during refill."""
        now = time.time()
        bucket = TokenBucket(
            capacity=10,
            tokens=5.0,
            rate=10.0,  # 10 tokens per second
            last_update=now - 10.0  # 10 seconds ago
        )
        # Even with 10 seconds elapsed, tokens should cap at capacity
        bucket.consume(1)
        assert bucket.tokens <= 10.0


class TestRateLimiter:
    """Test the rate limiter with token buckets."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter()
        assert limiter._buckets == {}

    def test_rate_limiter_allows_within_limits(self):
        """Test rate limiter allows requests within limits."""
        limiter = RateLimiter()
        limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10
        )

        # Should not raise exception
        try:
            limiter.check_rate_limit("user1", "user", limits)
            limiter.check_rate_limit("user1", "user", limits)
            limiter.check_rate_limit("user1", "user", limits)
        except HTTPException:
            pytest.fail("Rate limiter rejected request within limits")

    def test_rate_limiter_rejects_burst_exceeded(self):
        """Test rate limiter rejects requests exceeding burst size."""
        limiter = RateLimiter()
        limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=3  # Small burst for testing
        )

        # First 3 requests should succeed
        limiter.check_rate_limit("user2", "user", limits)
        limiter.check_rate_limit("user2", "user", limits)
        limiter.check_rate_limit("user2", "user", limits)

        # 4th request should fail (burst exhausted)
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit("user2", "user", limits)

        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in str(exc_info.value.detail).lower()

    def test_rate_limiter_separate_buckets_per_user(self):
        """Test different users have separate rate limit buckets."""
        limiter = RateLimiter()
        limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=2
        )

        # User 1: exhaust burst
        limiter.check_rate_limit("user_a", "user", limits)
        limiter.check_rate_limit("user_a", "user", limits)

        with pytest.raises(HTTPException):
            limiter.check_rate_limit("user_a", "user", limits)

        # User 2: should still have full burst available
        try:
            limiter.check_rate_limit("user_b", "user", limits)
            limiter.check_rate_limit("user_b", "user", limits)
        except HTTPException:
            pytest.fail(
                "Different user should have separate rate limit bucket")

    def test_rate_limiter_separate_buckets_per_role(self):
        """Test same user with different roles has separate buckets."""
        limiter = RateLimiter()
        user_limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=2
        )
        admin_limits = RateLimitSettings(
            requests_per_minute=120,
            requests_per_hour=5000,
            burst_size=20
        )

        # User role: exhaust burst
        limiter.check_rate_limit("alice", "user", user_limits)
        limiter.check_rate_limit("alice", "user", user_limits)

        with pytest.raises(HTTPException):
            limiter.check_rate_limit("alice", "user", user_limits)

        # Admin role: should have separate bucket
        try:
            limiter.check_rate_limit("alice", "admin", admin_limits)
            limiter.check_rate_limit("alice", "admin", admin_limits)
        except HTTPException:
            pytest.fail(
                "Different role should have separate rate limit bucket")

    def test_rate_limiter_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter()
        limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10
        )

        # Make 3 requests
        limiter.check_rate_limit("user3", "user", limits)
        limiter.check_rate_limit("user3", "user", limits)
        limiter.check_rate_limit("user3", "user", limits)

        remaining = limiter.get_remaining("user3", "user", limits)
        assert "per_minute" in remaining
        assert "per_hour" in remaining
        # Should have 7 remaining in minute bucket (10 - 3)
        assert remaining["per_minute"] >= 6  # Allow for slight timing variance

    def test_rate_limiter_cleanup_old_entries(self):
        """Test old rate limit entries are cleaned up."""
        limiter = RateLimiter()
        limits = RateLimitSettings(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10
        )

        # Create an entry
        limiter.check_rate_limit("old_user", "user", limits)
        assert len(limiter._buckets) == 1

        # Manually set last_seen to 25 hours ago
        key = "old_user:user"
        minute_bucket, hour_bucket, _ = limiter._buckets[key]
        limiter._buckets[key] = (
            minute_bucket,
            hour_bucket,
            time.time() - 90000)

        # Force cleanup by setting last_cleanup to more than an hour ago
        limiter._last_cleanup = time.time() - 3601

        # Trigger cleanup by checking a different user
        limiter.check_rate_limit("new_user", "user", limits)

        # Old entry should be removed
        assert "old_user:user" not in limiter._buckets
        assert "new_user:user" in limiter._buckets
