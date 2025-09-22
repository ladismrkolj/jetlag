from __future__ import annotations

import json
import sys
from datetime import datetime, time
import os
import traceback

from jetlag_core.schedule import create_jet_lag_timetable


def _parse_hhmm(s: str) -> time:
    try:
        h, m = s.split(":")
        return time(int(h), int(m))
    except Exception as e:
        raise ValueError(f"invalid HH:MM time: {s}") from e


def _parse_local_datetime(dt_s: str) -> datetime:
    # Expect 'YYYY-MM-DDTHH:MM' (no timezone), treat as naive local
    try:
        return datetime.strptime(dt_s, "%Y-%m-%dT%H:%M")
    except Exception as e:
        raise ValueError(f"invalid datetime-local: {dt_s}") from e


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        sys.stdout.write(json.dumps({"error": f"invalid json: {e}"}))
        return 1

    try:
        origin_offset = float(data["originOffset"])  # hours
        dest_offset = float(data["destOffset"])      # hours

        events = create_jet_lag_timetable(
            origin_timezone=origin_offset,
            destination_timezone=dest_offset,
            origin_sleep_start=_parse_hhmm(data["originSleepStart"]),
            origin_sleep_end=_parse_hhmm(data["originSleepEnd"]),
            destination_sleep_start=_parse_hhmm(data["destSleepStart"]),
            destination_sleep_end=_parse_hhmm(data["destSleepEnd"]),
            travel_start=_parse_local_datetime(data["travelStart"]),
            travel_end=_parse_local_datetime(data["travelEnd"]),
            use_melatonin=bool(data["useMelatonin"]),
            use_exercise=bool(data["useExercise"]),
            use_light_dark=bool(data["useLightDark"]),
            precondition_days=int(data.get("preDays", 0)),
            shift_on_travel_days=bool(data.get("shiftOnTravelDays", False)),
        )

        sys.stdout.write(json.dumps({"events": events}))
        return 0
    except Exception as e:
        if os.getenv("CALC_DEBUG"):
            tb = traceback.format_exc()
            sys.stdout.write(json.dumps({"error": str(e), "traceback": tb}))
        else:
            sys.stdout.write(json.dumps({"error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
