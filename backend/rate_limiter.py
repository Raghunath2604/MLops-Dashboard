"""
Rate Limiter for Multi-Tenant SaaS
Implements sliding-window rate limiting with Redis backend
Enforces per-tier usage quotas
"""

import redis
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Tier-based rate limits (requests per minute)
TIER_LIMITS = {
    "free": 10,        # 10 req/min = 600/hour = 14.4k/day = 430k/month
    "pro": 100,        # 100 req/min = 6k/hour = 144k/day = 4.3M/month
    "business": 500,   # 500 req/min = 30k/hour = 720k/day = 21.6M/month
    "enterprise": 10000  # 10k req/min = unlimited practically
}

# Monthly quota limits
MONTHLY_QUOTAS = {
    "free": 10_000,
    "pro": 100_000,
    "business": 1_000_000,
    "enterprise": 999_999_999
}


class RateLimiter:
    """
    Sliding-window rate limiter using Redis

    Algorithm:
    - For each API key, maintain a sorted set of request timestamps
    - On each request, remove old timestamps outside the window
    - Check if current count exceeds limit
    - Add current timestamp if allowed
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.window_seconds = 60  # 1-minute sliding window

    def get_rate_limit_key(self, org_id: int, tier: str) -> str:
        """Generate Redis key for org's rate limit"""
        return f"rate_limit:{org_id}:{tier}"

    def get_quota_key(self, org_id: int) -> str:
        """Generate Redis key for org's monthly quota"""
        return f"quota:{org_id}"

    def check_rate_limit(self, org_id: int, tier: str) -> Tuple[bool, Dict]:
        """
        Check if request is allowed under rate limit

        Returns:
            (allowed: bool, info: dict with remaining, reset_at)
        """
        try:
            key = self.get_rate_limit_key(org_id, tier)
            limit = TIER_LIMITS.get(tier, 10)

            current_time = time.time()
            window_start = current_time - self.window_seconds

            # Remove old entries outside window
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in window
            current_count = self.redis_client.zcard(key)

            if current_count >= limit:
                # Get oldest timestamp to calculate reset time
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_at = oldest[0][1] + self.window_seconds if oldest else current_time + self.window_seconds

                return False, {
                    "limit": limit,
                    "current": current_count,
                    "remaining": 0,
                    "reset_at": int(reset_at),
                    "retry_after": int(reset_at - current_time)
                }

            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})

            # Set expiry on key (window + 1 second safety margin)
            self.redis_client.expire(key, self.window_seconds + 1)

            remaining = limit - current_count - 1
            reset_at = current_time + self.window_seconds

            return True, {
                "limit": limit,
                "current": current_count + 1,
                "remaining": remaining,
                "reset_at": int(reset_at),
                "retry_after": None
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open on Redis errors - don't block users
            return True, {"error": "rate limit service unavailable"}

    def check_monthly_quota(self, org_id: int, tier: str) -> Tuple[bool, Dict]:
        """
        Check if organization has used monthly quota

        Returns:
            (allowed: bool, info: dict with usage, limit, reset_date)
        """
        try:
            key = self.get_quota_key(org_id)
            quota_limit = MONTHLY_QUOTAS.get(tier, 10_000)

            # Get current month's usage
            usage_data = self.redis_client.get(key)
            usage_info = json.loads(usage_data) if usage_data else {
                "usage": 0,
                "reset_date": self._get_next_month()
            }

            usage = usage_info["usage"]
            reset_date = usage_info["reset_date"]

            # Check if month has rolled over
            if datetime.utcnow() > datetime.fromisoformat(reset_date):
                usage = 0
                reset_date = self._get_next_month()

            if usage >= quota_limit:
                return False, {
                    "quota_limit": quota_limit,
                    "usage": usage,
                    "remaining": 0,
                    "reset_date": reset_date,
                    "tier": tier
                }

            remaining = quota_limit - usage

            return True, {
                "quota_limit": quota_limit,
                "usage": usage,
                "remaining": remaining,
                "reset_date": reset_date,
                "tier": tier,
                "percentage_used": (usage / quota_limit * 100) if quota_limit > 0 else 0
            }

        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            # Fail open on Redis errors
            return True, {"error": "quota service unavailable"}

    def increment_quota(self, org_id: int, amount: int = 1) -> bool:
        """Increment organization's monthly usage"""
        try:
            key = self.get_quota_key(org_id)
            usage_data = self.redis_client.get(key)

            if usage_data:
                usage_info = json.loads(usage_data)
                reset_date = usage_info["reset_date"]

                # Check if month rolled over
                if datetime.utcnow() > datetime.fromisoformat(reset_date):
                    usage = 0
                    reset_date = self._get_next_month()
                else:
                    usage = usage_info.get("usage", 0)
            else:
                usage = 0
                reset_date = self._get_next_month()

            usage += amount

            # Store updated usage
            usage_info = {"usage": usage, "reset_date": reset_date}
            self.redis_client.set(key, json.dumps(usage_info))

            # Set expiry to reset date + 1 day (safety margin)
            expiry = datetime.fromisoformat(reset_date) + timedelta(days=1)
            self.redis_client.expireat(key, expiry)

            return True

        except Exception as e:
            logger.error(f"Quota increment failed: {e}")
            return False

    def reset_quota(self, org_id: int) -> bool:
        """Reset organization's monthly quota (admin only)"""
        try:
            key = self.get_quota_key(org_id)
            reset_date = self._get_next_month()
            usage_info = {"usage": 0, "reset_date": reset_date}
            self.redis_client.set(key, json.dumps(usage_info))
            return True
        except Exception as e:
            logger.error(f"Quota reset failed: {e}")
            return False

    def _get_next_month(self) -> str:
        """Get ISO format string for end of current month"""
        today = datetime.utcnow()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return next_month.isoformat()


import os

# Singleton instance
_rate_limiter = None

def get_rate_limiter(redis_url: str = None) -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if redis_url is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(redis_url)
    return _rate_limiter
