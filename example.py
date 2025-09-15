from datetime import datetime, time, timedelta, timezone
from jetlag_core import create_jet_lag_timetable

def main():
    # Example: Trip from New York (UTC-4) to Paris (UTC+2)
    ny_tz = timezone(timedelta(hours=-4))
    paris_tz = timezone(timedelta(hours=2))

    travel_start = datetime(2025, 9, 10, 18, 0, tzinfo=ny_tz)
    travel_end = datetime(2025, 9, 11, 8, 0, tzinfo=paris_tz)

    # Habitual sleep windows in local time
    origin_sleep_start = time(23, 0)
    origin_sleep_end = time(7, 0)
    destination_sleep_start = time(23, 0)
    destination_sleep_end = time(7, 0)

    events = create_jet_lag_timetable(
        origin_timezone=ny_tz,
        destination_timezone=paris_tz,
        origin_sleep_start=origin_sleep_start,
        origin_sleep_end=origin_sleep_end,
        destination_sleep_start=destination_sleep_start,
        destination_sleep_end=destination_sleep_end,
        travel_start=travel_start,
        travel_end=travel_end,
        use_melatonin=True,
        use_exercise=False,
        use_light_dark=True,
        precondition_days=2,
    )

    # Print a brief summary
    print("Jet Lag Timetable (UTC)")
    for e in events[:10]:  # show first 10
        print(e)

if __name__ == "__main__":
    main()
