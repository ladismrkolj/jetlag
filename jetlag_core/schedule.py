from __future__ import annotations

from datetime import datetime, timedelta, time, date, timezone
from typing import Dict, List, Tuple, Any

# Legacy composition helpers removed in favor of a single high-level timetable builder.


__all__ = [
    "create_jet_lag_timetable",
    "rasterize_timetable",
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

    def _move_toward(curr: float, target: float, step: float, direction_sign: int) -> float:
        """Move CBTmin hour toward target by ``step`` in a fixed direction.

        direction_sign: +1 for delay (later), -1 for advance (earlier), 0 to hold.
        Caps movement when remaining distance is <= step.
        """
        remaining = abs(_signed_delta_hours(curr, target))
        if remaining <= step:
            return _wrap_hour(target)
        if direction_sign == 0:
            return _wrap_hour(curr)
        return _wrap_hour(curr + direction_sign * step)

    def _intervals_overlap(a: Tuple[datetime, datetime], b: Tuple[datetime, datetime]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    # ---- Normalize and baseline values ----
    if travel_end.tzinfo is None or travel_start.tzinfo is None:
        raise ValueError("travel_start and travel_end must be timezone-aware")
    # Normalize travel interval; allow zero-length and reversed inputs
    if travel_end < travel_start:
        travel_start, travel_end = travel_end, travel_start

    travel_start_utc = _to_utc(travel_start)
    travel_end_utc = _to_utc(travel_end)

    # Day 0 is destination local date of travel_end
    day0_dest_local_date = travel_end.astimezone(destination_timezone).date()

    # Compute baseline CBTmin hour (UTC) at origin and target at destination
    origin_ref_date = travel_start.astimezone(origin_timezone).date()
    dest_ref_date = travel_end.astimezone(destination_timezone).date()
    origin_cbt_hour = _cbt_hour_utc_from_sleep_end(origin_sleep_end, origin_timezone, origin_ref_date)
    dest_cbt_hour = _cbt_hour_utc_from_sleep_end(destination_sleep_end, destination_timezone, dest_ref_date)

    signed_initial_diff = _signed_delta_hours(origin_cbt_hour, dest_cbt_hour)
    initial_diff = abs(signed_initial_diff)
    phase_direction = "delay" if signed_initial_diff > 0 else ("advance" if signed_initial_diff < 0 else "aligned")
    direction_sign = 1 if signed_initial_diff > 0 else (-1 if signed_initial_diff < 0 else 0)
    any_method = bool(use_melatonin or use_exercise or use_light_dark)

    # Determine preconditioning step (per day, hours)
    pre_step = 1.0 if any_method else 0.0

    # Post‑arrival step is chosen dynamically each day based on current remaining diff.

    # ---- Build daily CBTmin series (pre, day0, post) ----
    cbt_entries: List[Tuple[int, datetime]] = []  # (day_index, cbtmin_utc)

    current_hour = origin_cbt_hour
    origin_local_departure_date = origin_ref_date  # local date on departure

    do_shift = initial_diff >= 3.0

    # Preconditioning days in origin timezone: indices -precondition_days..-1
    if do_shift:
        for i in range(precondition_days, 0, -1):
            d_local = origin_local_departure_date - timedelta(days=i)
            day_start_utc = _midnight_utc_for_local_date(d_local, origin_timezone)
            remaining_now = abs(_signed_delta_hours(current_hour, dest_cbt_hour))
            if pre_step > 0 and direction_sign != 0 and remaining_now > 0:
                current_hour = _move_toward(current_hour, dest_cbt_hour, pre_step, direction_sign)
            cbt_dt = day_start_utc + timedelta(hours=current_hour)
            cbt_entries.append((-i, cbt_dt))

    # Day 0 at destination local date of travel_end; no shift during travel
    day0_start_utc = _midnight_utc_for_local_date(day0_dest_local_date, destination_timezone)
    # If no preconditioning days, current_hour is still origin baseline
    cbt_day0_dt = day0_start_utc + timedelta(hours=current_hour)
    cbt_entries.append((0, cbt_day0_dt))

    # Post‑arrival days: apply dynamic step until aligned, only if shifting is needed
    remaining = abs(_signed_delta_hours(current_hour, dest_cbt_hour))
    day_idx = 1
    if do_shift and direction_sign != 0:
        while remaining > 1e-6:  # until aligned
            day_start_utc = _midnight_utc_for_local_date(day0_dest_local_date + timedelta(days=day_idx), destination_timezone)
            # choose dynamic step based on current remaining difference
            if any_method:
                step_today = 1.5 if remaining > 3.0 else 1.0
            else:
                step_today = 1.0 if remaining > 3.0 else 0.5
            current_hour = _move_toward(current_hour, dest_cbt_hour, step_today, direction_sign)
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
                    "phase_direction": phase_direction,
                    "signed_initial_diff_hours": signed_initial_diff,
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
                    "phase_direction": phase_direction,
                    "signed_initial_diff_hours": signed_initial_diff,
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
                    "phase_direction": phase_direction,
                    "signed_initial_diff_hours": signed_initial_diff,
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
                    "phase_direction": phase_direction,
                    "signed_initial_diff_hours": signed_initial_diff,
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
            "phase_direction": phase_direction,
            "signed_initial_diff_hours": signed_initial_diff,
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
            "phase_direction": phase_direction,
            "signed_initial_diff_hours": signed_initial_diff,
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
        "phase_direction": phase_direction,
        "signed_initial_diff_hours": signed_initial_diff,
    })

    # Sort events by start time
    events.sort(key=lambda e: e["start"])
    return events


# --- Visualization helper: rasterize timetable into fixed slots ------------

def rasterize_timetable(
    events: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
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

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware datetimes")
    if end <= start:
        return []

    def _to_utc(dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    def _parse_utc_iso(s: str | None) -> datetime | None:
        if s is None:
            return None
        # Accept 'Z' suffix
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)

    start_utc = _to_utc(start)
    end_utc = _to_utc(end)

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
            "start": start_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if cur == start_utc else cur.isoformat().replace("+00:00", "Z"),
            "end": nxt.isoformat().replace("+00:00", "Z"),
            "events": sorted(set(names)),
        }
        slot.update(flags)
        slots.append(slot)
        cur = nxt

    return slots
