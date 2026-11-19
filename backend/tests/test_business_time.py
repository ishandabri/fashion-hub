from datetime import datetime, timezone

from app.business_time import business_month, business_today


def test_india_business_date_crosses_midnight_before_utc_date_changes():
    instant = datetime(2026, 11, 19, 18, 31, tzinfo=timezone.utc)
    assert business_today(instant).isoformat() == "2026-11-20"
    assert business_month(instant) == "2026-11"
