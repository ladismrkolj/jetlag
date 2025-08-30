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

def is_sleep_time(dt: datetime, sleep_start: time, sleep_end: time) -> bool:
    """Determine if it's sleep time at the given datetime using local sleep schedule."""
    time_of_day = dt.time()
    if sleep_start <= sleep_end:
        return sleep_start <= time_of_day < sleep_end
    else:  # Sleep schedule crosses midnight
        return time_of_day >= sleep_start or time_of_day < sleep_end

def calculate_next_cbtmin(current_time: datetime, target_time: datetime, 
                      num_interventions: int, delay: bool, 
                      travel_window: tuple[datetime, datetime],
                      pre_travel_days: int = 0) -> float:
    """Calculate the shift for the next CBTmin based on current conditions."""
    # Check if we're in the adjustment period
    is_during_travel = travel_window[0] <= current_time <= travel_window[1]
    is_before_travel = current_time < travel_window[0]
    
    # Calculate how many days before travel we are
    days_before_travel = (travel_window[0] - current_time).days if is_before_travel else 0
    
    # Only adjust if:
    # 1. We're after travel, or
    # 2. We're before travel but within the pre-travel adjustment window
    if is_before_travel:
        if pre_travel_days <= 0 or days_before_travel > pre_travel_days:
            return 0
    
    if is_during_travel:
        return 0  # No adjustments during travel
        
    # Calculate time difference to target
    time_diff = abs(hours_from_timedelta(subtract_times(
        astimezone_time(current_time.time(), timezone.utc), 
        astimezone_time(target_time.time(), timezone.utc)
    )))
    
    # Determine shift rate based on number of interventions and proximity to target
    if num_interventions == 0:
        shift = 0.5
    elif num_interventions == 1:
        shift = 1.0
    else:  # 2 or 3 interventions
        shift = 1.5 if time_diff >= 3 else 1.0
        
    return shift if delay else -shift

def midpoint_time(t1: time, t2: time) -> time:
    # Pick an arbitrary reference date
    ref = date(2000, 1, 1)

    dt1 = datetime.combine(ref, t1)
    # If t2 ≤ t1, roll t2 into the next day
    dt2_date = ref if (t2 > t1) else ref + timedelta(days=1)
    dt2 = datetime.combine(dt2_date, t2)

    mid_dt = dt1 + (dt2 - dt1) / 2
    return mid_dt.time()

# %%
t1 = time(23, 30)
t2 = time(23, 30)
mid_time = midpoint_time(t1, t2)
print(f"Midpoint time between {t1} and {t2} is {mid_time}")

# %%
# Configuration parameters
PRE_TRAVEL_ADJUSTMENT_DAYS = 3  # How many days before travel to start adjusting CBTmin

# input data in local time zones
tz1 = 5
tz2 = 8

tz1_sleep_start_ltz = time(23, 30, tzinfo=timezone(timedelta(hours=tz1)))
tz1_sleep_stop_ltz = time(7, 30,tzinfo=timezone(timedelta(hours=tz1)))

tz2_sleep_start_ltz = time(23, 30, tzinfo=timezone(timedelta(hours=tz2)))
tz2_sleep_stop_ltz = time(7, 30, tzinfo=timezone(timedelta(hours=tz2)))

travel_start_ltz = datetime(2025, 6, 1, 4, 30, tzinfo=timezone(timedelta(hours=tz1)))
travel_stop_ltz = datetime(2025, 6, 2, 14, 30, tzinfo=timezone(timedelta(hours=tz2)))

# %%
travel_start = travel_start_ltz.astimezone(timezone.utc)
travel_stop = travel_stop_ltz.astimezone(timezone.utc)

travel_window = (travel_stop, travel_stop)

print(f"Travel start: {travel_start.isoformat()}")
print(f"Travel stop:  {travel_stop.isoformat()}")

# %%
total_travel_time = travel_stop - travel_start
print(f"Total travel time: {total_travel_time}")

# %%
start_date = travel_start.date()
print(f"Start date in UTC: {start_date.isoformat()}")

# %%
def sum_time_timedelta(t: time, delta: timedelta) -> time:
    # Use a mid-range date so subtraction can't underflow
    ref_date = date(2000, 1, 1)
    dt = datetime.combine(ref_date, t) + delta
    new_t = dt.time()
    return new_t.replace(tzinfo=t.tzinfo) if t.tzinfo else new_t

# %%
def astimezone_time(t: time, tz: timezone) -> time:
    """Convert local time to UTC."""
    ref_date = date(2000, 1, 1)
    dt = datetime.combine(ref_date, t).astimezone(tz)
    return dt.time().replace(tzinfo=tz)

# %%
# first CBTmin datetime object is combined from the time calculated and from the start date
CBTmin_time_start_ltz = sum_time_timedelta(tz1_sleep_stop_ltz, timedelta(hours=-3))
print(f"CBTmin start time in LTZ: {CBTmin_time_start_ltz}")
CBTmin_time_start = astimezone_time(CBTmin_time_start_ltz, timezone.utc)
print(f"CBTmin start time in UTC: {CBTmin_time_start}")

