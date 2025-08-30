import pytest
from datetime import datetime, time, timedelta, timezone
from typing import Dict, List, Tuple
from jetlag_core import (
    midpoint_time, 
    sum_time_timedelta, 
    astimezone_time, 
    subtract_times,
    calculate_next_cbtmin,
    is_sleep_time,
    create_timeline
)

def is_valid_time_window(window: Tuple[datetime, datetime]) -> bool:
    """Helper function to validate time windows."""
    return (
        isinstance(window, tuple) and
        len(window) == 2 and
        isinstance(window[0], datetime) and
        isinstance(window[1], datetime) and
        window[0] <= window[1]
    )

@pytest.fixture
def test_times():
    """Fixture providing common test times."""
    return {
        'base_date': datetime(2025, 6, 1, tzinfo=timezone.utc),
        'sleep_start': time(23, 30),
        'sleep_end': time(7, 30),
        'travel_start': datetime(2025, 6, 1, 9, 30, tzinfo=timezone.utc),  # 4:30 UTC+5
        'travel_stop': datetime(2025, 6, 2, 6, 30, tzinfo=timezone.utc)   # 14:30 UTC+8
    }

@pytest.fixture
def test_timezones():
    """Fixture providing timezone information."""
    return {
        'origin': 5,    # UTC+5
        'destination': 8 # UTC+8
    }

def test_midpoint_time():
    """Test midpoint time calculation."""
    # Test across midnight
    t1 = time(22, 0)  # 10 PM
    t2 = time(2, 0)   # 2 AM next day
    mid = midpoint_time(t1, t2)
    assert mid.hour == 0
    assert mid.minute == 0

    # Test same day times
    t3 = time(10, 0)  # 10 AM
    t4 = time(14, 0)  # 2 PM
    mid = midpoint_time(t3, t4)
    assert mid.hour == 12
    assert mid.minute == 0

    # Test same time
    mid = midpoint_time(t1, t1)
    assert mid == t1

def test_time_zone_conversions():
    """Test timezone conversion utilities."""
    # Test astimezone_time
    local_time = time(10, 0, tzinfo=timezone(timedelta(hours=5)))
    utc_time = astimezone_time(local_time, timezone.utc)
    assert utc_time.hour == 5

    # Test sum_time_timedelta
    base_time = time(10, 0)
    delta = timedelta(hours=2)
    new_time = sum_time_timedelta(base_time, delta)
    assert new_time.hour == 12

def test_sleep_time_detection(test_times):
    """Test sleep time detection."""
    sleep_start = test_times['sleep_start']
    sleep_end = test_times['sleep_end']
    
    # Test during sleep time
    dt_during_sleep = datetime(2025, 6, 1, 2, 0)
    assert is_sleep_time(dt_during_sleep, sleep_start, sleep_end)
    
    # Test during wake time
    dt_during_wake = datetime(2025, 6, 1, 12, 0)
    assert not is_sleep_time(dt_during_wake, sleep_start, sleep_end)

@pytest.mark.parametrize("num_interventions,expected_shift,time_diff", [
    (0, 0.5, 5),  # No interventions -> 0.5h shift
    (1, 1.0, 5),  # One intervention -> 1.0h shift
    (2, 1.5, 5),  # Two interventions, >3h from target -> 1.5h shift
    (2, 1.0, 2),  # Two interventions, <3h from target -> 1.0h shift
    (3, 1.5, 5),  # Three interventions, >3h from target -> 1.5h shift
    (3, 1.0, 2),  # Three interventions, <3h from target -> 1.0h shift
])
def test_cbtmin_adjustment_rates(test_times, num_interventions, expected_shift, time_diff):
    """Test different CBTmin adjustment rates based on interventions and target proximity."""
    current_time = test_times['travel_stop'] + timedelta(days=1)
    target_time = current_time + timedelta(hours=time_diff)
    
    shift = calculate_next_cbtmin(
        current_time=current_time,
        target_time=target_time,
        num_interventions=num_interventions,
        delay=True,
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        pre_travel_days=3
    )
    assert shift == expected_shift

