import datetime
from datetime import timedelta

def parse_time_str(time_str):
    """
    Parse a string in "HH:MM" 24-hour format into a datetime.time object.
    """
    try:
        hours, minutes = map(int, time_str.split(":"))
        return datetime.time(hour=hours, minute=minutes)
    except ValueError:
        raise ValueError(f"Time string '{time_str}' is invalid. Use 'HH:MM' 24-hour format.")

def calculate_timezone_difference(start_offset: int, end_offset: int) -> int:
    """
    Return the number of hours difference between two time zone offsets.
    Positive means end_offset is ahead of start_offset.
    """
    return end_offset - start_offset

def plan_phase_shift(
    arrival_dt: datetime.datetime,
    normal_sleep_start: datetime.time,
    dest_sleep_start: datetime.time,
    tz_diff_hours: int,
    use_melatonin: bool,
    melatonin_dose_mg: float,
    use_light_control: bool
) -> list[dict]:
    """
    Simulate daily interventions until CBTmin aligns to destination sleep pattern.
    Returns a list of dictionaries, each containing:
      - 'date': datetime.date
      - 'current_CBTmin': datetime.time of predicted CBTmin
      - 'target_CBTmin': datetime.time of desired CBTmin
      - 'melatonin_time': datetime.time or None
      - 'light_exposure_window': tuple(start_time, end_time) or None
      - 'light_avoidance_window': tuple(start_time, end_time) or None
      - 'phase_shift': float hours applied that day
    """
    schedule = []
    # Estimate initial CBTmin: 6 hours after normal sleep start on arrival date
    today = arrival_dt.date()
    init_datetime = datetime.datetime.combine(today, normal_sleep_start) + timedelta(hours=6)
    current_CBTmin = init_datetime
    # Desired CBTmin: 6 hours after dest_sleep_start each day
    desired_datetime = datetime.datetime.combine(today, dest_sleep_start) + timedelta(hours=6)
    target_CBTmin = desired_datetime.time()

    day = 0
    # Continue until aligned within 0.5 hour
    while True:
        current_date = arrival_dt.date() + timedelta(days=day)
        curr_CBT_time = current_CBTmin.time()
        # Compute phase difference in hours, wrap to [-12,12]
        diff = (desired_datetime - current_CBTmin).total_seconds() / 3600
        if diff > 12:
            diff -= 24
        elif diff < -12:
            diff += 24
        # Check alignment
        if abs(diff) <= 0.5:
            schedule.append({
                'date': current_date,
                'current_CBTmin': curr_CBT_time,
                'target_CBTmin': target_CBTmin,
                'melatonin_time': None,
                'light_exposure_window': None,
                'light_avoidance_window': None,
                'phase_shift': 0.0
            })
            break
        # Determine direction: positive diff => advance (eastward), negative => delay (westward)
        if diff > 0:
            direction = 1
            if use_melatonin:
                mel_datetime = current_CBTmin - timedelta(hours=11.5)
                mel_time = mel_datetime.time()
            else:
                mel_time = None
            if use_light_control:
                le_start = (current_CBTmin + timedelta(hours=3)).time()
                le_end = (current_CBTmin + timedelta(hours=6)).time()
                light_exp = (le_start, le_end)
                la_start = (current_CBTmin - timedelta(hours=3)).time()
                la_end = curr_CBT_time
                light_avoid = (la_start, la_end)
            else:
                light_exp = None
                light_avoid = None
        else:
            direction = -1
            if use_melatonin:
                mel_datetime = current_CBTmin + timedelta(hours=4)
                mel_time = mel_datetime.time()
            else:
                mel_time = None
            if use_light_control:
                le_start = (current_CBTmin - timedelta(hours=6)).time()
                le_end = (current_CBTmin - timedelta(hours=3)).time()
                light_exp = (le_start, le_end)
                la_start = curr_CBT_time
                la_end = (current_CBTmin + timedelta(hours=3)).time()
                light_avoid = (la_start, la_end)
            else:
                light_exp = None
                light_avoid = None
        # Estimate phase shift magnitude: 1h from melatonin, 1h from light, in direction
        shift = 0.0
        if use_melatonin:
            shift += 1.0 * direction
        if use_light_control:
            shift += 1.0 * direction
        # Prevent overshoot
        if abs(shift) > abs(diff):
            shift = diff
        current_CBTmin = current_CBTmin + timedelta(hours=shift)
        schedule.append({
            'date': current_date,
            'current_CBTmin': curr_CBT_time,
            'target_CBTmin': target_CBTmin,
            'melatonin_time': mel_time,
            'light_exposure_window': light_exp,
            'light_avoidance_window': light_avoid,
            'phase_shift': shift
        })
        day += 1
        # Update desired CBTmin for next day
        desired_date = arrival_dt.date() + timedelta(days=day)
        desired_datetime = datetime.datetime.combine(desired_date, dest_sleep_start) + timedelta(hours=6)
        target_CBTmin = desired_datetime.time()
    return schedule

