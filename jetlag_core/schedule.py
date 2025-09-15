from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Sequence, Tuple

# --- Data structures -------------------------------------------------------

@dataclass(frozen=True)
class TimelineEvent:
    """Simple representation of a scheduled event."""

    event: str
    start: datetime
    end: datetime | None = None


# --- Core calculations -----------------------------------------------------

def calculate_next_cbtmin(current: datetime, target: datetime, max_shift: timedelta) -> datetime:
    """Shift the current CBTmin toward the target by at most ``max_shift``."""
    if current.tzinfo != target.tzinfo:
        raise ValueError("current and target must share tzinfo")

    delta = target - current
    step = min(max_shift, abs(delta))
    direction = 1 if delta.total_seconds() > 0 else -1
    return current + direction * step


def calculate_cbtmin_times(
    start: datetime,
    target: datetime,
    end: datetime,
    max_shift: timedelta,
) -> List[datetime]:
    """Return successive CBTmin times from ``start`` until ``end``."""
    times = [start]
    current = start
    while current < end:
        next_cbt = calculate_next_cbtmin(current, target, max_shift)
        if next_cbt == current:
            break
        times.append(next_cbt)
        current = next_cbt
    return times


def calculate_intervention_times(
    cbtmins: Sequence[datetime],
) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """Return intervention windows keyed by intervention type."""
    windows: Dict[str, List[Tuple[datetime, datetime]]] = {
        "melatonin": [],
        "light": [],
        "dark": [],
    }
    for cbt in cbtmins:
        windows["melatonin"].append((cbt - timedelta(hours=2), cbt - timedelta(hours=1)))
        windows["light"].append((cbt + timedelta(hours=1), cbt + timedelta(hours=2)))
        windows["dark"].append((cbt - timedelta(hours=1), cbt + timedelta(hours=1)))
    return windows


def create_timeline(
    cbtmins: Sequence[datetime],
    interventions: Dict[str, List[Tuple[datetime, datetime]]],
) -> List[TimelineEvent]:
    """Combine CBTmin and interventions into a single, sorted timeline."""
    events: List[TimelineEvent] = []
    for cbt in cbtmins:
        events.append(TimelineEvent("cbtmin", cbt))
    for name, slots in interventions.items():
        for start, end in slots:
            events.append(TimelineEvent(name, start, end))
    events.sort(key=lambda e: e.start)
    return events


def create_jet_lag_schedule(
    start: datetime,
    end: datetime,
    initial_cbtmin: datetime,
    target_cbtmin: datetime,
    max_shift_hours: float = 1.0,
) -> List[TimelineEvent]:
    """High level helper producing a full jet‑lag schedule."""
    max_shift = timedelta(hours=max_shift_hours)
    cbtmins = calculate_cbtmin_times(initial_cbtmin, target_cbtmin, end, max_shift)
    interventions = calculate_intervention_times(cbtmins)
    return create_timeline(cbtmins, interventions)


__all__ = [
    "TimelineEvent",
    "calculate_next_cbtmin",
    "calculate_cbtmin_times",
    "calculate_intervention_times",
    "create_timeline",
    "create_jet_lag_schedule",
]
