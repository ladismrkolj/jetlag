from __future__ import annotations

from datetime import datetime, timedelta, time, date, timezone
from typing import Dict, List, Tuple, Any

# Legacy composition helpers removed in favor of a single high-level timetable builder.


__all__ = [
    "create_jet_lag_timetable",
    "rasterize_timetable",
]

def sum_time_timedelta(t: time, td: timedelta) -> time:
    """Add a timedelta to a time."""
    ref_date = date(2000, 1, 1)
    dt = datetime.combine(ref_date, t)
    result_dt = dt + td
    return result_dt.time()

def astimezone_time(t: time, tz: timezone) -> time:
    """Convert a time to a different timezone."""
    if t.tzinfo is None:
        raise ValueError("Input time should be naive (without timezone)")
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

def is_in_time_interval(dt: datetime, sleep_start: time, sleep_end: time) -> bool:
    """Determine if it's sleep time at the given datetime using local sleep schedule."""
    time_of_day = dt.time()
    if sleep_start <= sleep_end:
        return sleep_start <= time_of_day < sleep_end
    else:  # Sleep schedule crosses midnight
        return time_of_day >= sleep_start or time_of_day < sleep_end

def is_inside_interval(ts: datetime, interval: tuple[datetime, datetime]) -> bool:
    """
    Check if a datetime is inside a given interval.
    """
    start, end = interval
    return start <= ts < end


def intersection_hours(interval1: tuple[datetime, datetime], interval2: tuple[datetime, datetime]) -> float:
    """
    Return the overlap in hours between two datetime intervals.
    If there is no intersection, returns 0.0.
    """
    start1, end1 = interval1
    start2, end2 = interval2

    # Find latest start and earliest end
    latest_start = max(start1, start2)
    earliest_end = min(end1, end2)

    if latest_start >= earliest_end:
        return 0.0  # no overlap

    overlap_seconds = (earliest_end - latest_start).total_seconds()
    return overlap_seconds / 3600.0

def midnight_for_datetime(d: datetime) -> datetime:
    return datetime.combine(d.date(), time(0, 0))

def to_iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")

def next_interval(time: datetime, interval:Tuple[time, time], filter_window:Tuple[datetime, datetime]=None) -> Tuple[datetime, datetime]:
    """Find the next occurrence of a daily time interval after a given datetime.
    If filter_window is provided, ensure the interval does not overlap it. if the end time is before start time, it is assumed to cross midnight.
    Returns (start_datetime, end_datetime) of the next interval. If filter_window is provided, 
    will return None, None if intersects.
    """
    start_time, end_time = interval
    ref_date = time.date()
    start_dt = datetime.combine(ref_date, start_time)
    end_dt = datetime.combine(ref_date, end_time)
    
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)  # crosses midnight

    if start_dt <= time:
        # Move to next day
        if end_dt > time:
            start_dt = time
        else:
            start_dt += timedelta(days=1)
            end_dt += timedelta(days=1)

    # TODO comment
    if filter_window is not None and intersection_hours((start_dt, end_dt), filter_window) > 0:
        return None, None

    return start_dt, end_dt