first_CBTmin = datetime.combine(start_date, tz1_sleep_start_ltz, tzinfo=timezone.utc)
print(f"First CBTmin in UTC: {first_CBTmin.isoformat()}")

CBTmin_time_dest_ltz = sum_time_timedelta(tz2_sleep_stop_ltz, timedelta(hours=-3))
print(f"CBTmin dest time in LTZ: {CBTmin_time_dest_ltz}")
CBTmin_time_dest = astimezone_time(CBTmin_time_dest_ltz, timezone.utc)
print(f"CBTmin dest time in UTC: {CBTmin_time_dest}")

# %%
def subtract_times(t1: time, t2: time):
    ref_date = date(2000, 1, 1)
    dt1 = datetime.combine(ref_date, t1)
    dt2 = datetime.combine(ref_date, t2)
    return dt1 - dt2

# %%
def hours_from_timedelta(td: timedelta) -> float:
    return td.total_seconds() / 3600.0

# %%
delta_cbtmin = subtract_times(CBTmin_time_dest, CBTmin_time_start)
print(f"Delta CBTmin: {delta_cbtmin}")
print(f"Delta CBTmin in hours: {hours_from_timedelta(delta_cbtmin)}")

# %%
if abs(hours_from_timedelta(delta_cbtmin)) < 3:
    print("CBTmin times are close enough, no adjustment needed.")

if hours_from_timedelta(delta_cbtmin) > 0:
    print("CBTmin at destination is later than at origin")
    delay = True
else:
    print("CBTmin at destination is earlier than at origin")
    delay = False
    

# %%
# numbers from article, relative to CBTmin
melatonin_advance = timedelta(hours=-11.5)
melatonin_delay = timedelta(hours=4)

light_advance_window = (timedelta(hours=0), timedelta(hours=3))
light_delay_window = (timedelta(hours=-3), timedelta(hours=0))
                        
dark_advance_window = (timedelta(hours=-3), timedelta(hours=0))
dark_delay_window = (timedelta(hours=0), timedelta(hours=3))

exercise_advance_window = (timedelta(hours=0), timedelta(hours=3))
exercise_delay_window = (timedelta(hours=-3), timedelta(hours=0))

# %%
use_melatonin = True
use_light = True
use_exercise = True
take_melatonin_while_traveling = True
light_when_traveling = True
exercise_when_traveling = True

# %%
CBTmin_times = []

a=True
i=0
while a:
    i += 1
    if i == 1:
        CBTmin_times.append(first_CBTmin)
        continue
    next_CBTmin = CBTmin_times[-1] + timedelta(hours=24)
    # Count number of active interventions
    active_interventions = sum([use_melatonin, use_light, use_exercise])
    
    # Calculate shift using the new function
    shift = calculate_next_cbtmin(
        current_time=next_CBTmin,
        target_time=datetime.combine(next_CBTmin.date(), CBTmin_time_dest),
        num_interventions=active_interventions,
        delay=delay,
        travel_window=travel_window,
        pre_travel_days=PRE_TRAVEL_ADJUSTMENT_DAYS
    )
    
    # Apply the calculated shift
    next_CBTmin += timedelta(hours=shift)
    CBTmin_times.append(next_CBTmin)
    print(f"Next CBTmin: {next_CBTmin.isoformat()}")
    if timedelta(hours=-0.5) < subtract_times(astimezone_time(next_CBTmin.time(), timezone.utc), CBTmin_time_dest) < timedelta(hours=0.5):
        a = False

print(f"Total CBTmin times: {CBTmin_times}")

# %%
melatonin_times = []
light_time_windows= []
dark_time_windows = []
exercise_time_windows = []

if use_melatonin:
    for cbt in CBTmin_times:
        if delay:
            melatonin_time = cbt + melatonin_delay
        else:
            melatonin_time = cbt + melatonin_advance
        #if take_melatonin_while_traveling:
        #    pass
        melatonin_times.append(melatonin_time)
        print(f"Melatonin time: {melatonin_time.isoformat()}")
        
        
if use_light:
    for cbt in CBTmin_times:
        if delay:
            light_time_window = (cbt + light_delay_window[0], cbt + light_delay_window[1])
            dark_time_window = (cbt + dark_delay_window[0], cbt + dark_delay_window[1])
        else:
            light_time_window = (cbt + light_advance_window[0], cbt + light_advance_window[1])
            dark_time_window = (cbt + dark_advance_window[0], cbt + dark_advance_window[1])
        #if light_when_traveling:
        #    pass
        light_time_windows.append(light_time_window)
        dark_time_windows.append(dark_time_window)
        print(f"Light time window: {light_time_window[0].isoformat()} - {light_time_window[1].isoformat()}")
        print(f"Dark time window: {dark_time_window[0].isoformat()} - {dark_time_window[1].isoformat()}")
        
