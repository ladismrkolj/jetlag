# %%
from datetime import datetime, date, time, timedelta, timezone

def sum_time_timedelta(t: time, td: timedelta) -> time:
    """Add a timedelta to a time."""
    ref_date = date(2000, 1, 1)
    dt = datetime.combine(ref_date, t)
    result_dt = dt + td
    return result_dt.time()

def astimezone_time(t: time, tz: timezone) -> time:
    """Convert a time to a different timezone."""
    ref_date = date(2000, 1, 1)
    dt = datetime.combine(ref_date, t)
    result_dt = dt.astimezone(tz)
    return result_dt.time()

def subtract_times(t1: time, t2: time) -> timedelta:
    """Subtract two times."""
    ref_date = date(2000, 1, 1)
    dt1 = datetime.combine(ref_date, t1)
    dt2 = datetime.combine(ref_date, t2)
    return dt1 - dt2

def hours_from_timedelta(td: timedelta) -> float:
    """Convert a timedelta to hours (can be fractional)"""
    return td.total_seconds() / 3600

def midpoint_time(t1: time, t2: time) -> time:
    """Calculate the midpoint between two times.
    
    If t1 and t2 are the same, returns that time.
    Otherwise, calculates the midpoint considering midnight crossover if needed.
    """
    if t1 == t2:
        return t1
        
    ref = date(2000, 1, 1)
    dt1 = datetime.combine(ref, t1)
    dt2_date = ref if (t2 > t1) else ref + timedelta(days=1)
    dt2 = datetime.combine(dt2_date, t2)
    mid_dt = dt1 + (dt2 - dt1) / 2
    return mid_dt.time()

def is_sleep_time(dt: datetime, sleep_start: time, sleep_end: time) -> bool:
    """Determine if it's sleep time at the given datetime using local sleep schedule."""
    time_of_day = dt.time()
    if sleep_start <= sleep_end:
        return sleep_start <= time_of_day < sleep_end
    else:  # Sleep schedule crosses midnight
        return time_of_day >= sleep_start or time_of_day < sleep_end

class JetlagError(Exception):
    """Custom exception for jetlag calculation errors."""
    pass

# Intervention timing constants (relative to CBTmin)
MELATONIN_ADVANCE = timedelta(hours=-11.5)  # Take melatonin 11.5 hours before CBTmin when advancing
MELATONIN_DELAY = timedelta(hours=4)        # Take melatonin 4 hours after CBTmin when delaying

# Light exposure windows (relative to CBTmin)
LIGHT_ADVANCE_WINDOW = (timedelta(hours=0), timedelta(hours=3))    # 0-3 hours after CBTmin
LIGHT_DELAY_WINDOW = (timedelta(hours=-3), timedelta(hours=0))     # 0-3 hours before CBTmin

# Dark period windows (relative to CBTmin)
DARK_ADVANCE_WINDOW = (timedelta(hours=-3), timedelta(hours=0))    # 0-3 hours before CBTmin
DARK_DELAY_WINDOW = (timedelta(hours=0), timedelta(hours=3))       # 0-3 hours after CBTmin

# Exercise windows (relative to CBTmin)
EXERCISE_ADVANCE_WINDOW = (timedelta(hours=0), timedelta(hours=3))  # 0-3 hours after CBTmin
EXERCISE_DELAY_WINDOW = (timedelta(hours=-3), timedelta(hours=0))   # 0-3 hours before CBTmin

