"""The multi-segment schedule timeline.

This is the general primitive behind every scenario the engine models: a single
jet-lag trip (2 segments), a multi-leg trip (N segments, each with its own
timezone), or a non-travel habit change like preparing a worker for a night shift
(N segments, same timezone, a progressively-shifted sleep window) are all just
different `ScheduleTimeline`s. There is no privileged "origin"/"destination" concept
anywhere in this module.

All wall-clock reasoning goes through `zoneinfo.ZoneInfo` and timezone-aware
`datetime` objects rather than a cached numeric UTC offset, so multi-day
simulations that cross a daylight-saving transition resolve the correct local time
automatically -- see docs/circadian-model.md, 'Time handling'.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ScheduleSegment:
    """One stretch of imposed schedule, in effect from `start` until the next
    segment's `start` (or the end of the simulation, for the last segment)."""

    start: datetime
    sleep_window_local: tuple[time, time] | None = None
    """(sleep_start, sleep_end) in LOCAL clock time for this segment's timezone.
    None means free-running / no imposed sleep-wake schedule."""
    tz: str | None = None
    """IANA timezone name in effect from `start` onward. None means "unchanged
    from the previous segment" -- e.g. a same-timezone habit change like
    night-shift prep, where only the sleep window moves, not the timezone."""
    label: str = ""

    def __post_init__(self) -> None:
        if self.start.tzinfo is None:
            raise ValueError("ScheduleSegment.start must be timezone-aware")
        if self.tz is not None:
            # Validate eagerly -- a typo'd zone name should fail at construction,
            # not silently later inside a stimulus module's drive() call.
            ZoneInfo(self.tz)


ScheduleTimeline = list[ScheduleSegment]
"""Sorted or not -- every function here sorts defensively by `start`."""


def _sorted(timeline: ScheduleTimeline) -> list[ScheduleSegment]:
    return sorted(timeline, key=lambda seg: seg.start)


def segment_at(timeline: ScheduleTimeline, t: datetime) -> ScheduleSegment | None:
    """The segment in effect at `t`: the latest segment whose start is <= t.
    None if `t` is before the first segment (or the timeline is empty)."""
    active: ScheduleSegment | None = None
    for seg in _sorted(timeline):
        if seg.start <= t:
            active = seg
        else:
            break
    return active


def tz_at(timeline: ScheduleTimeline, t: datetime) -> str | None:
    """The IANA zone in effect at `t`, resolving `tz=None` segments back to the
    most recent segment that actually specified one. None if no segment up to
    `t` has ever specified a timezone."""
    resolved: str | None = None
    for seg in _sorted(timeline):
        if seg.start > t:
            break
        if seg.tz is not None:
            resolved = seg.tz
    return resolved


def sleep_window_at(timeline: ScheduleTimeline, t: datetime) -> tuple[time, time] | None:
    """The imposed local sleep window in effect at `t`, or None if free-running."""
    seg = segment_at(timeline, t)
    return seg.sleep_window_local if seg is not None else None


def local_time_at(timeline: ScheduleTimeline, t: datetime) -> datetime:
    """`t`, converted to whatever timezone is in effect at `t` per the timeline.

    Uses `astimezone`, which resolves the correct UTC offset for that specific
    instant via the IANA database -- a daylight-saving transition partway through
    a segment is handled automatically, with no per-day offset bookkeeping needed.
    If no segment has specified a timezone by `t`, `t` is returned unchanged (its
    own tzinfo is treated as "local").
    """
    tz = tz_at(timeline, t)
    if tz is None:
        return t
    return t.astimezone(ZoneInfo(tz))


def is_in_local_window(local_dt: datetime, window: tuple[time, time]) -> bool:
    """Whether `local_dt`'s time-of-day falls in `window`, correctly handling
    windows that cross midnight (e.g. sleep 23:00-07:00)."""
    start, end = window
    tod = local_dt.time()
    if start <= end:
        return start <= tod < end
    return tod >= start or tod < end


def is_sleep_at(timeline: ScheduleTimeline, t: datetime) -> bool:
    """Whether `t` falls inside the imposed sleep window of the segment active
    at `t`. Always False if that segment is free-running (no sleep window)."""
    window = sleep_window_at(timeline, t)
    if window is None:
        return False
    return is_in_local_window(local_time_at(timeline, t), window)
