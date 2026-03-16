"""
fromscracth2_test.py

How to run:
- `pytest fromscracth2_test.py`
"""

from datetime import datetime, time, timezone

import pytest

from fromscratch2 import iterative_algorithm


@pytest.fixture
def valid_interventions_dict():
    return {'sleep_shift': False, 'light': False, 'melatonin': False}

def test_iterative_algorithm_accepts_valid_shapes(
    valid_interventions_dict
):    assert iterative_algorithm(
        ct_targets=[(datetime(2026, 3, 20, 4, 0), time(4, 0))],
        usual_sleep_times=[(datetime(2026, 3, 20, 4, 0), time(23, 0), time(7, 0))],
        travels=[],
        allow_during_sleep=valid_interventions_dict,
        allow_during_travel=valid_interventions_dict,
    ) is not None


def test_iterative_algorithm_rejects_departure_after_arrival(
    valid_interventions_dict
):
    with pytest.raises(
        ValueError,
        match="Each travel departure must be at or before arrival",
    ):
        iterative_algorithm(
            ct_targets=[(datetime(2026, 3, 20, 4, 0), time(4, 0))],
            usual_sleep_times=[(datetime(2026, 3, 20, 4, 0), time(23, 0), time(7, 0)), (datetime(2026, 3, 20, 4, 0), time(23, 0), time(7, 0))],
            travels=[
                (datetime(2026, 3, 20, 11, 0), datetime(2026, 3, 20, 10, 0), 0.0, 0.0)
            ],
            allow_during_sleep=valid_interventions_dict,
            allow_during_travel=valid_interventions_dict,
        )


def test_iterative_algorithm_rejects_wrong_sleep_keys(valid_interventions_dict):
    with pytest.raises(
        ValueError,
        match="allow_during_sleep and allow_during_travel must have the keys",
    ):
        iterative_algorithm(
            ct_targets=[(datetime(2026, 3, 20, 4, 0), time(4, 0))],
            usual_sleep_times=[(datetime(2026, 3, 20, 4, 0), time(23, 0), time(7, 0))],
            travels=[],
            allow_during_sleep={
                "something_wrong": False,
                "light": False,
                "melatonin": False,
            },
            allow_during_travel=valid_interventions_dict,
        )