def calculate_intervention_times(
    cbtmin_times: list[datetime],
    delay: bool,
    use_melatonin: bool = True,
    use_light: bool = True,
    use_exercise: bool = True
) -> tuple[list[datetime], list[tuple[datetime, datetime]], list[tuple[datetime, datetime]], list[tuple[datetime, datetime]]]:
    """Calculate intervention times based on CBTmin times.
    
    Args:
        cbtmin_times: List of CBTmin times
        delay: Whether to use delay timings (True) or advance timings (False)
        use_melatonin: Whether to include melatonin interventions
        use_light: Whether to include light/dark interventions
        use_exercise: Whether to include exercise interventions
    
    Returns:
        Tuple of (melatonin_times, light_windows, dark_windows, exercise_windows)
        where each element is a list of times or time windows for that intervention
    """
    melatonin_times = []
    light_windows = []
    dark_windows = []
    exercise_windows = []
    
    for cbt in cbtmin_times:
        # Calculate melatonin times
        if use_melatonin:
            melatonin_time = cbt + (MELATONIN_DELAY if delay else MELATONIN_ADVANCE)
            melatonin_times.append(melatonin_time)
        
        # Calculate light and dark windows
        if use_light:
            if delay:
                light_window = (cbt + LIGHT_DELAY_WINDOW[0], cbt + LIGHT_DELAY_WINDOW[1])
                dark_window = (cbt + DARK_DELAY_WINDOW[0], cbt + DARK_DELAY_WINDOW[1])
            else:
                light_window = (cbt + LIGHT_ADVANCE_WINDOW[0], cbt + LIGHT_ADVANCE_WINDOW[1])
                dark_window = (cbt + DARK_ADVANCE_WINDOW[0], cbt + DARK_ADVANCE_WINDOW[1])
            light_windows.append(light_window)
            dark_windows.append(dark_window)
        
        # Calculate exercise windows
        if use_exercise:
            if delay:
                exercise_window = (cbt + EXERCISE_DELAY_WINDOW[0], cbt + EXERCISE_DELAY_WINDOW[1])
            else:
                exercise_window = (cbt + EXERCISE_ADVANCE_WINDOW[0], cbt + EXERCISE_ADVANCE_WINDOW[1])
            exercise_windows.append(exercise_window)
    
    return melatonin_times, light_windows, dark_windows, exercise_windows

def calculate_next_cbtmin(current_time: datetime, target_time: datetime, 
                      num_interventions: int, delay: bool, 
                      travel_window: tuple[datetime, datetime],
                      pre_travel_days: int = 0) -> float:
    """Calculate the shift for the next CBTmin based on current conditions.
    
    Args:
        current_time: Current CBTmin time
        target_time: Target CBTmin time
        num_interventions: Number of active interventions (0-3)
        delay: Whether we need to delay (True) or advance (False) the CBTmin
        travel_window: Tuple of (travel_start, travel_stop) times
        pre_travel_days: Number of days before travel to start adjustments (default: 0)
    
    Returns:
        float: Hours to shift CBTmin (positive for delay, negative for advance)
        
    Raises:
        TypeError: If inputs are of wrong type or missing timezone info
        ValueError: If input values are out of valid ranges
    """
    # Validate inputs
    if not isinstance(current_time, datetime):
        raise TypeError("current_time must be a datetime object")
    if not current_time.tzinfo:
        raise ValueError("current_time must have timezone information")
        
    if not isinstance(target_time, datetime):
        raise TypeError("target_time must be a datetime object")
    if not target_time.tzinfo:
        raise ValueError("target_time must have timezone information")
        
    if not isinstance(num_interventions, int):
        raise TypeError("num_interventions must be an integer")
    if num_interventions < 0 or num_interventions > 3:
        raise ValueError("num_interventions must be between 0 and 3")
        
    if not isinstance(delay, bool):
        raise TypeError("delay must be a boolean")
        
    if not isinstance(pre_travel_days, int):
        raise TypeError("pre_travel_days must be an integer")
    if pre_travel_days < 0:
        raise ValueError("pre_travel_days must be non-negative")
        
    if not isinstance(travel_window, tuple):
        raise TypeError("travel_window must be a tuple")
    if len(travel_window) != 2:
        raise ValueError("travel_window must contain exactly two datetimes (start, stop)")
    if not all(isinstance(t, datetime) for t in travel_window):
        raise TypeError("travel_window times must be datetime objects")
    if not all(t.tzinfo for t in travel_window):
        raise ValueError("travel_window times must have timezone information")
    if travel_window[0] > travel_window[1]:
        raise ValueError("travel_window start must be before end")

    # Convert travel window times to UTC for consistent comparison
    travel_start_utc = travel_window[0].astimezone(timezone.utc)
    travel_stop_utc = travel_window[1].astimezone(timezone.utc)
    
    # Check time periods
    is_during_travel = travel_start_utc <= current_time <= travel_stop_utc
    is_before_travel = current_time < travel_start_utc
    
    # No adjustments during travel
    if is_during_travel:
        return 0
    
    # Check pre-travel window
    days_before_travel = 0
    if is_before_travel:
        days_before_travel = (travel_start_utc - current_time).days
        # Don't adjust if too far before travel
        if days_before_travel > pre_travel_days:
            return 0
        
    # Calculate time difference to target in hours more accurately
    diff = target_time - current_time
    diff_hours = diff.total_seconds() / 3600.0
    if diff_hours > 12:
        diff_hours -= 24
    elif diff_hours < -12:
        diff_hours += 24

    # No adjustment needed if at target
    if abs(diff_hours) < 0.1:  # Within 6 minutes
        return 0
    
    # Base shift rate depends on number of interventions and time difference
    if num_interventions == 0:
        shift = 0.5
    elif num_interventions == 1:
        shift = 1.0
    else:  # 2 or 3 interventions
        shift = 1.5 if abs(diff_hours) >= 3 else 1.0

    # The direction of the shift depends on two things:
    # 1. Whether we want to delay or advance (delay param)
    # 2. Whether we need to move forward or backward to reach target
    
    # First set the shift direction based on whether we want to delay
    shift = shift if delay else -shift
    
    # Then flip the sign if we're not moving in the right direction
    target_after = diff_hours > 0  # Target is after current
    
    # If (we want to delay and target is before) or
    # (we want to advance and target is after)
    # then we need to flip the direction
    if delay != target_after:
        shift = -shift
    
    return shift

