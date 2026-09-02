from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from circadian.schedule import (
    ScheduleSegment,
    is_in_local_window,
    is_sleep_at,
    local_time_at,
    segment_at,
    sleep_window_at,
    tz_at,
)


def _seg(
    start: datetime,
    sleep: tuple[time, time] | None = None,
    tz: str | None = None,
    label: str = "",
) -> ScheduleSegment:
    return ScheduleSegment(start=start, sleep_window_local=sleep, tz=tz, label=label)


class TestScheduleSegmentValidation:
    def test_rejects_naive_start(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            ScheduleSegment(start=datetime(2026, 1, 1, 0, 0))

    def test_rejects_bogus_timezone_eagerly(self) -> None:
        from zoneinfo import ZoneInfoNotFoundError

        with pytest.raises((ZoneInfoNotFoundError, ValueError)):
            ScheduleSegment(start=datetime(2026, 1, 1, tzinfo=UTC), tz="Mars/Olympus_Mons")

    def test_accepts_valid_zone(self) -> None:
        seg = ScheduleSegment(start=datetime(2026, 1, 1, tzinfo=UTC), tz="Europe/Ljubljana")
        assert seg.tz == "Europe/Ljubljana"


class TestSegmentAt:
    def test_none_before_first_segment(self) -> None:
        timeline = [_seg(datetime(2026, 1, 10, tzinfo=UTC))]
        assert segment_at(timeline, datetime(2026, 1, 9, tzinfo=UTC)) is None

    def test_none_for_empty_timeline(self) -> None:
        assert segment_at([], datetime(2026, 1, 9, tzinfo=UTC)) is None

    def test_picks_latest_segment_at_or_before_t(self) -> None:
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), label="a"),
            _seg(datetime(2026, 1, 5, tzinfo=UTC), label="b"),
            _seg(datetime(2026, 1, 9, tzinfo=UTC), label="c"),
        ]
        assert segment_at(timeline, datetime(2026, 1, 6, tzinfo=UTC)).label == "b"  # type: ignore[union-attr]
        assert segment_at(timeline, datetime(2026, 1, 9, tzinfo=UTC)).label == "c"  # type: ignore[union-attr]
        assert segment_at(timeline, datetime(2026, 2, 1, tzinfo=UTC)).label == "c"  # type: ignore[union-attr]

    def test_sorts_defensively(self) -> None:
        timeline = [
            _seg(datetime(2026, 1, 9, tzinfo=UTC), label="c"),
            _seg(datetime(2026, 1, 1, tzinfo=UTC), label="a"),
        ]
        assert segment_at(timeline, datetime(2026, 1, 3, tzinfo=UTC)).label == "a"  # type: ignore[union-attr]


class TestTzAt:
    def test_carries_forward_last_specified_zone(self) -> None:
        """A segment with tz=None means 'unchanged' -- the night-shift-prep case,
        where only the sleep window moves and the timezone never does."""
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), tz="America/New_York"),
            _seg(datetime(2026, 1, 3, tzinfo=UTC), tz=None),
            _seg(datetime(2026, 1, 5, tzinfo=UTC), tz=None),
        ]
        assert tz_at(timeline, datetime(2026, 1, 6, tzinfo=UTC)) == "America/New_York"

    def test_updates_on_each_new_zone(self) -> None:
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), tz="America/New_York"),
            _seg(datetime(2026, 1, 3, tzinfo=UTC), tz="Europe/Paris"),
            _seg(datetime(2026, 1, 5, tzinfo=UTC), tz="Asia/Tokyo"),
        ]
        assert tz_at(timeline, datetime(2026, 1, 2, tzinfo=UTC)) == "America/New_York"
        assert tz_at(timeline, datetime(2026, 1, 4, tzinfo=UTC)) == "Europe/Paris"
        assert tz_at(timeline, datetime(2026, 1, 9, tzinfo=UTC)) == "Asia/Tokyo"

    def test_none_when_never_specified(self) -> None:
        timeline = [_seg(datetime(2026, 1, 1, tzinfo=UTC))]
        assert tz_at(timeline, datetime(2026, 1, 2, tzinfo=UTC)) is None


class TestLocalTimeAtAndDst:
    def test_converts_to_segment_zone(self) -> None:
        timeline = [_seg(datetime(2026, 1, 1, tzinfo=UTC), tz="Asia/Tokyo")]
        t = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
        assert local_time_at(timeline, t).hour == 9  # Tokyo is UTC+9, no DST

    def test_resolves_dst_offset_per_instant_not_once_per_trip(self) -> None:
        """The DST fix: one timeline spanning a daylight-saving transition must
        report the correct local time on BOTH sides of it. A cached fixed offset
        (what app/lib/jetlag.ts does) would be an hour wrong after the change."""
        timeline = [_seg(datetime(2026, 1, 1, tzinfo=UTC), tz="America/New_York")]

        winter = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)  # EST, UTC-5
        summer = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)  # EDT, UTC-4

        assert local_time_at(timeline, winter).utcoffset() == timedelta(hours=-5)
        assert local_time_at(timeline, summer).utcoffset() == timedelta(hours=-4)
        assert local_time_at(timeline, winter).hour == 7
        assert local_time_at(timeline, summer).hour == 8

    def test_returns_t_unchanged_when_no_zone_known(self) -> None:
        timeline = [_seg(datetime(2026, 1, 1, tzinfo=UTC))]
        t = datetime(2026, 1, 2, 3, 0, tzinfo=UTC)
        assert local_time_at(timeline, t) == t


