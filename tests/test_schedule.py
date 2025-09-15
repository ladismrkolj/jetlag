import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone

from jetlag_core.schedule import (
    TimelineEvent,
    calculate_cbtmin_times,
    calculate_intervention_times,
    calculate_next_cbtmin,
    create_jet_lag_schedule,
    create_timeline,
)


def test_calculate_next_cbtmin_moves_toward_target():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    target = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)
    result = calculate_next_cbtmin(start, target, timedelta(hours=1))
    assert result == start + timedelta(hours=1)


def test_calculate_cbtmin_times_generates_sequence():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    target = datetime(2024, 1, 1, 5, tzinfo=timezone.utc)
    end = datetime(2024, 1, 3, tzinfo=timezone.utc)
    times = calculate_cbtmin_times(start, target, end, timedelta(hours=1))
    assert times[0] == start
    assert times[-1] == target


def test_calculate_intervention_times_structure():
    cbt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    windows = calculate_intervention_times([cbt])
    assert set(windows.keys()) == {"melatonin", "light", "dark"}
    mel_start, mel_end = windows["melatonin"][0]
    assert mel_end - mel_start == timedelta(hours=1)


def test_create_timeline_orders_events():
    cbt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    interventions = {"light": [(cbt, cbt + timedelta(hours=1))]}
    timeline = create_timeline([cbt], interventions)
    assert [e.event for e in timeline] == ["cbtmin", "light"]


def test_create_jet_lag_schedule_returns_timeline():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 3, tzinfo=timezone.utc)
    target = datetime(2024, 1, 1, 6, tzinfo=timezone.utc)
    schedule = create_jet_lag_schedule(start, end, start, target)
    assert all(isinstance(e, TimelineEvent) for e in schedule)