def calculate_cbtmin_times(
    start_time: datetime,
    target_time: datetime,
    travel_window: tuple[datetime, datetime],
    end_time: datetime,
    num_interventions: int = 2,
    pre_travel_days: int = 3
) -> list[datetime]:
    """Calculate all CBTmin times from start to end, adjusting for jet lag.
    
    Args:
        start_time: Initial CBTmin time
        target_time: Target CBTmin time in destination timezone
        travel_window: (travel_start, travel_stop) times
        end_time: When to stop calculating CBTmin times
        num_interventions: Number of interventions to use (0-3)
        pre_travel_days: Days before travel to start adjusting
    
    Returns:
        List of CBTmin times from start to end
    """
    cbtmin_times = [start_time]
    current_time = start_time
    
    # Calculate whether we need to delay or advance
    time_diff = (target_time - start_time).total_seconds() / 3600
    while time_diff > 12:  # Normalize to -12 to +12 range
        time_diff -= 24
    while time_diff < -12:
        time_diff += 24
    delay = time_diff > 0
    
    while current_time < end_time:
        # Calculate next CBTmin shift
        shift = calculate_next_cbtmin(
            current_time=current_time,
            target_time=target_time,
            num_interventions=num_interventions,
            delay=delay,
            travel_window=travel_window,
            pre_travel_days=pre_travel_days
        )
        
        # If no shift is needed, just move to next day
        if abs(shift) < 0.1:  # Less than 6 minutes
            next_time = current_time + timedelta(days=1)
        else:
            next_time = current_time + timedelta(hours=shift)
        
        cbtmin_times.append(next_time)
        current_time = next_time
    
    return cbtmin_times

def create_timeline(
    start_time: datetime,
    end_time: datetime,
    resolution_minutes: int,
    CBTmin_times: list[datetime],
    melatonin_times: list[datetime],
    light_time_windows: list[tuple[datetime, datetime]],
    dark_time_windows: list[tuple[datetime, datetime]],
    exercise_time_windows: list[tuple[datetime, datetime]],
    travel_window: tuple[datetime, datetime],
    tz1: int,
    tz2: int,
    sleep_start_origin: time,
    sleep_end_origin: time,
    sleep_start_dest: time,
    sleep_end_dest: time
) -> list[dict]:
    """Create a timeline of all events and status changes.
    
    Returns a list of dictionaries, each containing the status at that time point.
    """
    timeline = []
    current_time = start_time
    
    # Create time window buffer (15 minutes) for point-in-time events
    time_buffer = timedelta(minutes=15)
    
    while current_time <= end_time:
        # Convert current time to origin and destination timezones
        time_in_tz1 = current_time.astimezone(timezone(timedelta(hours=tz1)))
        time_in_tz2 = current_time.astimezone(timezone(timedelta(hours=tz2)))
        
        event = {
            'timestamp': current_time,
            'is_sleep_origin': is_sleep_time(time_in_tz1, sleep_start_origin, sleep_end_origin),
            'is_sleep_destination': is_sleep_time(time_in_tz2, sleep_start_dest, sleep_end_dest),
            'is_traveling': travel_window[0] <= current_time <= travel_window[1],
            'is_cbtmin': any(abs(current_time - cbt) <= time_buffer for cbt in CBTmin_times),
            'is_melatonin': any(abs(current_time - mel) <= time_buffer for mel in melatonin_times),
            'is_light_exposure': any(start <= current_time <= end for start, end in light_time_windows),
            'is_dark_period': any(start <= current_time <= end for start, end in dark_time_windows),
            'is_exercise': any(start <= current_time <= end for start, end in exercise_time_windows),
            'timezone_origin': tz1,
            'timezone_destination': tz2,
            'local_time_origin': time_in_tz1.strftime('%H:%M'),
            'local_time_destination': time_in_tz2.strftime('%H:%M')
        }
        
        timeline.append(event)
        current_time += timedelta(minutes=resolution_minutes)
    
    return timeline

