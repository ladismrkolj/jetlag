import pytest

from circadian.angles import circular_diff, wrap24


class TestWrap24:
    def test_already_in_range(self) -> None:
        assert wrap24(5.5) == pytest.approx(5.5)

    def test_negative(self) -> None:
        assert wrap24(-1.0) == pytest.approx(23.0)

    def test_exactly_24(self) -> None:
        assert wrap24(24.0) == pytest.approx(0.0)

    def test_large_multiple(self) -> None:
        assert wrap24(24.0 * 5 + 3.25) == pytest.approx(3.25)

    def test_large_negative(self) -> None:
        assert wrap24(-24.0 * 3 - 1.0) == pytest.approx(23.0)


class TestCircularDiff:
    def test_zero(self) -> None:
        assert circular_diff(5.0, 5.0) == pytest.approx(0.0)

    def test_simple_positive(self) -> None:
        assert circular_diff(10.0, 8.0) == pytest.approx(2.0)

    def test_simple_negative(self) -> None:
        assert circular_diff(8.0, 10.0) == pytest.approx(-2.0)

    def test_wraps_shortest_path_forward(self) -> None:
        # 1 o'clock is 2 hours *after* 23:00 going forward through midnight --
        # the shorter way round than 22 hours backward.
        assert circular_diff(1.0, 23.0) == pytest.approx(2.0)

    def test_wraps_shortest_path_backward(self) -> None:
        assert circular_diff(23.0, 1.0) == pytest.approx(-2.0)

    def test_antipodal_boundary_reports_positive_half_period(self) -> None:
        assert circular_diff(12.0, 0.0) == pytest.approx(12.0)
        assert circular_diff(0.0, 12.0) == pytest.approx(12.0)

    def test_custom_period(self) -> None:
        assert circular_diff(1.0, 11.0, period=12.0) == pytest.approx(2.0)
