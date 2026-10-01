"""Trading-calendar helpers.

Phase 0 uses a simple business-day calendar (Mon–Fri, no holiday table) to keep
generation deterministic and simple. A holiday-aware calendar can be layered in
later without changing the data contract.
"""

from __future__ import annotations

from datetime import date, timedelta


def business_days(start: date, end: date) -> list[date]:
    """Return every business day (Mon–Fri) in ``[start, end]``, inclusive."""
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days