class CBTmin:
    
    PRESETS: Dict[str, Dict[str, float|tuple]] = {
    "default": {
        "melatonin_advance": -11.5,
        "melatonin_delay": 4,
        "exercise_advance": (0., 3.),
        "exercise_delay": (-3., 0.),
        "light_advance": (0., 3.),
        "light_delay": (-3., 0.),
        "dark_advance": (-3., 0.),
        "dark_delay": (0., 3.),
        },
    }
    
    def __init__(self, origin_cbtmin: time, dest_cbtmin: time, shift_preset = "default"):
        self.origin_cbtmin = origin_cbtmin # of course in UTC
        self.dest_cbtmin = dest_cbtmin # of course in UTC
        self.presets = self.PRESETS.get(shift_preset)
        self.cbtmin = self.origin_cbtmin
        self.phase_direction = "delay" if self.signed_difference() > 0 else ("advance" if self.signed_difference() < 0 else "aligned")
        
    def signed_difference(self):
        diff = hours_from_timedelta(subtract_times(self.dest_cbtmin, self.cbtmin))
        norm = ((diff + 12) % 24) - 12
        # Handle edge case: -12 → +12
        if norm == -12:
            norm = 12
        return norm
        
    def delta_cbtmin(self, melatonin, exercise, light_dark, precondition):
        if melatonin or exercise or light_dark:
            if abs(self.signed_difference()) > 3.0:
                return 1.5 if not precondition else 1.0
            else:
                return 1.5 if not precondition else 1.0
        else:
            if abs(self.signed_difference()) > 3.0:
                return 1.0 if not precondition else 0.0
            else:
                return 1.0 if not precondition else 0.0
    
    @classmethod
    def from_sleep(cls, origin_sleep_start, origin_sleep_end, dest_sleep_start, dest_sleep_end, shift_preset = "default"):
        """_summary_
        ALL IN UTC
        Args:
            origin_sleep_start (_type_): _description_
            origin_sleep_end (_type_): _description_
            dest_sleep_start (_type_): _description_
            dest_sleep_end (_type_): _description_
            shift_preset (str, optional): _description_. Defaults to "default".

        Returns:
            _type_: _description_
        """
        origin_cbtmin = sum_time_timedelta(origin_sleep_end, timedelta(hours=-3))
        dest_cbtmin = sum_time_timedelta(dest_sleep_end, timedelta(hours=-3))
        return cls(origin_cbtmin, dest_cbtmin, shift_preset)
    
    def optimal_melatonin_time(self):
        if self.phase_direction == 'advance':
            return timedelta(hours=self.presets["melatonin_advance"])
        else:
            return timedelta(hours=self.presets["melatonin_delay"])
    
    def optimal_exercise_window(self):
        if self.phase_direction == 'advance':
            start = timedelta(hours=self.presets["exercise_advance"][0])
            end = timedelta(hours=self.presets["exercise_advance"][1])
        else:
            start = timedelta(hours=self.presets["exercise_delay"][0])
            end = timedelta(hours=self.presets["exercise_delay"][1])
        return (start, end)
    
    def optimal_light_window(self):
        if self.phase_direction == 'advance':
            start = timedelta(hours=self.presets["light_advance"][0])
            end = timedelta(hours=self.presets["light_advance"][1])
        else:
            start = timedelta(hours=self.presets["light_delay"][0])
            end = timedelta(hours=self.presets["light_delay"][1])
        return (start, end)
    
    def optimal_dark_window(self):
        if self.phase_direction == 'advance':
            start = timedelta(hours=self.presets["dark_advance"][0])
            end = timedelta(hours=self.presets["dark_advance"][1])
        else:
            start = timedelta(hours=self.presets["dark_delay"][0])
            end = timedelta(hours=self.presets["dark_delay"][1])
        return (start, end)
    
    def next_cbtmin(self, time: datetime, no_intervention_window: Tuple[datetime, datetime] = None, melatonin = True, exercise = True, light = True, dark = True, precondition = True, skip_shift = False):
        """Calculate next CBTmin time after given datetime, applying shift if outside no_intervention_window.
        Assume that interventions of last cbtmin could be applied.
        return what interventions could be applied at this cbtmin.
        """
        
        next_cbtmin = datetime.combine(time.date(), self.cbtmin)
        if next_cbtmin <= time:
            next_cbtmin += timedelta(days=1)
        last_cbtmin = next_cbtmin - timedelta(days=1)
        
        optimal_melatonin = last_cbtmin + self.optimal_melatonin_time() + (timedelta(days=1) if self.phase_direction == "advance" else timedelta(0))
        optimal_exercise = (last_cbtmin + self.optimal_exercise_window()[0], last_cbtmin + self.optimal_exercise_window()[1])
        optimal_light = (last_cbtmin + self.optimal_light_window()[0], last_cbtmin + self.optimal_light_window()[1])
        optimal_dark = (last_cbtmin + self.optimal_dark_window()[0], last_cbtmin + self.optimal_dark_window()[1])
        
        window = no_intervention_window
        if window is not None and is_inside_interval(optimal_melatonin, window):
            used_melatonin = False
        else:
            used_melatonin = melatonin
        
        if window is not None and intersection_hours(optimal_exercise, window) > 0:
            used_exercise = False
        else:
            used_exercise = exercise
            
        if window is not None and intersection_hours(optimal_light, window) > 0:
            used_light = False
        else:
            used_light = light
            
        if window is not None and intersection_hours(optimal_dark, window) > 0:
            used_dark = False
        else:
            used_dark = dark
        
        if abs(self.signed_difference()) < 3.0:
            used_light = False
            used_dark = False
            used_melatonin = False
            used_exercise = False
        
        cbtmin_delta = max(self.delta_cbtmin(used_melatonin, used_exercise, used_light or used_dark, precondition), 0)
        
        if cbtmin_delta > abs(self.signed_difference()):
            cbtmin_delta = abs(self.signed_difference())
            
        if window is not None and intersection_hours((next_cbtmin-timedelta(hours=8), next_cbtmin), window) > 0:
            cbtmin_delta = 0
        
        # If no shift needed or already aligned, just return next_cbtmin
        if cbtmin_delta == 0 or self.phase_direction == "aligned" or skip_shift:
            return next_cbtmin, ((False, optimal_melatonin), (False, optimal_exercise), (False, optimal_light), (False, optimal_dark))
            

        direction_sign = 1 if self.phase_direction == "delay" else -1
        self.cbtmin = sum_time_timedelta(self.cbtmin, timedelta(hours=cbtmin_delta*direction_sign))
        next_cbtmin += timedelta(hours=cbtmin_delta*direction_sign)
        
        interventions = (
            (used_melatonin, optimal_melatonin),
            (used_exercise, optimal_exercise),
            (used_light, optimal_light),
            (used_dark, optimal_dark),
        )
        
        return next_cbtmin, interventions
        
        