def generate_timetable(schedule: list[dict]) -> list[dict]:
    """
    Convert schedule into hourly grid. Flags: 'M','+' for exposure, '-' for avoidance, 'T' for CBTmin.
    """
    timetable = []
    for entry in schedule:
        date = entry['date']
        hours = {h: set() for h in range(24)}
        # Mark CBTmin
        t_hour = entry['current_CBTmin'].hour
        hours[t_hour].add('T')
        # Mark Melatonin
        if entry['melatonin_time']:
            m_hour = entry['melatonin_time'].hour
            hours[m_hour].add('M')
        # Mark Light Exposure
        le_window = entry.get('light_exposure_window')
        if le_window:
            start, end = le_window
            if start <= end:
                for h in range(start.hour, end.hour + 1): hours[h].add('+')
            else:
                for h in range(start.hour, 24): hours[h].add('+')
                for h in range(0, end.hour + 1): hours[h].add('+')
        # Mark Light Avoidance
        la_window = entry.get('light_avoidance_window')
        if la_window:
            start, end = la_window
            if start <= end:
                for h in range(start.hour, end.hour + 1): hours[h].add('-')
            else:
                for h in range(start.hour, 24): hours[h].add('-')
                for h in range(0, end.hour + 1): hours[h].add('-')
        timetable.append({'date': date, 'hours': hours})
    return timetable

def print_timetable(timetable: list[dict]):
    """
    Print aligned ASCII table.
    """
    header = f"{'Date':<10} |"
    for h in range(24): header += f"{h:>3}"
    print(header)
    print('-' * len(header))
    for day in timetable:
        row = f"{day['date'].isoformat():<10} |"
        for h in range(24):
            flags = day['hours'][h]
            if 'M' in flags: cell = 'M'
            elif 'T' in flags: cell = 'T'
            elif '+' in flags: cell = '+'
            elif '-' in flags: cell = '-'
            else: cell = '.'
            row += f"{cell:>3}"
        print(row)

# Basic test cases
if __name__ == "__main__":
    # Test 1: No shift needed (tz_diff = 0, no interventions)
    normal_sleep_start = parse_time_str("23:00")
    arrival_dt = datetime.datetime.strptime("2025-06-20 00:00", "%Y-%m-%d %H:%M")
    dest_sleep_start = parse_time_str("23:00")
    tz_diff_zero = calculate_timezone_difference(0, 0)
    sched_zero = plan_phase_shift(
        arrival_dt=arrival_dt,
        normal_sleep_start=normal_sleep_start,
        dest_sleep_start=dest_sleep_start,
        tz_diff_hours=tz_diff_zero,
        use_melatonin=False,
        melatonin_dose_mg=0.0,
        use_light_control=False
    )
    assert len(sched_zero) == 1
    assert sched_zero[0]['phase_shift'] == 0.0

    # Test 2: Simple eastward shift with melatonin only
    tz_diff_east = calculate_timezone_difference(0, 3)
    sched_east = plan_phase_shift(
        arrival_dt=arrival_dt,
        normal_sleep_start=normal_sleep_start,
        dest_sleep_start=parse_time_str("22:00"),
        tz_diff_hours=tz_diff_east,
        use_melatonin=True,
        melatonin_dose_mg=3.0,
        use_light_control=False
    )
    # Should require at least one shift entry
    assert len(sched_east) >= 1
    assert all('melatonin_time' in entry for entry in sched_east)

    # Print a sample timetable
    tt = generate_timetable(sched_east)
    print_timetable(tt)
