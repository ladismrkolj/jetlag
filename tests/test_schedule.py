import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone, time

import pytest

from jetlag_core import create_jet_lag_timetable, rasterize_timetable
from jetlag_core.schedule import (
    sum_time_timedelta,
    subtract_times,
    hours_from_timedelta,
    is_in_time_interval,
    is_inside_interval,
    intersection_hours,
    midnight_for_datetime,
    to_iso,
    next_interval,
    CBTmin,
)


def test_create_jet_lag_timetable_basic():
    ny = timezone(timedelta(hours=-5))
    paris = timezone(timedelta(hours=1))
    travel_start = datetime(2024, 1, 1, 12, 0, tzinfo=ny)
    travel_end = datetime(2024, 1, 2, 6, 0, tzinfo=paris)
    events = create_jet_lag_timetable(
        origin_timezone=ny,
        destination_timezone=paris,
        origin_sleep_start=time(23, 0),
        origin_sleep_end=time(7, 0),
        destination_sleep_start=time(23, 0),
        destination_sleep_end=time(7, 0),
        travel_start=travel_start,
        travel_end=travel_end,
        use_melatonin=True,
        use_exercise=False,
        use_light_dark=True,
        precondition_days=1,
    )
    assert isinstance(events, list)
    assert any(e["event"] == "travel" for e in events)
    assert any(e.get("is_cbtmin") for e in events)
    assert any(e["event"] == "melatonin" and e["end"] is None for e in events)
    assert any(e["event"] == "light" and isinstance(e["end"], str) for e in events)


def test_direction_and_gating_under_3h():
    # Under 3h diff → only Day 0 CBTmin
    tz0 = timezone.utc
    tz1 = timezone(timedelta(hours=1))
    travel_start = datetime(2024, 1, 1, 12, 0, tzinfo=tz0)
    travel_end = datetime(2024, 1, 1, 13, 0, tzinfo=tz1)  # short hop
    events = create_jet_lag_timetable(
        origin_timezone=tz0,
        destination_timezone=tz1,
        origin_sleep_start=time(23, 0), origin_sleep_end=time(7, 0),
        destination_sleep_start=time(23, 0), destination_sleep_end=time(7, 0),
        travel_start=travel_start, travel_end=travel_end,
        use_melatonin=True, use_exercise=False, use_light_dark=True,
        precondition_days=2,
    )
    cbtmins = [e for e in events if e.get("is_cbtmin")]
    assert len(cbtmins) == 1
    assert cbtmins[0]["day_index"] == 0


def test_delay_direction_sign():
    # Choose tz and times so destination CBT is later → delay
    origin = timezone(timedelta(hours=-5))  # UTC-5
    dest = timezone(timedelta(hours=5))     # UTC+5
    travel_start = datetime(2024, 1, 1, 12, 0, tzinfo=origin)
    travel_end = datetime(2024, 1, 2, 6, 0, tzinfo=dest)
    events = create_jet_lag_timetable(
        origin_timezone=origin, destination_timezone=dest,
        origin_sleep_start=time(23, 0), origin_sleep_end=time(7, 0),
        destination_sleep_start=time(23, 0), destination_sleep_end=time(7, 0),
        travel_start=travel_start, travel_end=travel_end,
        use_melatonin=True, use_exercise=False, use_light_dark=False,
        precondition_days=0,
    )
    any_event = next(e for e in events if e["event"] in ("cbtmin", "melatonin"))
    assert any_event["phase_direction"] in ("delay", "advance", "aligned")


def test_zero_length_travel_and_rasterize():
    tz = timezone.utc
    travel = datetime(2024, 1, 1, 12, 0, tzinfo=tz)
    events = create_jet_lag_timetable(
        origin_timezone=tz, destination_timezone=tz,
        origin_sleep_start=time(23, 0), origin_sleep_end=time(7, 0),
        destination_sleep_start=time(23, 0), destination_sleep_end=time(7, 0),
        travel_start=travel, travel_end=travel,  # zero-length travel
        use_melatonin=True, use_exercise=False, use_light_dark=True,
        precondition_days=0,
    )
    assert any(e["event"] == "travel" for e in events)
    # Rasterize a one-day window
    slots = rasterize_timetable(
        events,
        start=datetime(2024, 1, 1, 0, 0, tzinfo=tz),
        end=datetime(2024, 1, 2, 0, 0, tzinfo=tz),
        step_minutes=60,
    )
    assert isinstance(slots, list) and len(slots) > 0
    # Ensure flags aggregate
    assert any(s.get("is_sleep") for s in slots)
    assert any(s.get("is_cbtmin") for s in slots)
    # all timestamps are ISO Z strings where present
    for e in events:
        if isinstance(e.get("start"), str):
            assert e["start"].endswith("Z")
        if isinstance(e.get("end"), str):
            assert e["end"].endswith("Z")


# --- Helper and format tests (consolidated) ---

