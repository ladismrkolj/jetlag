import datetime
from typing import Dict, List

def plan_circadian(
    mode, # advance or delay
    cbtmin_waypoints: List[datetime.datetime],
    enabled_interventions, # melatonin, light, dark, exercise, sleep shift - same as in setings
    rule_windows, # list of datetime windows (UTC) which define certain interventions. sleep, no interventions, etc. allow to be repeatable (e.g. sleep every day)
    fixed_events, # list of datetime events (UTC) which are fixed
    settings, # caps/limits, PRC models, suboptimality functions, (snapping/search parameters), defaults.
):
    real_cbt_entries: List[datetime.datetime] = []

    real_cbt_entries.append(cbtmin_waypoints[0]) # first cbtmin is the one we start, so we cannot already shift this one

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
    #         "end": datetime(2026, 2, 13, 8, 0)     # end time (UTC)
    #     },
    #     {
    #         "type": "light",
    #         "start": datetime(2026, 2, 13, 10, 0),
    #         "end": datetime(2026, 2, 13, 11, 0)
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


    # iteration algorithm
    for i in range(1, len(cbtmin_waypoints)):
        cbtmin_target = cbtmin_waypoints[i]
        current_cbtmin = real_cbt_entries[-1] + datetime.timedelta(days=1) # we know that the next cbt min is exactly 24h later, but we will shift it later.

        # extract current sleep from the rule_windows - we need this for interventions that are based on sleep or modify sleep

        # extract fixed events for the relevant 24h window (current cbtmin -24h)
        # these events should be light, dark, exercise, melatonin, sleep (calculate shift from normal sleep or previous day)

        # the logic is that interventions that shift current cbtmin occur before it. even if prc windows is after, that means we shift it 24h to the one before - already in the settings
        for intervention in enabled_interventions:
            intervention_settings = settings['interventions'][intervention]
            if intervention_settings['reference'] == 'cbtmin':
                if mode == 'advance':
                    intervention_start = current_cbtmin + datetime.timedelta(hours=intervention_settings['advance_start_h'])
                    intervention_end = current_cbtmin + datetime.timedelta(hours=intervention_settings['advance_stop_h'])
                else: # delay
                    intervention_start = current_cbtmin + datetime.timedelta(hours=intervention_settings['delay_start_h'])
                    intervention_end = current_cbtmin + datetime.timedelta(hours=intervention_settings['delay_stop_h'])
            elif intervention_settings['reference'] == 'sleep':
                # we need to find the sleep window that is before the current cbtmin and use it as reference
                sleep_windows_before_cbtmin = [w for w in rule_windows_processed if w['type'] == 'sleep' and w['end'] <= current_cbtmin]
                if not sleep_windows_before_cbtmin:
                    continue # if there is no sleep window before current cbtmin, we cannot use this intervention
                last_sleep_window = max(sleep_windows_before_cbtmin, key=lambda w: w['end'])
                if mode == 'advance':
                    intervention_start = last_sleep_window['end'] + datetime.timedelta(hours=intervention_settings['advance_start_h'])
                    intervention_end = last_sleep_window['end'] + datetime.timedelta(hours=intervention_settings['advance_stop_h'])
                else: # delay
                    intervention_start = last_sleep_window['end'] + datetime.timedelta(hours=intervention_settings['delay_start_h'])
                    intervention_end = last_sleep_window['end'] + datetime.timedelta(hours=intervention_settings['delay_stop_h'])

        # move/shorten/remove interventions based on filter windows

        # save them to events schedule

        # calculate next cbtmin based on a external function

        # save cbtmin to the list