import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone, time

from jetlag_core import create_jet_lag_timetable


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
    # all timestamps are ISO Z strings where present
    for e in events:
        if isinstance(e.get("start"), str):
            assert e["start"].endswith("Z")
        if isinstance(e.get("end"), str):
            assert e["end"].endswith("Z")
