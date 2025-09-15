from __future__ import annotations

from datetime import datetime, timedelta, time, date, timezone
from typing import Dict, List, Tuple, Any

# Legacy composition helpers removed in favor of a single high-level timetable builder.


__all__ = [
    "create_jet_lag_timetable",
]


# --- High-level timetable builder (UTC JSON) -------------------------------

def create_jet_lag_timetable(
    *,
    origin_timezone,
    destination_timezone,
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
) -> List[Dict[str, Any]]:
    """Build a UTC JSON timetable from simple inputs.

    Rules implemented (summary):
    - CBTmin = 3h before wake time.
    - Day 0 = date (in destination tz) of travel_end; no shift applied on Day 0.
    - Post‑arrival daily shift magnitude:
        any method -> 1.5h if diff>3h else 1h; no method -> 1h if diff>3h else 0.5h.
    - Preconditioning days (in origin tz): shift by 1h if any method else 0h per day.
    - No shifts during travel interval.
    - Interventions emitted around CBTmin; intervention windows overlapping travel are skipped.
    - Sleep windows and travel interval included as events; all timestamps in UTC.
    """

    # ---- Small utilities ----
    def _to_utc_iso(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _to_utc(dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    def _combine_local(d: date, t: time, tz) -> datetime:
        # Combine local date+time with tz, then return aware datetime
        return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, t.microsecond, tz)

    def _midnight_utc_for_local_date(d: date, tz) -> datetime:
        return _combine_local(d, time(0, 0), tz).astimezone(timezone.utc)

    def _sleep_window_utc_for_local_date(d: date, sleep_start: time, sleep_end: time, tz) -> Tuple[datetime, datetime]:
        start_local = _combine_local(d, sleep_start, tz)
        # If end time is earlier or equal, assume it crosses midnight to next day
        end_local = _combine_local(d, sleep_end, tz)
        if end_local <= start_local:
            end_local = end_local + timedelta(days=1)
        return _to_utc(start_local), _to_utc(end_local)

    def _cbt_hour_utc_from_sleep_end(sleep_end_local: time, tz, ref_date: date) -> float:
        wake_local = _combine_local(ref_date, sleep_end_local, tz)
        cbt_local = wake_local - timedelta(hours=3)
        cbt_utc = _to_utc(cbt_local)
        return cbt_utc.hour + cbt_utc.minute / 60 + cbt_utc.second / 3600

    def _wrap_hour(h: float) -> float:
        return (h % 24 + 24) % 24

    def _signed_delta_hours(curr: float, target: float) -> float:
        # Smallest signed delta from curr to target in hours, range (-12, 12]
        delta = (target - curr + 12) % 24 - 12
        if delta == -12:
            return 12
        return delta

    def _move_toward(curr: float, target: float, step: float) -> float:
        delta = _signed_delta_hours(curr, target)
        if abs(delta) <= step:
            return _wrap_hour(target)
        direction = 1 if delta > 0 else -1
        return _wrap_hour(curr + direction * step)

    def _intervals_overlap(a: Tuple[datetime, datetime], b: Tuple[datetime, datetime]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    # ---- Normalize and baseline values ----
    if travel_end.tzinfo is None or travel_start.tzinfo is None:
        raise ValueError("travel_start and travel_end must be timezone-aware")
    if travel_end <= travel_start:
        raise ValueError("travel_end must be after travel_start")

    travel_start_utc = _to_utc(travel_start)
    travel_end_utc = _to_utc(travel_end)

    # Day 0 is destination local date of travel_end
    day0_dest_local_date = travel_end.astimezone(destination_timezone).date()

    # Compute baseline CBTmin hour (UTC) at origin and target at destination
    origin_ref_date = travel_start.astimezone(origin_timezone).date()
    dest_ref_date = travel_end.astimezone(destination_timezone).date()
    origin_cbt_hour = _cbt_hour_utc_from_sleep_end(origin_sleep_end, origin_timezone, origin_ref_date)
    dest_cbt_hour = _cbt_hour_utc_from_sleep_end(destination_sleep_end, destination_timezone, dest_ref_date)

    initial_diff = abs(_signed_delta_hours(origin_cbt_hour, dest_cbt_hour))
    any_method = bool(use_melatonin or use_exercise or use_light_dark)

    # Determine preconditioning step (per day, hours)
    pre_step = 1.0 if any_method else 0.0

    # Determine post‑arrival step magnitude based on difference and methods
    if any_method:
        post_step = 1.5 if initial_diff > 3.0 else 1.0
    else:
        post_step = 1.0 if initial_diff > 3.0 else 0.5

    # ---- Build daily CBTmin series (pre, day0, post) ----
    cbt_entries: List[Tuple[int, datetime]] = []  # (day_index, cbtmin_utc)

    # Preconditioning days in origin timezone: indices -precondition_days..-1
    current_hour = origin_cbt_hour
    origin_local_departure_date = origin_ref_date  # local date on departure
    for i in range(precondition_days, 0, -1):
        d_local = origin_local_departure_date - timedelta(days=i)
        day_start_utc = _midnight_utc_for_local_date(d_local, origin_timezone)
        # move toward destination by pre_step (cap at target)
        current_hour = _move_toward(current_hour, dest_cbt_hour, pre_step)
        cbt_dt = day_start_utc + timedelta(hours=current_hour)
        cbt_entries.append((-i, cbt_dt))

    # Day 0 at destination local date of travel_end; no shift during travel
    day0_start_utc = _midnight_utc_for_local_date(day0_dest_local_date, destination_timezone)
    # If no preconditioning days, current_hour is still origin baseline
    cbt_day0_dt = day0_start_utc + timedelta(hours=current_hour)
    cbt_entries.append((0, cbt_day0_dt))

    # Post‑arrival days: apply fixed post_step until target reached
    remaining = abs(_signed_delta_hours(current_hour, dest_cbt_hour))
    day_idx = 1
    while remaining > 1e-6:  # until aligned
        day_start_utc = _midnight_utc_for_local_date(day0_dest_local_date + timedelta(days=day_idx), destination_timezone)
        current_hour = _move_toward(current_hour, dest_cbt_hour, post_step)
        cbt_dt = day_start_utc + timedelta(hours=current_hour)
        cbt_entries.append((day_idx, cbt_dt))
        remaining = abs(_signed_delta_hours(current_hour, dest_cbt_hour))
        day_idx += 1

    # ---- Build interventions around CBTmin (direct, no helper) ----
    cbtmins_only = [dt for _, dt in cbt_entries]

    travel_interval = (travel_start_utc, travel_end_utc)

    def _point_in_interval(pt: datetime, interval: Tuple[datetime, datetime]) -> bool:
        return interval[0] <= pt < interval[1]

    intervention_events: List[Dict[str, Any]] = []

    for cbt in cbtmins_only:
        if use_melatonin:
            # Single time dose: midpoint of a typical [-2h, -1h] window -> -1.5h
            m_time = cbt - timedelta(hours=1.5)
            if not _point_in_interval(m_time, travel_interval):
                intervention_events.append({
                    "event": "melatonin",
                    "start": _to_utc_iso(m_time),
                    "end": None,
                    "is_cbtmin": False,
                    "is_melatonin": True,
                    "is_light": False,
                    "is_dark": False,
                    "is_exercise": False,
                    "is_sleep": False,
                    "is_travel": False,
                    "day_index": None,
                })

        if use_light_dark:
            # Light: [ +1h, +2h ]; Dark: [ -1h, +1h ]
            l_start, l_end = cbt + timedelta(hours=1), cbt + timedelta(hours=2)
            d_start, d_end = cbt - timedelta(hours=1), cbt + timedelta(hours=1)
            if not _intervals_overlap((l_start, l_end), travel_interval):
                intervention_events.append({
                    "event": "light",
                    "start": _to_utc_iso(l_start),
                    "end": _to_utc_iso(l_end),
                    "is_cbtmin": False,
                    "is_melatonin": False,
                    "is_light": True,
                    "is_dark": False,
                    "is_exercise": False,
                    "is_sleep": False,
                    "is_travel": False,
                    "day_index": None,
                })
            if not _intervals_overlap((d_start, d_end), travel_interval):
                intervention_events.append({
                    "event": "dark",
                    "start": _to_utc_iso(d_start),
                    "end": _to_utc_iso(d_end),
                    "is_cbtmin": False,
                    "is_melatonin": False,
                    "is_light": False,
                    "is_dark": True,
                    "is_exercise": False,
                    "is_sleep": False,
                    "is_travel": False,
                    "day_index": None,
                })

        if use_exercise:
            # Exercise: simple placeholder [ +10h, +11h ] from CBTmin
            e_start, e_end = cbt + timedelta(hours=10), cbt + timedelta(hours=11)
            if not _intervals_overlap((e_start, e_end), travel_interval):
                intervention_events.append({
                    "event": "exercise",
                    "start": _to_utc_iso(e_start),
                    "end": _to_utc_iso(e_end),
                    "is_cbtmin": False,
                    "is_melatonin": False,
                    "is_light": False,
                    "is_dark": False,
                    "is_exercise": True,
                    "is_sleep": False,
                    "is_travel": False,
                    "day_index": None,
                })

    # ---- Sleep windows ----
    sleep_windows: List[Tuple[datetime, datetime, int]] = []  # include day index for tagging

    # Preconditioning sleep windows in origin tz
    for i in range(precondition_days, 0, -1):
        d_local = origin_local_departure_date - timedelta(days=i)
        s, e = _sleep_window_utc_for_local_date(d_local, origin_sleep_start, origin_sleep_end, origin_timezone)
        sleep_windows.append((-i, s, e))

    # Day 0 and onward sleep windows in destination tz
    for idx in range(0, day_idx):  # includes day 0..last post day
        d_local = day0_dest_local_date + timedelta(days=idx)
        s, e = _sleep_window_utc_for_local_date(d_local, destination_sleep_start, destination_sleep_end, destination_timezone)
        sleep_windows.append((idx, s, e))

    # ---- Assemble timeline events ----
    events: List[Dict[str, Any]] = []

    # Add CBTmin points
    for di, dt in cbt_entries:
        events.append({
            "event": "cbtmin",
            "start": _to_utc_iso(dt),
            "end": None,
            "is_cbtmin": True,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": False,
            "is_travel": False,
            "day_index": di,
        })

    # Add interventions (already UTC ISO strings)
    events.extend(intervention_events)

    # Add sleep windows
    for di, s, e in sleep_windows:
        events.append({
            "event": "sleep",
            "start": _to_utc_iso(s),
            "end": _to_utc_iso(e),
            "is_cbtmin": False,
            "is_melatonin": False,
            "is_light": False,
            "is_dark": False,
            "is_exercise": False,
            "is_sleep": True,
            "is_travel": False,
            "day_index": di,
        })

    # Add travel pause
    events.append({
        "event": "travel",
        "start": _to_utc_iso(travel_start_utc),
        "end": _to_utc_iso(travel_end_utc),
        "is_cbtmin": False,
        "is_melatonin": False,
        "is_light": False,
        "is_dark": False,
        "is_exercise": False,
        "is_sleep": False,
        "is_travel": True,
        "day_index": 0,
    })

    # Sort events by start time
    events.sort(key=lambda e: e["start"])
    return events
