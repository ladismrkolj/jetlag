"""Estimating an initial phase from a schedule timeline."""

from __future__ import annotations

from datetime import datetime, timedelta

from circadian.angles import wrap24
from circadian.constants import CBTMIN_BEFORE_WAKE_HOURS
from circadian.schedule import ScheduleTimeline, local_time_at, segment_at
from circadian.types import PhaseHours


def estimate_initial_theta(timeline: ScheduleTimeline, at: datetime) -> PhaseHours:
    """Estimate the circadian phase at `at`, assuming the individual is entrained
    to whichever schedule segment was active just before `at`.

    Generalizes the existing app's heuristic (CBTmin ~= habitual wake time - 3h,
    `app/lib/jetlag.ts`) to an arbitrary timeline: it reads the wake time off the
    segment that is ACTUALLY active at `at`, not a hardcoded "origin" schedule, so
    it works the same way whether `at` is the start of a single trip, the first
    day of a multi-leg itinerary, or the first day of a night-shift-prep plan.

    Returns 0.0 (i.e. "assume starting exactly at CBTmin") if there is no active
    segment or the active segment is free-running (no imposed sleep window) --
    this is a documented, arbitrary fallback, not a computed estimate, since there
    is nothing to anchor an estimate to in that case. Callers who already know the
    individual's actual phase should pass it directly rather than relying on this.
    """
    seg = segment_at(timeline, at)
    if seg is None or seg.sleep_window_local is None:
        return 0.0

    _, sleep_end = seg.sleep_window_local
    local_now = local_time_at(timeline, at)
    cbtmin_clock_time = (
        datetime.combine(local_now.date(), sleep_end, tzinfo=local_now.tzinfo)
        - timedelta(hours=CBTMIN_BEFORE_WAKE_HOURS)
    )
    # Hours elapsed since the most recent occurrence of that local clock time.
    # Using `local_now.date()` above (rather than hunting for "the right" nearby
    # date) is deliberate: whichever calendar date is picked, the raw difference
    # is within +-24h of correct, and wrap24() folds it to the right answer either
    # way, since phase only cares about position in the cycle, not which specific
    # day the last occurrence fell on.
    hours_since = (local_now - cbtmin_clock_time).total_seconds() / 3600.0
    return wrap24(hours_since)
