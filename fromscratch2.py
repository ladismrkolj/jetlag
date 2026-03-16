from typing import List, Tuple, Dict
from datetime import datetime, timedelta, time


# all datetimes are in UTC
def iterative_algorithm(
    ct_targets: List[Tuple[datetime, time]], # derive start from ct targets. first is from when, second is target cbtmin time (utc)
    usual_sleep_times: List[Tuple[datetime, time, time]], # same as before, first is from when, secons and third are windows (utc)
    travels: List[Tuple[datetime, datetime, float, float]],  # (departure (utc), arrival (utc), tz1, tz2); departure >= arrival
    allow_during_sleep: Dict[str, bool] = {'sleep_shift': False, 'light': False, 'melatonin': False}, # standardized dict of all three dicts. channels are interventions; values are bool
    allow_during_travel:  Dict[str, bool] = {'sleep_shift': False, 'light': False, 'melatonin': False}, 
    intervention_filters: List[Tuple[datetime, datetime, Dict[str, bool]]] = [] # overrides for allow_during_sleep and allow_during_travel; (start, end, dict of channel -> bool)
) -> List[Tuple[datetime, datetime, str]] :
    
    if ct_targets is []:
        raise ValueError("ct_targets cannot be empty")
    if any(t[0] > t[1] for t in travels):
        raise ValueError("Each travel departure must be at or before arrival")
    
    interventions = {'sleep_shift', 'light', 'melatonin'} # these are the interventions we consider

    if allow_during_sleep.keys() != interventions or allow_during_travel.keys() != interventions:
        raise ValueError(f"allow_during_sleep and allow_during_travel must have the keys: {interventions}")
    if any(d.keys() != interventions for d in intervention_filters):
        raise ValueError(f"Each dict in intervention_filters must have the keys: {interventions}")
    
    events: List[Tuple[datetime, datetime, str]] = [] # (start, end, type) where type is "cbtmin", "sleep", "travel", or "intervention"
    events_types = interventions.union({"cbtmin", "sleep", "travel"})

    # 

    return events