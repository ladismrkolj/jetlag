import numpy as np
import pytest

from circadian.integrators import integrate_fixed_step, rk4_step


class TestRK4StepExactness:
    def test_constant_derivative_is_exact_regardless_of_step_size(self) -> None:
        """RK4 integrates polynomials up to degree 4 exactly per step; a constant
        derivative (degree 0) must be reproduced exactly for ANY step size."""

        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return np.array([3.0])

        state = np.array([1.0])
        for dt in (0.01, 0.1, 1.0, 5.0):
            result = rk4_step(state, 0.0, dt, derivative)
            assert result[0] == pytest.approx(1.0 + 3.0 * dt, rel=1e-12)

    def test_linear_in_t_derivative_is_exact(self) -> None:
        # dy/dt = t  =>  y(t) = y0 + t^2/2; RK4 is exact for this per step.
        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return np.array([t])

        state = np.array([0.0])
        result = rk4_step(state, 0.0, 2.0, derivative)
        assert result[0] == pytest.approx(2.0, rel=1e-12)  # 2^2/2 = 2


class TestRK4Convergence:
    def test_fourth_order_convergence_on_harmonic_oscillator(self) -> None:
        """dy/dt = [y2, -y1] (simple harmonic oscillator; y1(t) = cos(t) exactly).
        Halving the step size should shrink the error by roughly 2^4 = 16x --
        confirms this is genuinely 4th-order accurate, not silently lower-order."""

        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return np.array([state[1], -state[0]])

        t_end = 10.0
        y0 = np.array([1.0, 0.0])

        def error_for_step(dt: float) -> float:
            samples = integrate_fixed_step(y0, 0.0, t_end, dt, derivative)
            t_final, state_final = samples[-1]
            exact = np.cos(t_final)
            return abs(state_final[0] - exact)

        err_coarse = error_for_step(0.1)
        err_fine = error_for_step(0.05)
        assert err_coarse > 0  # sanity: not accidentally exact
        ratio = err_coarse / err_fine
        assert 12.0 < ratio < 20.0  # ~16x, with tolerance for discretization noise


class TestIntegrateFixedStep:
    def test_samples_start_and_end_inclusive(self) -> None:
        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return np.array([1.0])

        samples = integrate_fixed_step(np.array([0.0]), 0.0, 1.0, 0.3, derivative)
        assert samples[0][0] == pytest.approx(0.0)
        assert samples[-1][0] == pytest.approx(1.0)

    def test_final_step_is_shortened_to_land_exactly_on_t1(self) -> None:
        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return np.array([2.0])

        samples = integrate_fixed_step(np.array([0.0]), 0.0, 1.0, 0.3, derivative)
        # steps: 0 -> 0.3 -> 0.6 -> 0.9 -> 1.0 (last step shortened to 0.1)
        times = [t for t, _ in samples]
        assert times[-1] == pytest.approx(1.0)
        assert len(times) == 5

    def test_rejects_non_positive_step(self) -> None:
        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return state

        with pytest.raises(ValueError):
            integrate_fixed_step(np.array([0.0]), 0.0, 1.0, 0.0, derivative)

    def test_rejects_end_before_start(self) -> None:
        def derivative(state: np.ndarray, t: float) -> np.ndarray:
            return state

        with pytest.raises(ValueError):
            integrate_fixed_step(np.array([0.0]), 1.0, 0.0, 0.1, derivative)