@pytest.mark.parametrize("t1,t2,expected_hour,expected_minute", [
    (time(0, 0), time(1, 0), 0, 30),      # Simple case
    (time(23, 0), time(1, 0), 0, 0),      # Across midnight
    (time(22, 0), time(2, 0), 0, 0),      # Symmetric around midnight
    (time(12, 0), time(14, 0), 13, 0),    # Simple afternoon case
    (time(23, 45), time(0, 15), 0, 0),    # 30-minute window across midnight
    (time(23, 0), time(23, 0), 23, 0),    # Same time
    (time(6, 30), time(7, 30), 7, 0),     # One-hour difference with minutes
    (time(23, 59), time(0, 1), 0, 0),     # Just around midnight
])
def test_midpoint_edge_cases(t1, t2, expected_hour, expected_minute):
    """Test edge cases for midpoint calculation."""
    result = midpoint_time(t1, t2)
    assert result.hour == expected_hour
    assert result.minute == expected_minute

@pytest.mark.parametrize("timezone_hours,time_str,expected_hour", [
    (5, "10:00", 5),     # Simple conversion to UTC
    (-5, "10:00", 15),   # Negative timezone
    (0, "10:00", 10),    # UTC
    (13, "10:00", 21),   # Extreme timezone
    (5, "00:00", 19)     # Midnight conversion
])
def test_timezone_conversions_comprehensive(timezone_hours, time_str, expected_hour):
    """Test comprehensive timezone conversion scenarios."""
    local_time = datetime.strptime(time_str, "%H:%M").time()
    local_time = local_time.replace(tzinfo=timezone(timedelta(hours=timezone_hours)))
    utc_time = astimezone_time(local_time, timezone.utc)
    
    assert utc_time.hour == expected_hour

@pytest.mark.parametrize("input_data", [
    {'num_interventions': -1},           # Invalid intervention count
    {'num_interventions': 4},            # Too many interventions
    {'pre_travel_days': -1},            # Invalid pre-travel days
    {'delay': None},                     # Invalid delay value
    {'current_time': None},              # Missing current time
    {'target_time': None},               # Missing target time
    {'travel_window': (None, None)},     # Invalid travel window
])
def test_cbtmin_invalid_inputs(test_times, input_data):
    """Test that calculate_next_cbtmin handles invalid inputs appropriately."""
    base_params = {
        'current_time': test_times['travel_stop'] + timedelta(days=1),
        'target_time': test_times['travel_stop'] + timedelta(days=1, hours=5),
        'num_interventions': 1,
        'delay': True,
        'travel_window': (test_times['travel_start'], test_times['travel_stop']),
        'pre_travel_days': 3
    }
    
    # Update base params with invalid input
    test_params = base_params.copy()
    test_params.update(input_data)
    
    # Should raise either TypeError for wrong types or ValueError for invalid values
    with pytest.raises((TypeError, ValueError)):
        calculate_next_cbtmin(**test_params)

def test_timeline_resolution_constraints(test_times, test_timezones):
    """Test timeline creation with different resolutions."""
    start_time = test_times['travel_start']
    end_time = start_time + timedelta(hours=1)
    base_params = {
        'start_time': start_time,
        'end_time': end_time,
        'CBTmin_times': [start_time],
        'melatonin_times': [start_time],
        'light_time_windows': [(start_time, end_time)],
        'dark_time_windows': [(start_time, end_time)],
        'exercise_time_windows': [(start_time, end_time)],
        'travel_window': (test_times['travel_start'], test_times['travel_stop']),
        'tz1': test_timezones['origin'],
        'tz2': test_timezones['destination'],
        'sleep_start_origin': test_times['sleep_start'],
        'sleep_end_origin': test_times['sleep_end'],
        'sleep_start_dest': test_times['sleep_start'],
        'sleep_end_dest': test_times['sleep_end']
    }
    
    # Test different resolutions
    resolutions = [1, 5, 15, 30, 60]
    for resolution in resolutions:
        timeline = create_timeline(resolution_minutes=resolution, **base_params)
        expected_entries = (end_time - start_time) / timedelta(minutes=resolution) + 1
        assert len(timeline) == int(expected_entries)

