"""The stimulus registry: the sum in dtheta/dt = omega + sum_i Z_i(theta)*p_i(t).

Deliberately tiny -- its entire job is to let a new influence be added to the
engine without touching tier1/oscillator.py, tier1/integrate.py, or
tier1/analytic.py. `default_registry()` (assembling the concrete built-in modules)
is added incrementally as those modules land, in stimuli/light.py etc.
"""

from __future__ import annotations

from datetime import datetime

from circadian.stimuli.base import StimulusRegistry
from circadian.types import PhaseHours


def combined_forcing(registry: StimulusRegistry, theta: PhaseHours, t: datetime) -> float:
    """Sum_i Z_i(theta) * p_i(t) over every ENABLED module in the registry."""
    total = 0.0
    for active in registry:
        if not active.enabled:
            continue
        total += active.module.sensitivity(theta) * active.module.drive(t, active.params)
    return total


def validate_registry(registry: StimulusRegistry) -> None:
    """Hygiene check: every module must have a unique id, and must carry
    citations unless it's explicitly 'low' confidence (where the whole point is
    that solid evidence doesn't exist yet). Raises ValueError on violation.

    Not called automatically by the simulation entry points -- intended for
    tests, and for callers assembling a custom registry who want early feedback.
    """
    seen_ids: set[str] = set()
    for active in registry:
        meta = active.module.meta
        if meta.id in seen_ids:
            raise ValueError(f"duplicate stimulus module id: {meta.id!r}")
        seen_ids.add(meta.id)
        if not meta.citations and meta.confidence != "low":
            raise ValueError(
                f"stimulus module {meta.id!r} has confidence={meta.confidence!r} "
                "but no citations"
            )