# --- High-level timetable builder (UTC JSON) -------------------------------

def create_jet_lag_timetable(
    *,
    origin_timezone: float,
    destination_timezone: float,
    origin_sleep_start: time,
    origin_sleep_end: time,
    destination_sleep_start: time,
    destination_sleep_end: time,
    travel_start: datetime,
    travel_end: datetime,
    use_melatonin: bool,
    use_exercise: bool,
    use_light_dark: bool,
    precondition_days: int = 0,
    shift_on_travel_days: bool = False,
) -> List[Dict[str, Any]]:
    """Build a UTC JSON timetable from simple inputs.

    Rules implemented (summary):
    - CBTmin = 3h before wake time.
    - Day 0 = date (in destination tz) of travel_end; no shift applied on Day 0.
    - Post-arrival daily shift magnitude:
        any method -> 1.5h if diff>3h else 1h; no method -> 1h if diff>3h else 0.5h.
    - Preconditioning days (in origin tz): shift by 1h if any method else 0h per day.
    - No shifts during travel interval.
    - Interventions emitted around CBTmin; intervention windows overlapping travel are skipped.
    - Sleep windows and travel interval included as events; all timestamps in UTC.
    """

    origin_sleep_start_utc = sum_time_timedelta(origin_sleep_start, timedelta(hours=-origin_timezone))
    origin_sleep_end_utc = sum_time_timedelta(origin_sleep_end, timedelta(hours=-origin_timezone))
    destination_sleep_start_utc = sum_time_timedelta(destination_sleep_start, timedelta(hours=-destination_timezone))
    destination_sleep_end_utc = sum_time_timedelta(destination_sleep_end, timedelta(hours=-destination_timezone))

    travel_start_utc = travel_start - timedelta(hours=origin_timezone)
    travel_end_utc = travel_end - timedelta(hours=destination_timezone)

    # Day 0 is destination local date of travel_end
    #day0_dest_local_date = travel_end.astimezone(destination_timezone).date()

    # Compute baseline CBTmin hour (UTC) at origin and target at destination
    #origin_ref_date = travel_start.astimezone(origin_timezone).date()
    #dest_ref_date = travel_end.astimezone(destination_timezone).date()
    #origin_cbt_hour = _cbt_hour_utc_from_sleep_end(origin_sleep_end, origin_timezone)
    #dest_cbt_hour = _cbt_hour_utc_from_sleep_end(destination_sleep_end, destination_timezone)

    #signed_initial_diff = _signed_delta_hours(origin_cbt_hour, dest_cbt_hour)
    #initial_diff = abs(signed_initial_diff)
    #phase_direction = "delay" if signed_initial_diff > 0 else ("advance" if signed_initial_diff < 0 else "aligned")
    #direction_sign = 1 if signed_initial_diff > 0 else (-1 if signed_initial_diff < 0 else 0)
    #any_method = bool(use_melatonin or use_exercise or use_light_dark)

    # Everything works around the end of travel. This is the fixed point everything is relative to.

    if shift_on_travel_days:
        start_of_shift = midnight_for_datetime(travel_start_utc) - timedelta(days=precondition_days)
    elif precondition_days > 0:
        start_of_shift = midnight_for_datetime(travel_start_utc) - timedelta(days=precondition_days)
    else:
        start_of_shift = travel_end_utc
        
    CBTobj = CBTmin.from_sleep(origin_sleep_start_utc, origin_sleep_end_utc, destination_sleep_start_utc, destination_sleep_end_utc, shift_preset="default")
    
    num_extra_before_days = 1
    num_extra_after_days = 2
    
    midnight_start_of_calculations = midnight_for_datetime(travel_start_utc - timedelta(days=precondition_days+num_extra_before_days))
    
    cbt_entries: List[Tuple[datetime, Tuple[Tuple]]] = []
    
    first_cbtmin, _ = CBTobj.next_cbtmin(midnight_start_of_calculations, no_intervention_window=(travel_start_utc, travel_end_utc), melatonin=use_melatonin, exercise=use_exercise, light=use_light_dark, dark=use_light_dark, precondition=False, skip_shift=True)
    cbt_entries.append((first_cbtmin, ((False, first_cbtmin), (False, first_cbtmin), (False, first_cbtmin), (False, first_cbtmin))))
    
    time = first_cbtmin
    i_ext = 0
    while (abs(CBTobj.signed_difference()) > 1e-6) or i_ext < num_extra_after_days:
        if abs(CBTobj.signed_difference()) < 1e-6:
            i_ext += 1
        if precondition_days > 0 and time > start_of_shift and time < travel_start_utc:
            is_precondition = True 
        else:
            is_precondition = False
        
        no_intervention_window = (travel_start_utc, travel_end_utc) if not shift_on_travel_days else None 
        
        next_cbtmin, used_interventions = CBTobj.next_cbtmin(time, no_intervention_window=no_intervention_window, melatonin=use_melatonin, exercise=use_exercise, light=use_light_dark, dark=use_light_dark, precondition=is_precondition, skip_shift=(time < start_of_shift))
        cbt_entries.append((next_cbtmin, used_interventions))
        time = next_cbtmin
        
    midnight_end_of_calculations = midnight_for_datetime(cbt_entries[-1][0] + timedelta(days=1))

    intervention_events: List[Dict[str, Any]] = []

    for i in range(len(cbt_entries)):
        intervention_events.append({
                    "event": "cbtmin",
                    "start": to_iso(cbt_entries[i][0]),
                    "end": None,
                    "is_cbtmin": True,
                    "is_melatonin": False,
                    "is_light": False,
                    "is_dark": False,
                    "is_exercise": False,
                    "is_sleep": False,
                    "is_travel": False,
                    "day_index": None,
                    "phase_direction": CBTobj.phase_direction,
                    "signed_initial_diff_hours": CBTobj.signed_difference(),
                })
        
        # melatonin
        if cbt_entries[i][1][0][0]:
            intervention_events.append({
                        "event": "melatonin",
                        "start": to_iso(cbt_entries[i][1][0][1]),
                        "end": None,
                        "is_cbtmin": False,
                        "is_melatonin": True,
                        "is_light": False,
                        "is_dark": False,
                        "is_exercise": False,
                        "is_sleep": False,
                        "is_travel": False,
                        "day_index": None,
                        "phase_direction": CBTobj.phase_direction,
                        "signed_initial_diff_hours": CBTobj.signed_difference(),
                    })
            
        # exercise
        if cbt_entries[i][1][1][0]:
            intervention_events.append({
                        "event": "exercise",
                        "start": to_iso(cbt_entries[i][1][1][1][0]),
                        "end": to_iso(cbt_entries[i][1][1][1][1]),
                        "is_cbtmin": False,
                        "is_melatonin": False,
                        "is_light": False,
                        "is_dark": False,
                        "is_exercise": True,
                        "is_sleep": False,
                        "is_travel": False,
                        "day_index": None,
                        "phase_direction": CBTobj.phase_direction,
                        "signed_initial_diff_hours": CBTobj.signed_difference(),
                    })
        
        # light
        if cbt_entries[i][1][2][0]:
            intervention_events.append({
                        "event": "light",
                        "start": to_iso(cbt_entries[i][1][2][1][0]),
                        "end": to_iso(cbt_entries[i][1][2][1][1]),
                        "is_cbtmin": False,
                        "is_melatonin": False,
                        "is_light": True,
                        "is_dark": False,
                        "is_exercise": False,
                        "is_sleep": False,
                        "is_travel": False,
                        "day_index": None,
                        "phase_direction": CBTobj.phase_direction,
                        "signed_initial_diff_hours": CBTobj.signed_difference(),
                    })
            
        # dark
        if cbt_entries[i][1][3][0]:
            intervention_events.append({
                        "event": "dark",
                        "start": to_iso(cbt_entries[i][1][3][1][0]),
                        "end": to_iso(cbt_entries[i][1][3][1][1]),
                        "is_cbtmin": False,
                        "is_melatonin": False,
                        "is_light": False,
                        "is_dark": True,
                        "is_exercise": False,
                        "is_sleep": False,
                        "is_travel": False,
                        "day_index": None,
                        "phase_direction": CBTobj.phase_direction,
                        "signed_initial_diff_hours": CBTobj.signed_difference(),
                    })
            

    # ---- Sleep windows ----
    sleep_windows: List[Tuple[datetime, datetime]] = []  # include day index for tagging
    
    time = midnight_start_of_calculations
    sleep_dest = False
    while time < midnight_end_of_calculations:
        if sleep_dest is False:
            s, e = next_interval(time, (origin_sleep_start_utc, origin_sleep_end_utc), filter_window=(travel_start_utc, travel_end_utc))
            if s is None or e is None:
                time += timedelta(days=1)
                continue
        if e > travel_start_utc or sleep_dest:
            s, e = next_interval(time, (destination_sleep_start_utc, destination_sleep_end_utc), filter_window=(travel_start_utc, travel_end_utc))
            sleep_dest = True
            if s is None or e is None:
                time += timedelta(days=1)
                continue
        sleep_windows.append((s, e))
        time = e
        

    # ---- Assemble timeline events ----
    events: List[Dict[str, Any]] = []

    # Add sleep windows
    for s, e in sleep_windows:
        events.append({
            "event": "sleep",
            "start": to_iso(s),
            "end": to_iso(e),
            "is_cbtmin": False,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": True,
            "is_travel": False,
            "day_index": None,
            "phase_direction": CBTobj.phase_direction,
            "signed_initial_diff_hours": CBTobj.signed_difference(),
        })

    # Add travel pause
    events.append({
        "event": "travel",
        "start": to_iso(travel_start_utc),
        "end": to_iso(travel_end_utc),
        "is_cbtmin": False,
        "is_melatonin": False,
        "is_light": False,
        "is_dark": False,
        "is_exercise": False,
        "is_sleep": False,
        "is_travel": True,
        "day_index": None,
        "phase_direction": CBTobj.phase_direction,
        "signed_initial_diff_hours": CBTobj.signed_difference(),
    })
    
    # Add interventions (already UTC ISO strings)
    events.extend(intervention_events)

    # Sort events by start time
    events.sort(key=lambda e: e["start"])
    return events


