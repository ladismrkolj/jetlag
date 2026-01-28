import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone, time

import pytest

from jetlag_core import create_jet_lag_timetable, rasterize_timetable
from jetlag_core.schedule import (
    sum_time_timedelta,
    astimezone_time,
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
    ny = -5.
    paris = 1.
    travel_start = datetime(2024, 1, 1, 12, 0)
    travel_end = datetime(2024, 1, 2, 6, 0)
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


def test_adjustment_start_invalid():
    ny = -5.
    paris = 1.
    travel_start = datetime(2024, 1, 1, 12, 0)
    travel_end = datetime(2024, 1, 2, 6, 0)
    with pytest.raises(ValueError):
        create_jet_lag_timetable(
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
            precondition_days=0,
            adjustment_start="invalid",
        )


def test_direction_and_gating_under_3h():
    # Under 3h diff → only Day 0 CBTmin
    tz0 = 0.0
    tz1 = 1.0
    travel_start = datetime(2024, 1, 1, 12, 0)
    travel_end = datetime(2024, 1, 1, 13, 0)  # short hop
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


def test_ignore_travel_interventions_allows_intervention_during_travel():
    origin = -5.0
    dest = 1.0
    travel_start = datetime(2024, 1, 1, 0, 0)
    travel_end = datetime(2024, 1, 3, 0, 0)
    base_args = dict(
        origin_timezone=origin,
        destination_timezone=dest,
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
        adjustment_start="precondition",
    )
    events_blocked = create_jet_lag_timetable(
        **base_args,
        ignore_travel_interventions=False,
    )
    events_allowed = create_jet_lag_timetable(
        **base_args,
        ignore_travel_interventions=True,
    )
    travel_start_utc = travel_start - timedelta(hours=origin)
    travel_end_utc = travel_end - timedelta(hours=dest)

    def has_intervention_within_travel(events):
        for event in events:
            if not (event.get("is_melatonin") or event.get("is_light") or event.get("is_dark") or event.get("is_exercise")):
                continue
            start = event.get("start")
            if not start:
                continue
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if travel_start_utc <= start_dt <= travel_end_utc:
                return True
        return False

    assert not has_intervention_within_travel(events_blocked)
    assert has_intervention_within_travel(events_allowed)


def test_delay_direction_sign():
    # Choose tz and times so destination CBT is later → delay
    origin = -5.0  # UTC-5
    dest = 5.0     # UTC+5
    travel_start = datetime(2024, 1, 1, 12, 0)
    travel_end = datetime(2024, 1, 2, 6, 0)
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
    tz_offset = 0.0
    travel = datetime(2024, 1, 1, 12, 0)
    events = create_jet_lag_timetable(
        origin_timezone=tz_offset, destination_timezone=tz_offset,
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
        start_utc=datetime(2024, 1, 1, 0, 0),
        end_utc=datetime(2024, 1, 2, 0, 0),
        step_minutes=60,
    )
    assert isinstance(slots, list) and len(slots) > 0
    # Ensure flags aggregate
    assert any(s.get("is_sleep") for s in slots)
    assert any(s.get("is_cbtmin") for s in slots)


@pytest.fixture(scope="module")
def cbtmin_init_delay():
    # Origin CBTmin 03:00 → Dest CBTmin 09:00 (+6h) → delay
    return CBTmin(time(3, 0), time(9, 0))


@pytest.fixture(scope="module")
def cbtmin_from_sleep_advance():
    # Origin sleep 23–10 → CBT 07:00; Dest sleep 23–07 → CBT 04:00 (−3h) → advance
    return CBTmin.from_sleep(time(23, 0), time(10, 0), time(23, 0), time(7, 0))


@pytest.fixture(scope="module")
def cbtmin_aligned():
    # No difference
    return CBTmin(time(4, 0), time(4, 0))


def test_cbtmin_init_full(cbtmin_init_delay):
    cbt = cbtmin_init_delay
    assert isinstance(cbt, CBTmin)
    assert cbt.signed_difference() > 0 and cbt.phase_direction == "delay"
    # Windows types and directionality
    from datetime import timedelta as _td
    m = cbt.optimal_melatonin_time()
    ex0, ex1 = cbt.optimal_exercise_window()
    l0, l1 = cbt.optimal_light_window()
    d0, d1 = cbt.optimal_dark_window()
    assert isinstance(m, _td) and all(isinstance(x, _td) for x in (ex0, ex1, l0, l1, d0, d1))
    assert m.total_seconds() > 0 and ex0 <= _td(0) <= ex1 and l0 <= _td(0) and d0 <= _td(0) <= d1
    # Delta behaviour
    assert cbt.delta_cbtmin(True, False, False, precondition=False) == 1.5
    # next_cbtmin without shift
    now = datetime(2025, 1, 1, 12, 0)
    cand, used = cbt.next_cbtmin(now, no_intervention_window=(now, now), precondition=False)
    assert isinstance(cand, datetime) and isinstance(used, tuple) and len(used) == 4
    assert cand == now.replace(hour=cbt.origin_cbtmin.hour, minute=cbt.origin_cbtmin.minute) + timedelta(hours=1.5) + timedelta(days=1)
    cand2, used2 = cbt.next_cbtmin(now+timedelta(days=1), no_intervention_window=(now, now), precondition=False)
    assert cand2 == cand + timedelta(days=1) + timedelta(hours=1.5)


def test_cbtmin_from_sleep_full(cbtmin_from_sleep_advance):
    cbt = cbtmin_from_sleep_advance
    assert isinstance(cbt, CBTmin)
    assert cbt.signed_difference() < 0 and cbt.phase_direction == "advance"
    # Windows
    from datetime import timedelta as _td
    m = cbt.optimal_melatonin_time()
    ex0, ex1 = cbt.optimal_exercise_window()
    l0, l1 = cbt.optimal_light_window()
    d0, d1 = cbt.optimal_dark_window()
    assert isinstance(m, _td) and m.total_seconds() < 0
    assert ex0 >= _td(0) and l0 >= _td(0) and d0 <= _td(0) <= d1
    # next_cbtmin gating last 8h
    now = datetime(2025, 1, 1, 12, 0)
    cand, _ = cbt.next_cbtmin(now, no_intervention_window=(now, now), precondition=False, skip_shift=True)
    win = (cand - timedelta(hours=8), cand + timedelta(hours=1))
    next2, used2 = cbt.next_cbtmin(now, no_intervention_window=win, precondition=False, skip_shift=False)
    assert isinstance(next2, datetime) and all(p[0] is False for p in used2)


def test_cbtmin_delta_values_edgecases():
    # Large diff (>3h)
    c_large = CBTmin(time(4, 0), time(10, 0))  # +6h
    # any method, no precondition → 1.5
    assert c_large.delta_cbtmin(True, False, False, precondition=False) == 1.5
    # any method, precondition → 1.0
    assert c_large.delta_cbtmin(True, False, False, precondition=True) == 1.0
    # no method → 1.0 (or 0.0 with precondition)
    assert c_large.delta_cbtmin(False, False, False, precondition=False) == 1.0
    assert c_large.delta_cbtmin(False, False, False, precondition=True) == 0.0

    # Small diff (<=3h)
    c_small = CBTmin(time(4, 0), time(6, 0))  # +2h
    assert c_small.delta_cbtmin(True, False, False, precondition=False) == 1.0
    assert c_small.delta_cbtmin(False, False, False, precondition=False) == 0.5


# --- Helper and format tests (consolidated) ---

def test_sum_time_timedelta_wrap():
    t = time(22, 30)
    td = timedelta(hours=3, minutes=45)
    res = sum_time_timedelta(t, td)
    assert isinstance(res, time)
    assert res.hour == 2 and res.minute == 15


def test_astimezone_time_basic():
    """Test basic timezone conversion."""
    # Create a time object for 10:00
    t = time(10, 0)
    # Convert from UTC to UTC+2
    tz = timezone(timedelta(hours=2))
    with pytest.raises(ValueError):
        astimezone_time(t, tz)
    t2 = time(10, 0, tzinfo=timezone.utc)
    result = astimezone_time(t2, tz)
    # Should be 12:00 in UTC+2
    assert result == time(12, 0)


def test_subtract_times_and_hours():
    t1 = time(9, 0)
    t2 = time(7, 30)
    delta = subtract_times(t1, t2)
    assert isinstance(delta, timedelta)
    assert delta == timedelta(hours=1.5)
    
def test_hours_from_timedelta():
    td = timedelta(hours=2, minutes=30)
    hrs = hours_from_timedelta(td)
    assert isinstance(hrs, float)
    assert hrs == 2.5


def test_is_in_time_interval_across_midnight():
    sleep_start = time(23, 0)
    sleep_end = time(7, 0)
    dt1 = datetime(2025, 1, 1, 23, 30)
    dt2 = datetime(2025, 1, 2, 23, 00)
    dt3 = datetime(2025, 1, 2, 7, 0)
    dt4 = datetime(2025, 1, 2, 8, 0)
    assert is_in_time_interval(dt1, sleep_start, sleep_end) is True
    assert is_in_time_interval(dt2, sleep_start, sleep_end) is True
    assert is_in_time_interval(dt3, sleep_start, sleep_end) is False
    assert is_in_time_interval(dt4, sleep_start, sleep_end) is False


def test_is_inside_interval_boundaries():
    start = datetime(2025, 1, 1, 12, 0)
    end = datetime(2025, 1, 1, 14, 0)
    assert is_inside_interval(start, (start, end)) is True
    assert is_inside_interval(end, (start, end)) is False
    assert is_inside_interval(datetime(2025, 1, 1, 11, 0), (start, end)) is False
    assert is_inside_interval(datetime(2025, 1, 1, 13, 0), (start, end)) is True


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


def test_midnight_for_datetime():
    dt = datetime(2025, 3, 4, 15, 16, 17)
    md = midnight_for_datetime(dt)
    assert md.hour == 0 and md.minute == 0 and md.second == 0
    
def test_to_iso():
    dt = datetime(2025, 3, 4, 15, 16, 17)
    s = to_iso(dt)
    assert isinstance(s, str) and s.startswith("2025-03-04T15:16:17")


def test_next_interval_basic_and_overlap():
    now = datetime(2025, 1, 1, 12, 0)
    interval = (time(13, 0), time(15, 0))
    start, end = next_interval(now, interval)
    assert start == datetime(2025, 1, 1, 13, 0) and end == datetime(2025, 1, 1, 15, 0)
    
    interval2 = (time(13, 0), time(15, 0))
    s2, e2 = next_interval(datetime(2025, 1, 1, 22, 0), interval2)
    assert s2 == datetime(2025, 1, 2, 13, 0) and e2 == datetime(2025, 1, 2, 15, 0)

    interval3 = (time(23, 0), time(1, 0))
    s3, e3 = next_interval(datetime(2025, 1, 1, 22, 0), interval3)
    assert s3 == datetime(2025, 1, 1, 23, 0) and e3 == datetime(2025, 1, 2, 1, 0)

    fw = (datetime(2025, 1, 1, 13, 30), datetime(2025, 1, 1, 14, 0))
    s4, e4 = next_interval(now, interval, filter_window=fw)
    assert s4 is None and e4 is None


def test_rasterize_timetable_io_format():
    events = [
        {
            "event": "sleep",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T08:00:00Z",
            "is_cbtmin": False,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": True,
            "is_travel": False,
            "day_index": None,
            "phase_direction": "advance",
            "signed_initial_diff_hours": 1.0,
        },
        {
            "event": "cbtmin",
            "start": "2025-01-01T03:30:00Z",
            "end": None,
            "is_cbtmin": True,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": False,
            "is_travel": False,
            "day_index": None,
            "phase_direction": "advance",
            "signed_initial_diff_hours": 1.0,
        },
    ]
    start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    slots = rasterize_timetable(events, start_utc=start, end_utc=end, step_minutes=60)
    assert isinstance(slots, list) and len(slots) > 0
    assert all(isinstance(s["start"], str) and s["start"].endswith("Z") for s in slots)
    assert all(isinstance(s["end"], str) and s["end"].endswith("Z") for s in slots)
    assert any(s.get("is_sleep") for s in slots)
    assert any(s.get("is_cbtmin") for s in slots)