@pytest.mark.parametrize("scenario", [
    {
        'current': datetime(2025,6,1, tzinfo=timezone.utc),
        'target': datetime(2025,6,1,3, tzinfo=timezone.utc),
        'interventions': [(0,0.5), (1,1.0), (2,1.5)],  # (num_interventions, expected_shift)
        'delay': True,
        'description': "Standard forward adjustment"
    },
    {
        'current': datetime(2025,6,1, tzinfo=timezone.utc),
        'target': datetime(2025,6,1, tzinfo=timezone.utc),
        'interventions': [(0,0.0), (1,0.0), (2,0.0)],
        'delay': True,
        'description': "No adjustment needed (at target)"
    },
    {
        'current': datetime(2025,6,1,3, tzinfo=timezone.utc),
        'target': datetime(2025,6,1, tzinfo=timezone.utc),
        'interventions': [(0,-0.5), (1,-1.0), (2,-1.5)],
        'delay': False,
        'description': "Backward adjustment"
    },
    {
        'current': datetime(2025,6,1, tzinfo=timezone.utc),
        'target': datetime(2025,6,1,1, tzinfo=timezone.utc),
        'interventions': [(2,1.0), (3,1.0)],
        'delay': True,
        'description': "Near target (<3h) with multiple interventions"
    }
])
def test_cbtmin_adjustment_scenarios(scenario, test_times):
    """Test various CBTmin adjustment scenarios."""
    for num_interventions, expected_shift in scenario['interventions']:
        shift = calculate_next_cbtmin(
            current_time=scenario['current'],
            target_time=scenario['target'],
            num_interventions=num_interventions,
            delay=scenario['delay'],
            travel_window=(test_times['travel_start'], test_times['travel_stop']),
            pre_travel_days=3
        )
        assert shift == expected_shift, f"Failed for {scenario['description']} with {num_interventions} interventions"

@pytest.mark.parametrize("interventions,windows", [
    # Test combinations of interventions
    (
        {'melatonin': True, 'light': True, 'exercise': False},
        {'light_window': (1, 4), 'dark_window': (-2, 1), 'exercise_window': None}
    ),
    (
        {'melatonin': True, 'light': False, 'exercise': True},
        {'light_window': None, 'dark_window': None, 'exercise_window': (1, 4)}
    ),
    (
        {'melatonin': False, 'light': True, 'exercise': True},
        {'light_window': (1, 4), 'dark_window': (-2, 1), 'exercise_window': (1, 4)}
    )
])
def test_intervention_combinations(interventions, windows, test_times):
    """Test different combinations of interventions and their timing windows."""
    base_time = test_times['base_date']
    timeline = create_timeline(
        start_time=base_time,
        end_time=base_time + timedelta(hours=24),
        resolution_minutes=60,
        CBTmin_times=[base_time],
        melatonin_times=[base_time] if interventions['melatonin'] else [],
        light_time_windows=[(base_time + timedelta(hours=windows['light_window'][0]), 
                            base_time + timedelta(hours=windows['light_window'][1]))] if windows['light_window'] else [],
        dark_time_windows=[(base_time + timedelta(hours=windows['dark_window'][0]), 
                           base_time + timedelta(hours=windows['dark_window'][1]))] if windows['dark_window'] else [],
        exercise_time_windows=[(base_time + timedelta(hours=windows['exercise_window'][0]), 
                              base_time + timedelta(hours=windows['exercise_window'][1]))] if windows['exercise_window'] else [],
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        tz1=5,
        tz2=8,
        sleep_start_origin=test_times['sleep_start'],
        sleep_end_origin=test_times['sleep_end'],
        sleep_start_dest=test_times['sleep_start'],
        sleep_end_dest=test_times['sleep_end']
    )
    
    # Verify intervention states
    has_melatonin = any(event['is_melatonin'] for event in timeline)
    has_light = any(event['is_light_exposure'] for event in timeline)
    has_exercise = any(event['is_exercise'] for event in timeline)
    
    assert has_melatonin == interventions['melatonin']
    assert has_light == interventions['light']
    assert has_exercise == interventions['exercise']