# --- Visualization helper: rasterize timetable into fixed slots ------------

def rasterize_timetable(
    events: List[Dict[str, Any]],
    start_utc: datetime,
    end_utc: datetime,
    step: timedelta | None = None,
    *,
    step_minutes: int | float | None = None,
) -> List[Dict[str, Any]]:
    """Convert event-based timetable into fixed UTC time slots.

    Each returned slot covers [start, end) and lists which event names occur
    in that slot. Point events (end=None) count if their timestamp falls in
    the slot. Interval events count if they overlap the slot.

    Parameters
    - events: List of dicts from create_jet_lag_timetable.
    - start, end: Aware datetimes; converted to UTC. If end <= start, returns [].
    - step: Slot width as timedelta. If not provided, use step_minutes or 1 hour.
    - step_minutes: Alternative to step; ignored if step is provided.
    """

    if end_utc <= start_utc:
        return []

    def _parse_utc_iso(s: str | None) -> datetime | None:
        if s is None:
            return None
        # Accept 'Z' suffix
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)

    slot_step = step if step is not None else timedelta(minutes=float(step_minutes) if step_minutes is not None else 60)
    if slot_step.total_seconds() <= 0:
        raise ValueError("step must be positive")

    # Pre-parse event times to UTC datetimes
    parsed_events = []
    for e in events:
        s = _parse_utc_iso(e.get("start")) if isinstance(e.get("start"), str) else None
        en = _parse_utc_iso(e.get("end")) if isinstance(e.get("end"), str) else None
        parsed_events.append((e, s, en))

    slots: List[Dict[str, Any]] = []
    cur = start_utc
    while cur < end_utc:
        nxt = min(cur + slot_step, end_utc)
        names: List[str] = []
        flags = {
            "is_cbtmin": False,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": False,
            "is_travel": False,
        }

        for e, es, ee in parsed_events:
            name = e.get("event")
            if es is None:
                continue
            occurs = False
            if ee is None:
                # point event
                occurs = (es >= cur and es < nxt)
            else:
                # interval event overlaps slot
                occurs = (es < nxt and ee > cur)
            if occurs:
                if isinstance(name, str):
                    names.append(name)
                for k in flags.keys():
                    if e.get(k):
                        flags[k] = True

        slot = {
            "start": start_utc.isoformat().replace("+00:00", "Z") if cur == start_utc else cur.isoformat().replace("+00:00", "Z"),
            "end": nxt.isoformat().replace("+00:00", "Z"),
            "events": sorted(set(names)),
        }
        slot.update(flags)
        slots.append(slot)
        cur = nxt

    return slots
