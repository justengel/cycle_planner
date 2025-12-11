"""
Rate limiter for AI generation requests.

Implements a sliding window rate limit to prevent abuse of the AI generation endpoint.
Limits are configurable via environment variables:
- RATE_LIMIT_REQUESTS: Maximum number of AI generations per window (default: 10)
- RATE_LIMIT_WINDOW_HOURS: Time window in hours (default: 24)

Note: Uses in-memory storage, so limits reset on server restart and don't persist
across multiple server instances.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException

from app.config import get_settings

# In-memory storage for rate limiting
_user_requests: dict[str, list[datetime]] = defaultdict(list)


def _get_rate_limits() -> tuple[int, int]:
    """Get rate limit settings from config."""
    settings = get_settings()
    return settings.rate_limit_requests, settings.rate_limit_window_hours


def check_rate_limit(user_id: str, max_requests: int | None = None, window_hours: int | None = None):
    """
    Check if user has exceeded rate limit.
    Raises HTTPException if limit exceeded.
    """
    default_max, default_window = _get_rate_limits()
    max_requests = max_requests if max_requests is not None else default_max
    window_hours = window_hours if window_hours is not None else default_window

    now = datetime.utcnow()
    window_start = now - timedelta(hours=window_hours)

    # Clean up old requests outside the window
    _user_requests[user_id] = [
        req_time for req_time in _user_requests[user_id]
        if req_time > window_start
    ]

    # Check current count
    current_count = len(_user_requests[user_id])

    if current_count >= max_requests:
        # Calculate when the oldest request will expire
        oldest = min(_user_requests[user_id])
        reset_time = oldest + timedelta(hours=window_hours)
        minutes_until_reset = int((reset_time - now).total_seconds() / 60)
        hours_until_reset = minutes_until_reset // 60
        mins_remaining = minutes_until_reset % 60

        if hours_until_reset > 0:
            time_str = f"{hours_until_reset}h {mins_remaining}m"
        else:
            time_str = f"{mins_remaining} minutes"

        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. You can generate {max_requests} plans per {window_hours} hours. Try again in {time_str}."
        )


def record_request(user_id: str):
    """Record a successful request for rate limiting."""
    _user_requests[user_id].append(datetime.utcnow())


def get_remaining_requests(user_id: str, max_requests: int | None = None, window_hours: int | None = None) -> dict:
    """Get remaining requests info for a user."""
    default_max, default_window = _get_rate_limits()
    max_requests = max_requests if max_requests is not None else default_max
    window_hours = window_hours if window_hours is not None else default_window

    now = datetime.utcnow()
    window_start = now - timedelta(hours=window_hours)

    # Clean up old requests
    _user_requests[user_id] = [
        req_time for req_time in _user_requests[user_id]
        if req_time > window_start
    ]

    current_count = len(_user_requests[user_id])
    remaining = max(0, max_requests - current_count)

    result = {
        "remaining": remaining,
        "limit": max_requests,
        "window_hours": window_hours,
        "used": current_count,
    }

    if current_count > 0:
        oldest = min(_user_requests[user_id])
        reset_time = oldest + timedelta(hours=window_hours)
        result["resets_at"] = reset_time.isoformat()

    return result
