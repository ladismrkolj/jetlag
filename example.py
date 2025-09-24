from datetime import datetime, time, timedelta, timezone
from jetlag_core import create_jet_lag_timetable, rasterize_timetable

def main():
    # Example: Trip from New York (UTC-4) to Paris (UTC+2)
    ny_tz = 5
    paris_tz = 1

    travel_start = datetime(2025, 9, 10, 18, 0)
    travel_end = datetime(2025, 9, 11, 8, 0)

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
        use_light_dark=False,
        precondition_days=0,
        shift_on_travel_days=False
    )

    # Print a brief summary of raw events
    print("Jet Lag Timetable (UTC) — first 10 events:")
    for e in events:
        print(e)

    # Rasterize into 30-minute slots over a 5-day window around travel
    start_window = min(travel_start - timedelta(days=2),
                       travel_end- timedelta(days=2))
    end_window = travel_end + timedelta(days=3)
    slots = rasterize_timetable(events, start_utc=start_window, end_utc=end_window, step_minutes=30)

    print("\nRasterized slots (first 10):")
    for s in slots[:10]:
        print(s)

if __name__ == "__main__":
    main()
