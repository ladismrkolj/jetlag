import datetime
from typing import Dict, List, Optional

light_advance_start_h = 0
light_advance_stop_h = 6
light_delay_start_h = 18
light_delay_stop_h = 24
exercise_advance_start_h = 0
exercise_advance_stop_h = 6
exercise_delay_start_h = 18
exercise_delay_stop_h = 24
melatonin_advance_h = 12.5 #check
melatonin_delay_h = 20 #check
max_daily_advance_h = 1.5
max_daily_delay_h = 1.5

def apply_filters(
    start: datetime.datetime,
    end: Optional[datetime.datetime],
    rule_windows: List[Dict],
    intervention: str,
):
    """
    Trim or reject a proposed time window for `intervention` based on the
    supplied `rule_windows`.  If `end` is None the request is treated as a
    single point.  The returned tuple is either the adjusted (start, end)
    or (None, None) when the interval/point is completely blocked.

    This simple version only clips the ends or discards the whole window;
    later we can add searching for the next usable segment.
    """
    # sort so results are deterministic
    for win in sorted(rule_windows, key=lambda w: w["start"]):
        if intervention not in win.get("blocked_interventions", []):
            continue

        wstart = win["start"]
        wend = win.get("end")

        # point case
        if end is None:
            if wstart <= start < (wend if wend is not None else start):
                return None, None
            else:
                continue

        # completely covered
        if wstart <= start and (wend is None or wend >= end):
            return None, None

        # overlaps beginning
        if wstart <= start < wend:
            start = wend

        # overlaps end
        if wstart < end <= wend:
            end = wstart

        # interior block – keep earlier segment
        if wstart > start and (wend is None or wend < end):
            end = wstart

        if end is not None and start >= end:
            return None, None

    return start, end

