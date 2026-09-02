"""circadian: a base oscillator plus additive, pluggable stimulus modules.

The core idea: dtheta/dt = omega + sum_i Z_i(theta) * p_i(t). See
docs/circadian-model.md for the full model and docs/whitepaper.md for the
literature the parameters come from. The public API is re-exported here as it is
built up; see individual submodules for full docstrings.
"""

from circadian.angles import circular_diff, wrap24
from circadian.constants import DEFAULT_STEP_HOURS, DEFAULT_TAU_HOURS
from circadian.estimate import estimate_initial_theta
from circadian.schedule import (
    ScheduleSegment,
    ScheduleTimeline,
    is_sleep_at,
    local_time_at,
    segment_at,
    sleep_window_at,
    tz_at,
)
from circadian.stimuli.base import (
    ActiveStimulus,
    Citation,
    PulseEvent,
    StimulusMetadata,
    StimulusModule,
    StimulusRegistry,
)
from circadian.stimuli.registry import combined_forcing, validate_registry
from circadian.tier1.integrate import simulate_rk4
from circadian.tier1.oscillator import dtheta_dt, omega_from_tau
from circadian.types import IndividualParams, SimulationResult, SimulationWindow, ThetaSample

__all__ = [
    # math
    "circular_diff",
    "wrap24",
    # constants
    "DEFAULT_STEP_HOURS",
    "DEFAULT_TAU_HOURS",
    # schedule timeline
    "ScheduleSegment",
    "ScheduleTimeline",
    "is_sleep_at",
    "local_time_at",
    "segment_at",
    "sleep_window_at",
    "tz_at",
    "estimate_initial_theta",
    # stimulus plugin contract
    "ActiveStimulus",
    "Citation",
    "PulseEvent",
    "StimulusMetadata",
    "StimulusModule",
    "StimulusRegistry",
    "combined_forcing",
    "validate_registry",
    # tier 1
    "dtheta_dt",
    "omega_from_tau",
    "simulate_rk4",
    # value types
    "IndividualParams",
    "SimulationResult",
    "SimulationWindow",
    "ThetaSample",
]
