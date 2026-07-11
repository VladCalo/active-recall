"""Timezone-aware date helpers shared across services."""

from datetime import date, datetime
from zoneinfo import ZoneInfo


def today_in_tz(tz_str: str) -> date:
    """Today's date in the given IANA timezone."""
    return datetime.now(ZoneInfo(tz_str)).date()
