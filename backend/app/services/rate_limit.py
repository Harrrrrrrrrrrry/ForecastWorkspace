from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from app.core.config import get_settings


@dataclass(frozen=True)
class RateLimitExceededError(Exception):
    message: str


class ExplanationRateLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = Lock()
        self._hour_key = ""
        self._day_key = ""
        self._ip_hourly_counts: dict[str, int] = {}
        self._global_daily_count = 0

    def check_and_consume(self, *, client_ip: str) -> None:
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%dT%H")
        day_key = now.strftime("%Y-%m-%d")

        with self._lock:
            if hour_key != self._hour_key:
                self._hour_key = hour_key
                self._ip_hourly_counts = {}

            if day_key != self._day_key:
                self._day_key = day_key
                self._global_daily_count = 0

            hourly_limit = self.settings.explanation_ip_hourly_limit
            daily_limit = self.settings.explanation_global_daily_limit
            current_ip_count = self._ip_hourly_counts.get(client_ip, 0)

            if hourly_limit > 0 and current_ip_count >= hourly_limit:
                raise RateLimitExceededError(
                    "GPT explanation limit reached for this IP address. Please try again later."
                )

            if daily_limit > 0 and self._global_daily_count >= daily_limit:
                raise RateLimitExceededError(
                    "The daily GPT explanation limit for this site has been reached. Please try again tomorrow."
                )

            self._ip_hourly_counts[client_ip] = current_ip_count + 1
            self._global_daily_count += 1

    def reset(self) -> None:
        with self._lock:
            self._hour_key = ""
            self._day_key = ""
            self._ip_hourly_counts = {}
            self._global_daily_count = 0
