"""Generic fixed-step 4th-order Runge-Kutta integrator, shared by Tier 1 and Tier 2.

Kept deliberately small and dependency-light (plain numpy arrays, no solver
framework) so it is easy to read and verify by hand -- Tier 1's oscillator uses this
directly; Tier 2's richer nonlinear model uses `scipy.integrate.solve_ivp` instead
(see model_b/simulate.py) because adaptive step control matters more once the system
is genuinely stiff-ish, and scipy is an unremarkable dependency for that tier.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

DerivativeFn = Callable[[np.ndarray, float], np.ndarray]
"""d(state)/dt at (state, t). Time unit is whatever the caller uses (hours, here)."""


def rk4_step(state: np.ndarray, t: float, dt_hours: float, derivative: DerivativeFn) -> np.ndarray:
    """Advance `state` by one fixed step of `dt_hours` using classic RK4."""
    k1 = derivative(state, t)
    k2 = derivative(state + k1 * (dt_hours / 2.0), t + dt_hours / 2.0)
    k3 = derivative(state + k2 * (dt_hours / 2.0), t + dt_hours / 2.0)
    k4 = derivative(state + k3 * dt_hours, t + dt_hours)
    return state + (k1 + 2.0 * k2 + 2.0 * k3 + k4) * (dt_hours / 6.0)


def integrate_fixed_step(
    state0: np.ndarray,
    t0: float,
    t1: float,
    dt_hours: float,
    derivative: DerivativeFn,
) -> list[tuple[float, np.ndarray]]:
    """Integrate from `t0` to `t1` with fixed-step RK4.

    Returns `(t, state)` samples inclusive of both endpoints. The final step is
    shortened so the last sample lands exactly on `t1` rather than overshooting.
    """
    if dt_hours <= 0:
        raise ValueError("dt_hours must be positive")
    if t1 < t0:
        raise ValueError("t1 must be >= t0")

    samples: list[tuple[float, np.ndarray]] = [(t0, state0)]
    t = t0
    state = state0
    while t < t1:
        step = min(dt_hours, t1 - t)
        state = rk4_step(state, t, step, derivative)
        t += step
        samples.append((t, state))
    return samples
