"""Shared value types for the circadian engine.

Conventions (see docs/circadian-model.md for the full rationale):
  * Phase (theta) is wrapped to [0, 24) hours, with theta=0 anchored to an
    individual's estimated CBTmin (core body temperature minimum) -- the same
    reference point the existing app's heuristic model uses.
  * A positive stimulus sensitivity Z_i(theta) combined with a positive drive
    p_i(t) means a phase ADVANCE (dtheta/dt increases -- the clock runs "ahead").
  * All wall-clock-facing values use timezone-aware `datetime.datetime` objects,
    never a cached numeric UTC offset (see schedule.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PhaseHours = float
"""Circadian phase in hours, conventionally wrapped to [0, 24). 0 == estimated CBTmin."""


@dataclass
class IndividualParams:
    """Per-individual calibration knobs. Defaults are literature population averages."""

    tau_hours: float = 24.2
    """Intrinsic free-running period. Population average per Czeisler et al. 1999."""

    prc_amplitude_scale: float = 1.0
    """Multiplies every registered stimulus's sensitivity(). 1.0 == literature-average
    responsiveness; use to represent e.g. reduced light sensitivity in older adults."""

    chronotype_offset_hours: float = 0.0
    """Added when estimating initial theta from a sleep schedule, to represent an
    individual's habitual offset from the population-average CBTmin-to-wake-time gap."""


@dataclass
class SimulationWindow:
    """The real time span to simulate over, and the integration step size."""

    start: datetime
    end: datetime
    step_hours: float = 0.1

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("SimulationWindow.start/end must be timezone-aware datetimes")
        if self.end <= self.start:
            raise ValueError("SimulationWindow.end must be after start")
        if self.step_hours <= 0:
            raise ValueError("step_hours must be positive")


@dataclass
class ThetaSample:
    """One point on a simulated phase trajectory."""

    t: datetime
    theta: PhaseHours
    forcing: float
    """Instantaneous Sum_i Z_i(theta) * p_i(t) at this sample, EXCLUDING the omega
    baseline -- i.e. how much the stimuli are pushing, not the free-running drift."""


@dataclass
class SimulationResult:
    """Output of a Tier-1 simulation run."""

    samples: list[ThetaSample]
    final_theta: PhaseHours
    net_shift_hours: float
    """Signed, UNWRAPPED cumulative shift relative to free-running drift over the
    simulated window (does not reset when theta wraps through 0/24)."""
    method: str
    """'rk4' or 'analytic' -- which integration path produced this result."""