def test_cbtmin_travel_periods(test_times):
    """Test CBTmin adjustments during different travel periods."""
    # During travel - should be 0
    during_travel = calculate_next_cbtmin(
        current_time=test_times['travel_start'],
        target_time=test_times['travel_start'],
        num_interventions=2,
        delay=True,
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        pre_travel_days=3
    )
    assert during_travel == 0

    # Way before travel (4 days) - should be 0
    before_travel = calculate_next_cbtmin(
        current_time=test_times['travel_start'] - timedelta(days=4),
        target_time=test_times['travel_stop'],
        num_interventions=2,
        delay=True,
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        pre_travel_days=3
    )
    assert before_travel == 0

    # Just before travel (2 days) - should allow adjustment
    just_before = calculate_next_cbtmin(
        current_time=test_times['travel_start'] - timedelta(days=2),
        target_time=test_times['travel_stop'],
        num_interventions=2,
        delay=True,
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        pre_travel_days=3
    )
    assert just_before == 1.5

# Utility function tests
@pytest.mark.parametrize("td,expected_hours", [
    (timedelta(hours=1), 1.0),
    (timedelta(hours=1, minutes=30), 1.5),
    (timedelta(days=1), 24.0),
    (timedelta(minutes=45), 0.75),
    (timedelta(0), 0.0),
    (timedelta(hours=-2), -2.0)
])
def test_hours_from_timedelta(td, expected_hours):
    """Test conversion of timedelta to hours."""
    from jetlag_core import hours_from_timedelta
    assert hours_from_timedelta(td) == expected_hours

@pytest.mark.parametrize("time_str,delta_hours,expected_hour", [
    ("10:00", 2, 12),    # Simple addition
    ("23:00", 2, 1),     # Cross midnight
    ("00:00", -1, 23),   # Backward cross midnight
    ("12:00", 0, 12),    # No change
    ("23:30", 0.5, 0)    # Half hour crossing midnight
])
def test_sum_time_timedelta_edge_cases(time_str, delta_hours, expected_hour):
    """Test edge cases of adding timedelta to time."""
    base_time = datetime.strptime(time_str, "%H:%M").time()
    result = sum_time_timedelta(base_time, timedelta(hours=delta_hours))
    assert result.hour == expected_hour

@pytest.mark.parametrize("current_time,travel_period,expected_result", [
    # Edge cases around travel period
    (datetime(2025,6,1, tzinfo=timezone.utc), 
     (datetime(2025,6,1, tzinfo=timezone.utc), datetime(2025,6,2, tzinfo=timezone.utc)),
     True),  # Exactly at start
    
    (datetime(2025,6,2, tzinfo=timezone.utc), 
     (datetime(2025,6,1, tzinfo=timezone.utc), datetime(2025,6,2, tzinfo=timezone.utc)),
     False),  # Exactly at end
    
    (datetime(2025,6,1,23,59,59, tzinfo=timezone.utc), 
     (datetime(2025,6,1, tzinfo=timezone.utc), datetime(2025,6,2, tzinfo=timezone.utc)),
     True),  # Just before midnight
    
    (datetime(2025,6,2,0,0,1, tzinfo=timezone.utc), 
     (datetime(2025,6,1, tzinfo=timezone.utc), datetime(2025,6,2, tzinfo=timezone.utc)),
     False),  # Just after midnight
])
def test_travel_period_boundaries(current_time, travel_period, expected_result):
    """Test edge cases for travel period detection."""
    result = current_time >= travel_period[0] and current_time < travel_period[1]
    assert result == expected_result