def test_sum_time_timedelta_wrap():
    t = time(22, 30)
    td = timedelta(hours=3, minutes=45)
    res = sum_time_timedelta(t, td)
    assert isinstance(res, time)
    assert res.hour == 2 and res.minute == 15


def test_subtract_times_and_hours():
    t1 = time(9, 0)
    t2 = time(7, 30)
    delta = subtract_times(t1, t2)
    assert isinstance(delta, timedelta)
    assert hours_from_timedelta(delta) == pytest.approx(1.5)


def test_is_in_time_interval_across_midnight():
    sleep_start = time(23, 0)
    sleep_end = time(7, 0)
    dt1 = datetime(2025, 1, 1, 23, 30)
    dt2 = datetime(2025, 1, 2, 6, 59)
    dt3 = datetime(2025, 1, 2, 7, 0)
    assert is_in_time_interval(dt1, sleep_start, sleep_end) is True
    assert is_in_time_interval(dt2, sleep_start, sleep_end) is True
    assert is_in_time_interval(dt3, sleep_start, sleep_end) is False


def test_is_inside_interval_boundaries():
    start = datetime(2025, 1, 1, 12, 0)
    end = datetime(2025, 1, 1, 14, 0)
    assert is_inside_interval(start, (start, end)) is True
    assert is_inside_interval(end, (start, end)) is True
    assert is_inside_interval(datetime(2025, 1, 1, 11, 59), (start, end)) is False


def test_intersection_hours_basic():
    a0 = datetime(2025, 1, 1, 8, 0)
    a1 = datetime(2025, 1, 1, 10, 0)
    b0 = datetime(2025, 1, 1, 9, 0)
    b1 = datetime(2025, 1, 1, 11, 0)
    assert intersection_hours((a0, a1), (b0, b1)) == pytest.approx(1.0)
    c0 = datetime(2025, 1, 1, 10, 0)
    c1 = datetime(2025, 1, 1, 11, 0)
    d0 = datetime(2025, 1, 1, 11, 0)
    d1 = datetime(2025, 1, 1, 12, 0)
    assert intersection_hours((c0, c1), (d0, d1)) == 0.0


def test_midnight_for_datetime_and_to_iso():
    dt = datetime(2025, 3, 4, 15, 16, 17)
    md = midnight_for_datetime(dt)
    assert md.hour == 0 and md.minute == 0 and md.second == 0
    s = to_iso(md)
    assert isinstance(s, str) and s.startswith("2025-03-04T00:00:00")


def test_next_interval_basic_and_overlap():
    now = datetime(2025, 1, 1, 12, 0)
    interval = (time(13, 0), time(15, 0))
    start, end = next_interval(now, interval)
    assert start >= now and end > start

    interval2 = (time(23, 0), time(1, 0))
    s2, e2 = next_interval(datetime(2025, 1, 1, 22, 0), interval2)
    assert e2 > s2 and (e2 - s2) == timedelta(hours=2)

    fw = (datetime(2025, 1, 1, 13, 30), datetime(2025, 1, 1, 14, 0))
    s3, e3 = next_interval(now, interval, filter_window=fw)
    assert s3 is None and e3 is None


def test_cbtmin_phase_and_next():
    origin_end = time(7, 0)
    dest_end = time(7, 0)
    cbt = CBTmin.from_sleep(time(23, 0), origin_end, time(23, 0), dest_end)
    assert cbt.phase_direction in ("delay", "advance", "aligned")

    now = datetime(2025, 1, 1, 12, 0)
    no_int = (datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 1, 23, 59))
    nxt, interventions = cbt.next_cbtmin(now, no_intervention_window=no_int, precondition=False, skip_shift=True)
    assert isinstance(nxt, datetime)
    assert isinstance(interventions, tuple) and len(interventions) == 4


def test_rasterize_timetable_io_format():
    events = [
        {
            "event": "sleep",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T08:00:00Z",
            "is_sleep": True,
            "is_light": False,
            "is_dark": False,
            "is_travel": False,
            "is_exercise": False,
            "is_melatonin": False,
            "is_cbtmin": False,
        },
        {
            "event": "cbtmin",
            "start": "2025-01-01T03:30:00Z",
            "end": None,
            "is_sleep": False,
            "is_light": False,
            "is_dark": False,
            "is_travel": False,
            "is_exercise": False,
            "is_melatonin": False,
            "is_cbtmin": True,
        },
    ]
    start = datetime(2025, 1, 1, 0, 0)
    end = datetime(2025, 1, 1, 12, 0)
    slots = rasterize_timetable(events, start_utc=start, end_utc=end, step_minutes=60)
    assert isinstance(slots, list) and len(slots) > 0
    assert all(isinstance(s["start"], str) and s["start"].endswith("Z") for s in slots)
    assert all(isinstance(s["end"], str) and s["end"].endswith("Z") for s in slots)
    assert any(s.get("is_sleep") for s in slots)
    assert any(s.get("is_cbtmin") for s in slots)
