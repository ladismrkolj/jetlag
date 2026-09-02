"""Tier 1's defining equation:

    dtheta/dt = omega + sum_i Z_i(theta) * p_i(t)

`omega = 24 / tau_hours` is the intrinsic angular rate; the sum is computed by
`stimuli.registry.combined_forcing()` over whatever modules are registered. This
module only ever calls that one registry function -- it has no knowledge of how
many stimulus modules exist or what they are, which is what makes "add an
influence = add a module" true. See docs/circadian-model.md for the full
derivation (phase reduction of weakly coupled oscillators) and its limits.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import numpy as np

from circadian.angles import wrap24
from circadian.stimuli.base import StimulusRegistry
from circadian.stimuli.registry import combined_forcing
from circadian.types import IndividualParams, PhaseHours


def omega_from_tau(tau_hours: float) -> float:
    """Intrinsic angular rate (hours-of-phase per hour-of-real-time) such that a
    free-running clock with period `tau_hours` completes one full phase cycle
    every `tau_hours` of real time."""
    return 24.0 / tau_hours


def dtheta_dt(
    theta: PhaseHours,
    t: datetime,
    individual: IndividualParams,
    registry: StimulusRegistry,
) -> float:
    """The right-hand side of the Tier-1 ODE at a given phase and real time.

    `theta` is wrapped to [0, 24) before being handed to stimulus modules --
    they define Z_i as a periodic function over that domain and must not see a
    raw, unwrapped, ever-growing phase value.
    """
    omega = omega_from_tau(individual.tau_hours)
    forcing = individual.prc_amplitude_scale * combined_forcing(registry, wrap24(theta), t)
    return omega + forcing


def make_derivative(
    individual: IndividualParams,
    registry: StimulusRegistry,
    t0: datetime,
) -> Callable[[np.ndarray, float], np.ndarray]:
    """Build a `(state, t_hours) -> d(state)/d(t_hours)` function suitable for
    `circadian.integrators.rk4_step`/`integrate_fixed_step`, where
    `state = [theta]` and `t_hours` is hours elapsed since `t0`.

    `theta` is deliberately NOT wrapped in the returned state -- RK4 needs a
    smooth, unwrapped trajectory to integrate correctly across cycle boundaries;
    callers wrap individual samples only when reporting or using an
    instantaneous phase value (see tier1/integrate.py).
    """

    def derivative(state: np.ndarray, t_hours: float) -> np.ndarray:
        theta = float(state[0])
        t = t0 + timedelta(hours=t_hours)
        return np.array([dtheta_dt(theta, t, individual, registry)])

    return derivative
