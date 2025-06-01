from datetime import datetime, time, timezone, timedelta
import math

def main():

    tz1 = 1
    tz2 = -5

    tz1_sleep_start = 22.
    tz1_sleep_stop = 7.

    tz2_sleep_start = 22.
    tz2_sleep_stop = 7.

    travel_start = datetime(2025, 6, 1, 14, 30, tzinfo=timezone(timedelta(hours=tz1)))  
    travel_stop = datetime(2025, 6, 2, 14, 30, tzinfo=timezone(timedelta(hours=tz2)))

    # translate all to UTC

    CBTmin_start = (tz1_sleep_start - tz1 + 6) % 24
    CBTmin_target = (tz2_sleep_start - tz2 + 6) % 24


    # lets start at travel start
    timetable = [] # list of dict

    current_CBTmin = CBTmin_start
    next_CBTmin = current_CBTmin
    print(current_CBTmin-CBTmin_target)
    current_iter_time = travel_start.replace(minute=0)

    while abs((current_CBTmin-CBTmin_target) % 24) > 0.5:
        print(current_CBTmin-CBTmin_target)
        tt_dict = {
            "dt": current_iter_time,
            "sleep": False,
            "travel": False,
            "melatonin": False,
            "light_exposure": False,
            "light_avoidance": False,
            "CBTmin": False,
        }

        print(math.floor(current_CBTmin), current_iter_time.hour)

        if math.floor(current_CBTmin) == current_iter_time.hour:
            tt_dict["CBTmin"] = True
        
        if math.floor((current_CBTmin + 12) % 24) == current_iter_time.hour:
            current_CBTmin = next_CBTmin

        if travel_start <= current_iter_time <= travel_stop:
            tt_dict["sleep"] = False
            tt_dict["travel"] = True
        

        if (current_CBTmin-CBTmin_target) > 0:
            # current is later than target. ie East
            best_melatonin = -11.5
            if math.floor((current_CBTmin + best_melatonin) % 24) == current_iter_time.hour:
                tt_dict["melatonin"] = True
                next_CBTmin = (next_CBTmin - 1) % 24
            
        elif (current_CBTmin-CBTmin_target) < 0:
            # current is earlier than target. ie West
            best_melatonin = 4
            if math.floor((current_CBTmin + best_melatonin) % 24) == current_iter_time.hour:
                tt_dict["melatonin"] = True
                next_CBTmin = (next_CBTmin + 1) % 24

        current_iter_time = current_iter_time + timedelta(hours=1)
        timetable.append(tt_dict)
    
    print(timetable)


if __name__ == "__main__":
    main()