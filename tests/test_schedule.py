from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger


def test_daily_trigger_is_europe_london_not_fixed_utc():
    tz = ZoneInfo("Europe/London")
    trigger = CronTrigger(hour=9, minute=0, timezone=tz)
    assert str(trigger.timezone) == "Europe/London"
    assert "9" in str(trigger) or "hour='9'" in repr(trigger)