def create_jet_lag_schedule(
    travel_start: datetime,
    travel_stop: datetime,
    origin_timezone: timezone,
    destination_timezone: timezone,
    sleep_start: time,
    sleep_end: time,
    days_before: int = 3,
    days_after: int = 5,
    num_interventions: int = 2,
    use_melatonin: bool = True,
    use_light: bool = True,
    use_exercise: bool = True,
    resolution_minutes: int = 30
) -> list[dict]:
    """Create a complete jet lag adjustment schedule.
    
    Args:
        travel_start: When travel begins (in any timezone, will be converted to UTC)
        travel_stop: When travel ends (in any timezone, will be converted to UTC)
        origin_timezone: Timezone of origin location
        destination_timezone: Timezone of destination location
        sleep_start: Desired sleep start time (local time, no timezone)
        sleep_end: Desired sleep end time (local time, no timezone)
        days_before: Days before travel to start adjusting
        days_after: Days after travel to continue adjusting
        num_interventions: Number of interventions to use (0-3)
        use_melatonin: Whether to include melatonin interventions
        use_light: Whether to include light/dark interventions
        use_exercise: Whether to include exercise interventions
        resolution_minutes: Time resolution for the timeline
    
    Returns:
        List of timeline events with all interventions
    """
    # Convert all times to UTC for calculations
    travel_start_utc = travel_start.astimezone(timezone.utc)
    travel_stop_utc = travel_stop.astimezone(timezone.utc)
    travel_window = (travel_start_utc, travel_stop_utc)
    
    # Calculate schedule boundaries
    schedule_start = travel_start_utc - timedelta(days=days_before)
    schedule_end = travel_stop_utc + timedelta(days=days_after)
    
    # Calculate initial and target CBTmin times (typically 2 hours before wake)
    initial_cbtmin = (datetime.combine(schedule_start.date(), sleep_end) - timedelta(hours=2))
    initial_cbtmin = initial_cbtmin.replace(tzinfo=origin_timezone).astimezone(timezone.utc)
    
    target_cbtmin = (datetime.combine(travel_stop_utc.date(), sleep_end) - timedelta(hours=2))
    target_cbtmin = target_cbtmin.replace(tzinfo=destination_timezone).astimezone(timezone.utc)
    
    # Calculate all CBTmin times
    cbtmin_times = calculate_cbtmin_times(
        start_time=initial_cbtmin,
        target_time=target_cbtmin,
        travel_window=travel_window,
        end_time=schedule_end,
        num_interventions=num_interventions,
        pre_travel_days=days_before
    )
    
    # Calculate time difference to determine delay/advance
    time_diff = (target_cbtmin - initial_cbtmin).total_seconds() / 3600
    while time_diff > 12:  # Normalize to -12 to +12 range
        time_diff -= 24
    while time_diff < -12:
        time_diff += 24
    delay = time_diff > 0
    
    # Calculate intervention times
    melatonin_times, light_windows, dark_windows, exercise_windows = calculate_intervention_times(
        cbtmin_times=cbtmin_times,
        delay=delay,
        use_melatonin=use_melatonin,
        use_light=use_light,
        use_exercise=use_exercise
    )
    
    # Create the timeline
    return create_timeline(
        start_time=schedule_start,
        end_time=schedule_end,
        resolution_minutes=resolution_minutes,
        CBTmin_times=cbtmin_times,
        melatonin_times=melatonin_times,
        light_time_windows=light_windows,
        dark_time_windows=dark_windows,
        exercise_time_windows=exercise_windows,
        travel_window=travel_window,
        tz1=int(origin_timezone.utcoffset(None).total_seconds() / 3600),
        tz2=int(destination_timezone.utcoffset(None).total_seconds() / 3600),
        sleep_start_origin=sleep_start,
        sleep_end_origin=sleep_end,
        sleep_start_dest=sleep_start,
        sleep_end_dest=sleep_end
    )
