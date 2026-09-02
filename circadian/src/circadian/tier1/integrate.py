"""Tier 1 numeric integration: the everyday RK4 path (see tier1/analytic.py for
the closed-form fast path used when every enabled stimulus reduces to discrete
pulses).
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from circadian.angles import wrap24
from circadian.integrators import integrate_fixed_step
from circadian.stimuli.base import StimulusRegistry
from circadian.stimuli.registry import combined_forcing
from circadian.tier1.oscillator import make_derivative, omega_from_tau
from circadian.types import IndividualParams, SimulationResult, SimulationWindow, ThetaSample


def simulate_rk4(
    window: SimulationWindow,
    initial_theta: float,
    individual: IndividualParams,
    registry: StimulusRegistry,
) -> SimulationResult:
    """Integrate dtheta/dt = omega + sum_i Z_i(theta)*p_i(t) with fixed-step RK4
    over `window`, starting from `initial_theta` (need not be pre-wrapped) at
    `window.start`.
    """
    derivative = make_derivative(individual, registry, window.start)
    duration_hours = (window.end - window.start).total_seconds() / 3600.0
    raw_samples = integrate_fixed_step(
        np.array([initial_theta]), 0.0, duration_hours, window.step_hours, derivative
    )

    samples: list[ThetaSample] = []
    for t_hours, state in raw_samples:
        t = window.start + timedelta(hours=t_hours)
        theta = wrap24(float(state[0]))
        forcing = combined_forcing(registry, theta, t)
        samples.append(ThetaSample(t=t, theta=theta, forcing=forcing))

    final_unwrapped = float(raw_samples[-1][1][0])
    free_running_drift = omega_from_tau(individual.tau_hours) * duration_hours
    net_shift_hours = (final_unwrapped - initial_theta) - free_running_drift

    return SimulationResult(
        samples=samples,
        final_theta=wrap24(final_unwrapped),
        net_shift_hours=net_shift_hours,
        method="rk4",
    )
