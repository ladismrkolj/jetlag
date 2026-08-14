"""circadian: a base oscillator plus additive, pluggable stimulus modules.

The core idea: dtheta/dt = omega + sum_i Z_i(theta) * p_i(t). See
docs/circadian-model.md for the full model. The public API is re-exported here as it
is built up; see individual submodules for full docstrings.
"""

from circadian.angles import circular_diff, wrap24
from circadian.constants import DEFAULT_STEP_HOURS, DEFAULT_TAU_HOURS
from circadian.types import IndividualParams, SimulationResult, SimulationWindow, ThetaSample

__all__ = [
    "circular_diff",
    "wrap24",
    "DEFAULT_STEP_HOURS",
    "DEFAULT_TAU_HOURS",
    "IndividualParams",
    "SimulationResult",
    "SimulationWindow",
    "ThetaSample",
]
