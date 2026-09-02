"""Circular (mod-24-hour) arithmetic helpers shared across the whole package."""

from __future__ import annotations


def wrap24(value: float) -> float:
    """Wrap an hour value into [0, 24)."""
    return value % 24.0


def circular_diff(a: float, b: float, period: float = 24.0) -> float:
    """Shortest signed difference `a - b` on a circle of the given period.

    Result is wrapped to `(-period/2, period/2]` -- e.g. for the default 24h period,
    `circular_diff(1, 23) == 2` (1 o'clock is 2 hours *after* 23:00, going forward
    through midnight, which is the shorter way round than going 22 hours backward).
    The exact antipodal case (difference of exactly half the period) is reported as
    `+period/2` rather than `-period/2` -- an arbitrary but fixed tie-break, since the
    two are the same point on the circle.
    """
    half = period / 2.0
    diff = (a - b + half) % period - half
    if diff == -half:
        diff = half
    return diff