@pytest.mark.parametrize("test_params", [
    # Edge cases for timeline resolution
    (
        datetime(2025,6,1,0,0, tzinfo=timezone.utc),
        datetime(2025,6,1,1,0, tzinfo=timezone.utc),
        60, 2
    ),  # 1-hour span with 60-min resolution (2 points)
    
    (
        datetime(2025,6,1,0,0, tzinfo=timezone.utc),
        datetime(2025,6,1,0,1, tzinfo=timezone.utc),
        1, 2
    ),   # 1-minute span with 1-min resolution (2 points)
    
    (
        datetime(2025,6,1,0,0, tzinfo=timezone.utc),
        datetime(2025,6,1,0,0, tzinfo=timezone.utc),
        30, 1
    ),  # Same start/end time (1 point)
    
    (
        datetime(2025,6,1,0,0, tzinfo=timezone.utc),
        datetime(2025,6,1,1,59, tzinfo=timezone.utc),
        60, 2
    ),  # Non-exact division of timespan - 0:00 and 1:00 only
])
def test_timeline_resolution_edge_cases(test_params, test_times, test_timezones):
    """Test edge cases for timeline resolution and point generation."""
    start_time, end_time, resolution, expected_count = test_params
    timeline = create_timeline(
        start_time=start_time,
        end_time=end_time,
        resolution_minutes=resolution,
        CBTmin_times=[start_time],
        melatonin_times=[],
        light_time_windows=[],
        dark_time_windows=[],
        exercise_time_windows=[],
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        tz1=test_timezones['origin'],
        tz2=test_timezones['destination'],
        sleep_start_origin=test_times['sleep_start'],
        sleep_end_origin=test_times['sleep_end'],
        sleep_start_dest=test_times['sleep_start'],
        sleep_end_dest=test_times['sleep_end']
    )
    assert len(timeline) == expected_count

@pytest.mark.parametrize("time_pairs", [
    # Test combinations of sleep schedules
    [(time(22,0), time(6,0)), (time(23,0), time(7,0))],   # Different but not overlapping
    [(time(22,0), time(7,0)), (time(23,0), time(6,0))],   # Overlapping schedules
    [(time(0,0), time(8,0)), (time(23,0), time(7,0))],    # Midnight crossing in first schedule
    [(time(2,0), time(10,0)), (time(1,0), time(9,0))],    # Late night schedules
])
def test_sleep_schedule_interactions(time_pairs, test_times):
    """Test how different sleep schedules interact during timeline generation."""
    start_time = test_times['travel_start']
    end_time = start_time + timedelta(hours=24)
    
    timeline = create_timeline(
        start_time=start_time,
        end_time=end_time,
        resolution_minutes=60,
        CBTmin_times=[start_time],
        melatonin_times=[],
        light_time_windows=[],
        dark_time_windows=[],
        exercise_time_windows=[],
        travel_window=(start_time, end_time),
        tz1=5,
        tz2=8,
        sleep_start_origin=time_pairs[0][0],
        sleep_end_origin=time_pairs[0][1],
        sleep_start_dest=time_pairs[1][0],
        sleep_end_dest=time_pairs[1][1]
    )
    
    # Verify there's at least one point where sleep states differ
    sleep_differences = [
        event['is_sleep_origin'] != event['is_sleep_destination']
        for event in timeline
    ]
    assert any(sleep_differences), "Sleep schedules should have some differences"

@pytest.mark.parametrize("start,end", [
    (time(23, 30), time(7, 30)),    # Normal schedule
    (time(22, 0), time(6, 0)),      # Early schedule
    (time(1, 0), time(9, 0)),       # Late schedule
    (time(0, 0), time(8, 0)),       # Midnight start
    (time(23, 0), time(23, 0))      # Edge case: same time
])
def test_sleep_schedule_validation(start, end):
    """Test that sleep schedules are properly handled."""
    # Test midnight crossing
    dt_during = datetime(2025, 6, 1, hour=(start.hour+1)%24)
    dt_after = datetime(2025, 6, 1, hour=(end.hour+1)%24)
    
    if start != end:
        assert is_sleep_time(dt_during, start, end)
        assert not is_sleep_time(dt_after, start, end)
    else:
        # For same time, should always return False except at exactly that time
        assert not is_sleep_time(dt_during, start, end)