def plan_circadian(
    cbtmin_waypoints: List[datetime.datetime],
    enabled_interventions, # melatonin, light, dark, exercise, sleep shift - same as in setings
    rule_windows, # list of datetime windows (UTC) which define certain interventions. sleep, no interventions, etc. allow to be repeatable (e.g. sleep every day)
    fixed_events = [], # list of datetime events (UTC) which are fixed
#    settings, # caps/limits, PRC models, suboptimality functions, (snapping/search parameters), defaults.
):
    cbt_entries: List[datetime.datetime] = []

    cbt_entries.append(cbtmin_waypoints[0]) # first cbtmin is the one we start, so we cannot already shift this one

    rule_windows_processed: List[Dict] = [] # dict keys: start, end, type, interventions_filter - same name as in settings dict
    # the algoritm works in iterations. It moves time to the next cbt min and looks at what interventions 
    # are possible given different rules and settings. also generates repeatable rules events if new day. 
    # It stores these rules, since the innputs are not necessarily deterministic (e.g. repeatable)
    # the algorithm stops when the cbt min is close enough to the target or we reach max_days.
    # rule_windows structure:
    # {
    #     "type": "sleep",                                    # intervention type sleep, travel or other
    #     "start": datetime(2026, 2, 13, 22, 0),             # start time (UTC)
    #     "end": datetime(2026, 2, 14, 6, 0),                # end time (UTC)
    #     "blocked_interventions": ["exercise", "work"],     # interventions blocked during this interval
    #     "repeat_until": None                               # None = doesn't repeat, datetime = repeats daily until then
    # }
    # interventions structure:
    # [
    #     {
    #         "type": "exercise",                    # matches settings name
    #         "start": datetime(2026, 2, 13, 7, 0),  # start time (UTC)
    #         "end": datetime(2026, 2, 13, 8, 0),     # end time (UTC)
    #         "value": 1.0                           # optional, e.g. for exercise intensity or light intensity
    #     },
    #     {
    #         "type": "light",
    #         "start": datetime(2026, 2, 13, 10, 0),
    #         "end": datetime(2026, 2, 13, 11, 0),
    #         "value": 1.0                           # optional, e.g. for exercise intensity or light intensity
    #     }
    # ]
    # settings structure:
    # {
    #     "max_daily_advance_h": 1.5,
    #     "max_daily_delay_h": 1.5,
    #     "cbtmin_from_sleep": lambda sleep_end: sleep_end + datetime.timedelta(hours=-2.5), # example function, in real life more complex and based on data
    #     "interventions": {
    #         "light": {
    #             "reference": "cbtmin" # or sleep or fixed time
    #             "advance_start_h": -12,
    #             "advance_stop_h": -2,
    #             "delay_start_h": 0,
    #             "delay_stop_h": 8,
    #             "standalone_max_effect_per_day_h": 1.5
    #         },
    #         ...
    #     }
    # }

    # fillout the rules for the first day and max_interventions_time forward and backwards
    for rule_window in rule_windows:
        # if the rule is not repeatable we just add it to the 
        if rule_window['repeat_until'] is None:
            # Remove 'repeat_until' key
            rule_window_copy = {k: v for k, v in rule_window.items() if k != 'repeat_until'}
            rule_windows_processed.append(rule_window_copy)
            continue
        # if the rule is repeatable, we need to generate the events until some very far in the future - this is an ugly way to do it
        current_date = rule_window['start']
        very_far_date = rule_window['start'] + datetime.timedelta(days=20)
        while current_date < very_far_date:
            # Stop at repeat_until date (exclusive - don't include repeat_until day)
            if current_date >= rule_window['repeat_until']:
                break
            
            rule_window_copy = rule_window.copy()
            rule_window_copy['start'] = current_date
            rule_window_copy['end'] = current_date + (rule_window['end'] - rule_window['start'])
            # Remove 'repeat_until' key before appending
            rule_window_copy.pop('repeat_until')
            rule_windows_processed.append(rule_window_copy)
            current_date += datetime.timedelta(days=1)

    events = [] # list of completed interventions and other events, same structure as proposed interventions, but with actual start and end times after applying filters and adjustments. this is the final output of the algorithm, which can be used for scheduling and tracking.
    # iteration algorithm
    for i in range(1, len(cbtmin_waypoints)):
        cbtmin_target = cbtmin_waypoints[i]
        last_cbtmin = cbt_entries[-1]
        current_cbtmin = cbt_entries[-1] + datetime.timedelta(days=1) # we know that the next cbt min is exactly 24h later, but we will shift it later.

        cbtmin_diff = (cbtmin_target - current_cbtmin).total_seconds() / 3600.0 # in hours float
        # TODO what to do if we are close to target? less than 3h no interventions...

        direction = 'advance' if cbtmin_diff < 0 else 'delay'
        # extract current sleep from the rule_windows - we need this for interventions that are based on sleep or modify sleep
        # look for the first (closest) sleep start which is -3 to -27 h before current cbtmin, than take this window as reference sleep.
        sleep_windows = [w for w in rule_windows_processed if w['type'] == 'sleep']
        reference_sleep_window_list = [w for w in sleep_windows if w['start'] > current_cbtmin - datetime.timedelta(hours=27) and w['start'] <= current_cbtmin - datetime.timedelta(hours=3)]
        # for sleep we need to calculate the shift based on the reference sleep (which is the closest sleep before current cbtmin)
        reference_sleep_start = reference_sleep_window_list[0]['start'] # take the closest one
        reference_sleep_end = reference_sleep_window_list[0]['end']
        # extract fixed events for the relevant 24h window (current cbtmin -24h)
        # these events should be light, dark, exercise, melatonin, sleep (calculate shift from normal sleep or previous day)

        # the logic is that interventions that shift current cbtmin occur before it. even if prc windows is after, that means we shift it 24h to the one before - already in the settings
        proposed_interventions = []
        if "light" in enabled_interventions:
            if direction == 'advance':
                light_start = last_cbtmin + datetime.timedelta(hours=light_advance_start_h)
                light_end = last_cbtmin + datetime.timedelta(hours=light_advance_stop_h)
                light_start, light_end = apply_filters(light_start, light_end, rule_windows_processed, intervention="light")
            else:
                light_start = last_cbtmin + datetime.timedelta(hours=light_delay_start_h)
                light_end = last_cbtmin + datetime.timedelta(hours=light_delay_stop_h)
                light_start, light_end = apply_filters(light_start, light_end, rule_windows_processed, intervention="light")
            
            if light_start is not None or light_end is not None:
                proposed_interventions.append({
                    "type": "light",
                    "start": light_start,
                    "end": light_end,
                    "value" : 1000 #lux
                })

        if "exercise" in enabled_interventions:
            if direction == 'advance':
                exercise_start = last_cbtmin + datetime.timedelta(hours=exercise_advance_start_h) # these values should be in settings, but for now hardcoded
                exercise_end = last_cbtmin + datetime.timedelta(hours=exercise_advance_stop_h)
                exercise_start, exercise_end = apply_filters(exercise_start, exercise_end, rule_windows_processed, intervention="exercise")
            else:
                exercise_start = last_cbtmin + datetime.timedelta(hours=exercise_delay_start_h)
                exercise_end = last_cbtmin + datetime.timedelta(hours=exercise_delay_stop_h)
                exercise_start, exercise_end = apply_filters(exercise_start, exercise_end, rule_windows_processed, intervention="exercise")
            
            if exercise_start is not None or exercise_end is not None:
                proposed_interventions.append({
                    "type": "exercise",
                    "start": exercise_start,
                    "end": exercise_end,
                    "value" : 1.0 # intensity
                })

        if "melatonin" in enabled_interventions:
            if direction =='advance':
                melatonin_time = last_cbtmin + datetime.timedelta(hours=melatonin_advance_h) # these values should be in settings, but for now hardcoded
                melatonin_time, _ = apply_filters(melatonin_time, None, rule_windows_processed, intervention="melatonin")
            else:
                melatonin_time = last_cbtmin + datetime.timedelta(hours=melatonin_delay_h)
                melatonin_time, _ = apply_filters(melatonin_time, None, rule_windows_processed, intervention="melatonin")
        
            if melatonin_time is not None:
                proposed_interventions.append({
                    "type": "melatonin",
                    "start": melatonin_time,
                    "end": None,
                    "value" : 0.5 # dose
                })
        
        if "sleep_shift" in enabled_interventions and len(reference_sleep_window_list) > 0:
            # TODO determine if previous sleep was also shifted and if yes we increase the shift relative to that shift.
            # for now, change is target cbtmin restarts this

            if direction == 'advance':
                proposed_sleep_start = reference_sleep_start + datetime.timedelta(hours=-1)
                proposed_sleep_end = reference_sleep_end + datetime.timedelta(hours=-1)
                postfilter_sleep_start, postfilter_sleep_end = apply_filters(proposed_sleep_start, proposed_sleep_end, rule_windows_processed, intervention="sleep_shift") # check the widest window if there is any filter preventing
            else:
                proposed_sleep_start = reference_sleep_start + datetime.timedelta(hours=1)
                proposed_sleep_end = reference_sleep_end + datetime.timedelta(hours=1)
                postfilter_sleep_start, postfilter_sleep_end = apply_filters(proposed_sleep_start, proposed_sleep_end, rule_windows_processed, intervention="sleep_shift") # check the widest window if there is any filter preventing

            # this intervention is a bit more complex
            if postfilter_sleep_start == proposed_sleep_start and postfilter_sleep_end == proposed_sleep_end:
                proposed_interventions.append({
                    "type": "sleep_shift",
                    "start": proposed_sleep_start,
                    "end": proposed_sleep_end,
                    "value" : None # we can calculate shift from normal sleep later if needed
            })
            # we also need to shift this and a couple more sleep windows
            # TODO how many sleep windows to shift? maybe all that are after the reference sleep and before the next cbtmin?
            sleep_index = [i for i, w in enumerate(rule_windows_processed) if w['type'] == 'sleep' and w['start'] == reference_sleep_start and w['end'] == reference_sleep_end]
            rule_windows_processed[sleep_index[0]]['start'] = proposed_sleep_start
            rule_windows_processed[sleep_index[0]]['end'] = proposed_sleep_end

            
        # TODO move/shorten/remove interventions based on filter windows here instead of above

        # TODO calculate next cbtmin based on a external function
        if direction == 'advance':
            cbtmin_shift = -min(-cbtmin_diff, max_daily_advance_h) # we cannot shift more than max_daily_advance_h, even if the target is further away
        else:
            cbtmin_shift = min(cbtmin_diff, max_daily_delay_h) # we cannot shift more than max_daily_delay_h, even if the target is further away
        shifted_current_cbtmin = current_cbtmin + datetime.timedelta(hours=cbtmin_shift)

        # save cbtmin to the list
        cbt_entries.append(shifted_current_cbtmin)

        # TODO save them to events schedule
        events.extend(proposed_interventions)
        events.append({
            "type": "sleep",
            "start": reference_sleep_start,
            "end": reference_sleep_end,
            "value": None
        })
        # TODO update rule_windows_processed with the new cbtmin if there are any rules based on cbtmin (e.g. light based on cbtmin)
        
    # add cbtmin to events
    for cbt_event in cbt_entries:
        events.append({
            "type": "cbtmin",
            "start": cbt_event,
            "end": None,
            "value": None
        })

    #return the list of cbtmin entries and the list of events - interventions, sleep, cbtmin, etc.
    return events


