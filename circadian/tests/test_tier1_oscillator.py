from datetime import UTC, datetime, time, timedelta

import pytest

from circadian.estimate import estimate_initial_theta
from circadian.schedule import ScheduleSegment
from circadian.tier1.integrate import simulate_rk4
from circadian.tier1.oscillator import dtheta_dt, omega_from_tau
from circadian.types import IndividualParams, SimulationWindow


class TestOmegaFromTau:
    def test_exactly_24h_period_runs_at_unit_rate(self) -> None:
        assert omega_from_tau(24.0) == pytest.approx(1.0)

    def test_longer_period_runs_slow(self) -> None:
        assert omega_from_tau(24.2) < 1.0

    def test_shorter_period_runs_fast(self) -> None:
        assert omega_from_tau(23.8) > 1.0


class TestDthetaDtWithEmptyRegistry:
    def test_equals_omega(self) -> None:
        individual = IndividualParams(tau_hours=24.2)
        rate = dtheta_dt(5.0, datetime(2026, 1, 1, tzinfo=UTC), individual, [])
        assert rate == pytest.approx(omega_from_tau(24.2))


class TestFreeRunningPeriod:
    """The headline Tier-1 sanity check: with no stimuli at all, the oscillator
    must free-run at exactly its intrinsic period, drifting away from local clock
    time at (24/tau - 1) hours per 24h. For tau=24.2 that is ~-11.9 min/day --
    i.e. a person in temporal isolation drifts LATER each day, which is the
    classic free-running result."""

    @pytest.mark.parametrize("tau_hours", [23.8, 24.0, 24.2, 24.5])
    @pytest.mark.parametrize("days", [1, 7, 30])
    def test_drift_matches_analytic_prediction(self, tau_hours: float, days: int) -> None:
        start = datetime(2026, 3, 1, tzinfo=UTC)
        window = SimulationWindow(start=start, end=start + timedelta(days=days), step_hours=0.1)
        individual = IndividualParams(tau_hours=tau_hours)

        result = simulate_rk4(window, initial_theta=0.0, individual=individual, registry=[])

        elapsed_hours = 24.0 * days
        expected_drift = (24.0 / tau_hours - 1.0) * elapsed_hours
        # theta advanced by omega*elapsed; drift is that minus the elapsed wall time
        actual_drift = (
            omega_from_tau(tau_hours) * elapsed_hours - elapsed_hours
        )
        assert actual_drift == pytest.approx(expected_drift, abs=1e-9)

        # And the integrator must reproduce it: final theta (unwrapped by
        # reconstructing from the known cycle count) tracks omega*elapsed.
        expected_theta_unwrapped = omega_from_tau(tau_hours) * elapsed_hours
        assert result.final_theta == pytest.approx(expected_theta_unwrapped % 24.0, abs=1e-6)

    def test_net_shift_is_zero_without_stimuli(self) -> None:
        """net_shift_hours is defined relative to free-running drift, so with an
        empty registry it must be exactly zero regardless of tau."""
        start = datetime(2026, 3, 1, tzinfo=UTC)
        window = SimulationWindow(start=start, end=start + timedelta(days=10))
        for tau in (23.5, 24.0, 24.2, 24.9):
            result = simulate_rk4(
                window, initial_theta=3.0, individual=IndividualParams(tau_hours=tau), registry=[]
            )
            assert result.net_shift_hours == pytest.approx(0.0, abs=1e-9)

    def test_tau_24_stays_locked_to_clock_time(self) -> None:
        start = datetime(2026, 3, 1, tzinfo=UTC)
        window = SimulationWindow(start=start, end=start + timedelta(days=14))
        result = simulate_rk4(
            window, initial_theta=6.0, individual=IndividualParams(tau_hours=24.0), registry=[]
        )
        # exactly 14 whole cycles later, phase returns to where it started
        assert result.final_theta == pytest.approx(6.0, abs=1e-6)


class TestSimulationResultShape:
    def test_samples_span_the_window(self) -> None:
        start = datetime(2026, 3, 1, tzinfo=UTC)
        end = start + timedelta(days=2)
        window = SimulationWindow(start=start, end=end, step_hours=0.5)
        result = simulate_rk4(window, 0.0, IndividualParams(), [])

        assert result.samples[0].t == start
        assert result.samples[-1].t == end
        assert result.method == "rk4"
        assert all(0.0 <= s.theta < 24.0 for s in result.samples)

    def test_forcing_is_zero_without_stimuli(self) -> None:
        start = datetime(2026, 3, 1, tzinfo=UTC)
        window = SimulationWindow(start=start, end=start + timedelta(days=1))
        result = simulate_rk4(window, 0.0, IndividualParams(), [])
        assert all(s.forcing == 0.0 for s in result.samples)


class TestEstimateInitialTheta:
    def test_cbtmin_is_three_hours_before_wake(self) -> None:
        """At exactly the estimated CBTmin instant, theta must be 0 by definition."""
        tz = "UTC"
        timeline = [
            ScheduleSegment(
                start=datetime(2026, 1, 1, tzinfo=UTC),
                sleep_window_local=(time(23, 0), time(7, 0)),
                tz=tz,
            )
        ]
        # wake 07:00 -> CBTmin 04:00
        at_cbtmin = datetime(2026, 1, 5, 4, 0, tzinfo=UTC)
        assert estimate_initial_theta(timeline, at_cbtmin) == pytest.approx(0.0, abs=1e-9)

    def test_hours_after_cbtmin(self) -> None:
        timeline = [
            ScheduleSegment(
                start=datetime(2026, 1, 1, tzinfo=UTC),
                sleep_window_local=(time(23, 0), time(7, 0)),
                tz="UTC",
            )
        ]
        assert estimate_initial_theta(
            timeline, datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        ) == pytest.approx(6.0)

    def test_wraps_when_before_that_days_cbtmin(self) -> None:
        """02:00 is 2h before the 04:00 CBTmin, i.e. 22h after the previous one."""
        timeline = [
            ScheduleSegment(
                start=datetime(2026, 1, 1, tzinfo=UTC),
                sleep_window_local=(time(23, 0), time(7, 0)),
                tz="UTC",
            )
        ]
        assert estimate_initial_theta(
            timeline, datetime(2026, 1, 5, 2, 0, tzinfo=UTC)
        ) == pytest.approx(22.0)

    def test_uses_the_active_segment_not_the_first(self) -> None:
        """Generalization past origin/destination: a later segment's schedule is
        what anchors phase once that segment is active."""
        timeline = [
            ScheduleSegment(
                start=datetime(2026, 1, 1, tzinfo=UTC),
                sleep_window_local=(time(23, 0), time(7, 0)),
                tz="UTC",
            ),
            ScheduleSegment(
                start=datetime(2026, 1, 10, tzinfo=UTC),
                sleep_window_local=(time(3, 0), time(11, 0)),
            ),
        ]
        # second segment: wake 11:00 -> CBTmin 08:00; at 08:00 theta == 0
        assert estimate_initial_theta(
            timeline, datetime(2026, 1, 15, 8, 0, tzinfo=UTC)
        ) == pytest.approx(0.0, abs=1e-9)

    def test_falls_back_to_zero_when_free_running(self) -> None:
        timeline = [ScheduleSegment(start=datetime(2026, 1, 1, tzinfo=UTC), tz="UTC")]
        assert estimate_initial_theta(timeline, datetime(2026, 1, 5, tzinfo=UTC)) == 0.0

    def test_falls_back_to_zero_for_empty_timeline(self) -> None:
        assert estimate_initial_theta([], datetime(2026, 1, 5, tzinfo=UTC)) == 0.0