if use_exercise:
    for cbt in CBTmin_times:
        if delay:
            exercise_time_window = (cbt + exercise_delay_window[0], cbt + exercise_delay_window[1])
        else:
            exercise_time_window = (cbt + exercise_advance_window[0], cbt + exercise_advance_window[1])
        #if exercise_when_traveling:
        #    pass
        exercise_time_windows.append(exercise_time_window)
        print(f"Exercise time window: {exercise_time_window[0].isoformat()} - {exercise_time_window[1].isoformat()}")

# %%
def is_sleep_time(dt: datetime, sleep_start: time, sleep_end: time) -> bool:
    """Determine if it's sleep time at the given datetime using local sleep schedule."""
    time_of_day = dt.time()
    if sleep_start <= sleep_end:
        return sleep_start <= time_of_day < sleep_end
    else:  # Sleep schedule crosses midnight
        return time_of_day >= sleep_start or time_of_day < sleep_end

def calculate_next_cbtmin(current_time: datetime, target_time: datetime, 
                      num_interventions: int, delay: bool, 
                      travel_window: tuple[datetime, datetime],
                      pre_travel_days: int = 0) -> float:
    """Calculate the shift for the next CBTmin based on current conditions."""
    # Check if we're in the adjustment period
    is_during_travel = travel_window[0] <= current_time <= travel_window[1]
    is_after_travel = current_time > travel_window[1]
    is_before_travel = current_time < travel_window[0]
    
    # Calculate how many days before travel we are
    days_before_travel = (travel_window[0] - current_time).days if is_before_travel else 0
    
    # Only adjust if:
    # 1. We're after travel, or
    # 2. We're before travel but within the pre-travel adjustment window
    if is_before_travel:
        if pre_travel_days <= 0 or days_before_travel > pre_travel_days:
            return 0
    
    if is_during_travel:
        return 0  # No adjustments during travel
        
    # Calculate time difference to target
    time_diff = abs(hours_from_timedelta(subtract_times(
        astimezone_time(current_time.time(), timezone.utc), 
        astimezone_time(target_time.time(), timezone.utc)
    )))
    
    # Determine shift rate based on number of interventions and proximity to target
    if num_interventions == 0:
        shift = 0.5
    elif num_interventions == 1:
        shift = 1.0
    else:  # 2 or 3 interventions
        shift = 1.5 if time_diff >= 3 else 1.0
        
    return shift if delay else -shift

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
    """
    Create a timeline of events with the specified resolution.
    Returns a list of dictionaries, each containing the status at that time point.
    """
    timeline = []
    current_time = start_time
    
    # Create time window buffer (15 minutes) for point-in-time events
    time_buffer = timedelta(minutes=15)
    
    while current_time <= end_time:
        # Initialize the event dictionary for this time point
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
            'local_time_origin': current_time.astimezone(timezone(timedelta(hours=tz1))).strftime('%H:%M'),
            'local_time_destination': current_time.astimezone(timezone(timedelta(hours=tz2))).strftime('%H:%M')
        }
        
        timeline.append(event)
        current_time += timedelta(minutes=resolution_minutes)
    
    return timeline

# %%
# Example usage:
start_time = travel_start - timedelta(days=2)  # Start 2 days before travel
end_time = travel_stop + timedelta(days=5)     # End 5 days after arrival
resolution = 30  # 30-minute resolution

timeline = create_timeline(
    start_time=start_time,
    end_time=end_time,
    resolution_minutes=resolution,
    CBTmin_times=CBTmin_times,
    melatonin_times=melatonin_times,
    light_time_windows=light_time_windows,
    dark_time_windows=dark_time_windows,
    exercise_time_windows=exercise_time_windows,
    travel_window=(travel_start, travel_stop),
    tz1=tz1,
    tz2=tz2,
    sleep_start_origin=tz1_sleep_start_ltz.replace(tzinfo=None),
    sleep_end_origin=tz1_sleep_stop_ltz.replace(tzinfo=None),
    sleep_start_dest=tz2_sleep_start_ltz.replace(tzinfo=None),
    sleep_end_dest=tz2_sleep_stop_ltz.replace(tzinfo=None)
)

# Print first few events as example
for event in timeline[:5]:
    print(f"Time (UTC): {event['timestamp']}")
    print(f"Origin ({tz1}): {event['local_time_origin']} {'[SLEEP]' if event['is_sleep_origin'] else ''}")
    print(f"Destination ({tz2}): {event['local_time_destination']} {'[SLEEP]' if event['is_sleep_destination'] else ''}")
    print(f"Traveling: {event['is_traveling']}")
    print(f"CBTmin: {event['is_cbtmin']}")
    print(f"Interventions: Melatonin={event['is_melatonin']}, Light={event['is_light_exposure']}, Dark={event['is_dark_period']}, Exercise={event['is_exercise']}")
    print("---")