def test_timeline_event_format(test_times, test_timezones):
    """Test the format and validity of timeline events."""
    # Create a minimal timeline
    start_time = test_times['base_date']
    end_time = start_time + timedelta(hours=1)
    timeline = create_timeline(
        start_time=start_time,
        end_time=end_time,
        resolution_minutes=30,
        CBTmin_times=[start_time],
        melatonin_times=[start_time],
        light_time_windows=[(start_time, end_time)],
        dark_time_windows=[(start_time, end_time)],
        exercise_time_windows=[(start_time, end_time)],
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        tz1=test_timezones['origin'],
        tz2=test_timezones['destination'],
        sleep_start_origin=test_times['sleep_start'],
        sleep_end_origin=test_times['sleep_end'],
        sleep_start_dest=test_times['sleep_start'],
        sleep_end_dest=test_times['sleep_end']
    )
    
    # Check each event's format
    for event in timeline:
        # Type checks
        assert isinstance(event['timestamp'], datetime)
        assert isinstance(event['is_sleep_origin'], bool)
        assert isinstance(event['is_sleep_destination'], bool)
        assert isinstance(event['is_traveling'], bool)
        assert isinstance(event['is_cbtmin'], bool)
        assert isinstance(event['is_melatonin'], bool)
        assert isinstance(event['is_light_exposure'], bool)
        assert isinstance(event['is_dark_period'], bool)
        assert isinstance(event['is_exercise'], bool)
        assert isinstance(event['local_time_origin'], str)
        assert isinstance(event['local_time_destination'], str)
        
        # Format checks
        assert len(event['local_time_origin'].split(':')) == 2
        assert len(event['local_time_destination'].split(':')) == 2
        
        # Value checks
        assert event['timezone_origin'] == test_timezones['origin']
        assert event['timezone_destination'] == test_timezones['destination']

@pytest.mark.parametrize("window,is_valid", [
    ((datetime(2025,1,1), datetime(2025,1,2)), True),    # Valid window
    ((datetime(2025,1,2), datetime(2025,1,1)), False),   # End before start
    ((datetime(2025,1,1), datetime(2025,1,1)), True),    # Same time
    ((datetime(2025,1,1), "not a datetime"), False),     # Invalid type
    (("not a datetime", datetime(2025,1,1)), False),     # Invalid type
    ((datetime(2025,1,1),), False),                      # Too short
    ((1, 2), False)                                      # Wrong types
])
def test_time_window_validation(window, is_valid):
    """Test validation of time window tuples."""
    assert is_valid_time_window(window) == is_valid

def test_timeline_creation(test_times, test_timezones):
    """Test timeline creation and event tracking."""
    start_time = test_times['travel_start'] - timedelta(days=2)
    end_time = test_times['travel_stop'] + timedelta(days=2)
    
    # Create some test times
    cbt_times = [test_times['base_date'] + timedelta(hours=i*24) for i in range(3)]
    melatonin_times = [test_times['base_date'] + timedelta(hours=i*24 + 12) for i in range(3)]
    light_windows = [(t, t + timedelta(hours=3)) for t in cbt_times]
    dark_windows = [(t - timedelta(hours=3), t) for t in cbt_times]
    exercise_windows = light_windows
    
    timeline = create_timeline(
        start_time=start_time,
        end_time=end_time,
        resolution_minutes=30,
        CBTmin_times=cbt_times,
        melatonin_times=melatonin_times,
        light_time_windows=light_windows,
        dark_time_windows=dark_windows,
        exercise_time_windows=exercise_windows,
        travel_window=(test_times['travel_start'], test_times['travel_stop']),
        tz1=test_timezones['origin'],
        tz2=test_timezones['destination'],
        sleep_start_origin=test_times['sleep_start'],
        sleep_end_origin=test_times['sleep_end'],
        sleep_start_dest=test_times['sleep_start'],
        sleep_end_dest=test_times['sleep_end']
    )
    
    # Test timeline properties
    assert isinstance(timeline, list)
    assert len(timeline) > 0
    assert all(isinstance(event, dict) for event in timeline)
    
    # Test required keys in timeline events
    required_keys = {
        'timestamp', 'is_sleep_origin', 'is_sleep_destination',
        'is_traveling', 'is_cbtmin', 'is_melatonin', 'is_light_exposure',
        'is_dark_period', 'is_exercise'
    }
    assert all(required_keys.issubset(event.keys()) for event in timeline)

    # Test specific timeline event
    first_event = timeline[0]
    assert 'local_time_origin' in first_event
    assert 'local_time_destination' in first_event
