from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, reset_tzpath

try:
    KOLKATA = ZoneInfo("Asia/Kolkata")
except (ZoneInfoNotFoundError, ValueError):
    # Some ARM base images ship a broken system zoneinfo file. Fall back to
    # the pinned Python tzdata package instead of making the API fail startup.
    reset_tzpath([])
    KOLKATA = ZoneInfo("Asia/Kolkata")


def business_today(now: datetime | None = None) -> date:
    """Return the calendar date used by the shop, regardless of host timezone."""
    return (now or datetime.now(KOLKATA)).astimezone(KOLKATA).date()


def business_month(now: datetime | None = None) -> str:
    return business_today(now).strftime("%Y-%m")


def month_start(month: str) -> date:
    return date.fromisoformat(f"{month}-01")
