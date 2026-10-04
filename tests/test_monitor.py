from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import text
from src.monitor import check_daily, decisions, persist_alert, validate_threshold
from test_load_integration import engine


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_invalid_threshold(value):
    with pytest.raises(ValueError):
        validate_threshold(value)


def test_threshold_and_retry():
    assert decisions({"state": "running"}, {"accepted": 0, "rejected": 20}, 10) == []
    assert (
        decisions({"state": "success"}, {"accepted": 90, "rejected": 10}, 10)[1][1]
        is False
    )
    assert (
        decisions({"state": "failed"}, {"accepted": 89, "rejected": 11}, 10)[1][1]
        is True
    )
    assert len(decisions({"state": "failed"}, None, 10)) == 1


@pytest.mark.parametrize("hour,late", [(0, False), (1, True)])
def test_missing_daily(hour, late):
    result = check_daily(
        [], {}, datetime(2026, 10, 5, hour, tzinfo=ZoneInfo("Europe/Bucharest"))
    )
    assert result[1] is late
    assert result[2] is False


@pytest.mark.parametrize("clear,confirmed", [(0, True), (1, False)])
def test_daily_success(clear, confirmed):
    now = datetime(2026, 10, 5, 2, tzinfo=ZoneInfo("Europe/Bucharest"))
    run = {
        "run_id": "scheduled",
        "state": "success",
        "run_type": "scheduled",
        "run_after": now.replace(hour=0),
        "clear_number": clear,
    }
    tasks = {
        "scheduled": dict.fromkeys(
            ("extract", "transform", "validate", "load"), "success"
        )
    }
    result = check_daily([run], tasks, now)
    assert result[1] is False
    assert result[2] is confirmed
    tasks["scheduled"]["extract"] = "failed"
    assert check_daily([run], tasks, now)[1] is True


def test_alert_lifecycle(engine):
    with engine.begin() as c:
        assert (
            persist_alert(c, "test", "pipeline_failed", True, {"state": "failed"})
            == "opened"
        )
        assert (
            persist_alert(c, "test", "pipeline_failed", True, {"state": "failed"})
            is None
        )
        assert (
            persist_alert(c, "test", "pipeline_failed", False, {"state": "success"})
            == "resolved"
        )
        assert persist_alert(c, "test", "pipeline_failed", False, {}) is None
        assert persist_alert(c, "test", "pipeline_failed", True, {}) == "reopened"
        assert c.execute(text("SELECT count(*) FROM pipeline_alerts")).scalar() == 1


def test_custom_daily_time_excludes_older_run():
    now = datetime(2026, 10, 4, 19, 8, tzinfo=ZoneInfo("Europe/Bucharest"))
    old_run = {
        "run_id": "old",
        "state": "success",
        "run_type": "scheduled",
        "run_after": now.replace(hour=0, minute=0),
        "clear_number": 0,
    }
    result = check_daily([old_run], {}, now, scheduled_hour=19, scheduled_minute=7)
    assert result[3]["state"] == "missing"
    assert result[1] is False
    assert (
        check_daily(
            [], {}, now.replace(hour=20), scheduled_hour=19, scheduled_minute=7
        )[1]
        is True
    )