class TestIsInLocalWindow:
    def test_normal_window(self) -> None:
        window = (time(9, 0), time(17, 0))
        assert is_in_local_window(datetime(2026, 1, 1, 12, 0, tzinfo=UTC), window)
        assert not is_in_local_window(datetime(2026, 1, 1, 8, 0, tzinfo=UTC), window)
        assert not is_in_local_window(datetime(2026, 1, 1, 17, 0, tzinfo=UTC), window)

    def test_window_crossing_midnight(self) -> None:
        window = (time(23, 0), time(7, 0))
        assert is_in_local_window(datetime(2026, 1, 1, 23, 30, tzinfo=UTC), window)
        assert is_in_local_window(datetime(2026, 1, 1, 2, 0, tzinfo=UTC), window)
        assert not is_in_local_window(datetime(2026, 1, 1, 7, 0, tzinfo=UTC), window)
        assert not is_in_local_window(datetime(2026, 1, 1, 12, 0, tzinfo=UTC), window)


class TestIsSleepAt:
    def test_uses_local_clock_of_active_segment(self) -> None:
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), sleep=(time(23, 0), time(7, 0)), tz="Asia/Tokyo")
        ]
        # 2026-01-02 15:00Z == 2026-01-03 00:00 Tokyo -> inside 23:00-07:00
        assert is_sleep_at(timeline, datetime(2026, 1, 2, 15, 0, tzinfo=UTC))
        # 2026-01-02 03:00Z == 2026-01-02 12:00 Tokyo -> awake
        assert not is_sleep_at(timeline, datetime(2026, 1, 2, 3, 0, tzinfo=UTC))

    def test_free_running_segment_is_never_sleep(self) -> None:
        timeline = [_seg(datetime(2026, 1, 1, tzinfo=UTC), sleep=None, tz="Asia/Tokyo")]
        assert not is_sleep_at(timeline, datetime(2026, 1, 2, 15, 0, tzinfo=UTC))

    def test_sleep_window_switches_with_segment(self) -> None:
        """Night-shift prep: same timezone, sleep window jumps to daytime."""
        tz = "Europe/Ljubljana"
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), sleep=(time(23, 0), time(7, 0)), tz=tz),
            _seg(datetime(2026, 1, 10, tzinfo=UTC), sleep=(time(9, 0), time(17, 0))),
        ]
        # 12:00 local on Jan 5 -> awake (night-schedule week)
        early = datetime(2026, 1, 5, 11, 0, tzinfo=UTC)  # 12:00 Ljubljana (UTC+1)
        assert not is_sleep_at(timeline, early)
        # 12:00 local on Jan 15 -> asleep (day-sleeping night-shift week)
        late = datetime(2026, 1, 15, 11, 0, tzinfo=UTC)
        assert is_sleep_at(timeline, late)


class TestSleepWindowAt:
    def test_returns_active_segments_window(self) -> None:
        timeline = [
            _seg(datetime(2026, 1, 1, tzinfo=UTC), sleep=(time(23, 0), time(7, 0)), tz="UTC"),
            _seg(datetime(2026, 1, 5, tzinfo=UTC), sleep=(time(1, 0), time(9, 0))),
        ]
        early = datetime(2026, 1, 3, tzinfo=UTC)
        late = datetime(2026, 1, 7, tzinfo=UTC)
        assert sleep_window_at(timeline, early) == (time(23, 0), time(7, 0))
        assert sleep_window_at(timeline, late) == (time(1, 0), time(9, 0))

    def test_none_before_first_segment(self) -> None:
        timeline = [_seg(datetime(2026, 1, 5, tzinfo=UTC), sleep=(time(23, 0), time(7, 0)))]
        assert sleep_window_at(timeline, datetime(2026, 1, 1, tzinfo=UTC)) is None


class TestZoneInfoSanity:
    """Guards against a missing tzdata install silently degrading DST handling."""

    def test_dst_database_is_present(self) -> None:
        ny = ZoneInfo("America/New_York")
        jan = datetime(2026, 1, 15, 12, 0, tzinfo=ny)
        jul = datetime(2026, 7, 15, 12, 0, tzinfo=ny)
        assert jan.utcoffset() != jul.utcoffset()