def run_showcase_test() -> None:
    start = datetime.datetime(2026, 2, 1, 5, 0)
    cbtmin_waypoints = [
        start,
        start + datetime.timedelta(days=1),
        start + datetime.timedelta(days=2),
        start + datetime.timedelta(days=3, hours=6),
        start + datetime.timedelta(days=4, hours=6),
        start + datetime.timedelta(days=5, hours=6),
        start + datetime.timedelta(days=6, hours=6),
    ]
    rule_windows = [
        {
            "type": "sleep",
            "start": datetime.datetime(2026, 1, 31, 22, 0),
            "end": datetime.datetime(2026, 2, 1, 6, 0),
            "blocked_interventions": ["light", "exercise"],
            "repeat_until": datetime.datetime(2026, 2, 10, 0, 0),
        }
    ]
    enabled_interventions = ["light"]

    result = plan_circadian(
        cbtmin_waypoints=cbtmin_waypoints,
        enabled_interventions=enabled_interventions,
        rule_windows=rule_windows,
    )

    events = result

    #assert len(cbt_entries) == len(cbtmin_waypoints), "Expected one simulated CBTmin per waypoint"
    #assert any(e["type"] == "light" for e in events), "Expected at least one light event in showcase"

    print("Showcase test passed.")

    print("\nAll events:")
    for event in events:
        start_s = event["start"].isoformat(timespec="minutes") if event["start"] else "None"
        end_s = event["end"].isoformat(timespec="minutes") if event["end"] else "None"
        print(f"  - {event['type']:11s} start={start_s} end={end_s} value={event['value']}")


if __name__ == "__main__":
    run_showcase_test()
