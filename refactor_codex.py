import datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


Interval = Tuple[datetime.datetime, datetime.datetime]

_LIGHT_KERNEL_DEFAULTS = {
    "A_D": 1.0,
    "mu_D": -8.0,
    "sigma_D": 3.0,
    "A_A": 1.0,
    "mu_A": 3.0,
    "sigma_A": 3.0,
    "L50": 500.0,
    "gamma": 1.0,
}


def wrap_hours(x: float) -> float:
    return ((x + 12.0) % 24.0) - 12.0


def _interval_minutes(interval: Interval) -> float:
    return max(0.0, (interval[1] - interval[0]).total_seconds() / 60.0)


def _intersect(a: Interval, b: Interval) -> Optional[Interval]:
    start = max(a[0], b[0])
    end = min(a[1], b[1])
    if start >= end:
        return None
    return start, end


def _merge_intervals(intervals: Sequence[Interval]) -> List[Interval]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda it: it[0])
    merged: List[Interval] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _subtract_intervals(base: Interval, blocked: Sequence[Interval]) -> List[Interval]:
    if not blocked:
        return [base]
    pieces: List[Interval] = [base]
    for block in _merge_intervals(blocked):
        next_pieces: List[Interval] = []
        for piece in pieces:
            overlap = _intersect(piece, block)
            if overlap is None:
                next_pieces.append(piece)
                continue
            if piece[0] < overlap[0]:
                next_pieces.append((piece[0], overlap[0]))
            if overlap[1] < piece[1]:
                next_pieces.append((overlap[1], piece[1]))
        pieces = next_pieces
        if not pieces:
            break
    return [p for p in pieces if p[1] > p[0]]


def _snap_up(ts: datetime.datetime, step_min: int) -> datetime.datetime:
    day_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed_seconds = (ts - day_start).total_seconds()
    step_seconds = float(step_min * 60)
    snapped_seconds = math.ceil(elapsed_seconds / step_seconds) * step_seconds
    return day_start + datetime.timedelta(seconds=snapped_seconds)


def _interval_to_indices(
    grid_start: datetime.datetime,
    steps: int,
    step_min: int,
    interval: Interval,
) -> Optional[Tuple[int, int]]:
    grid_end = grid_start + datetime.timedelta(minutes=steps * step_min)
    clipped = _intersect(interval, (grid_start, grid_end))
    if clipped is None:
        return None
    step_seconds = float(step_min * 60)
    start_idx = int(math.floor((clipped[0] - grid_start).total_seconds() / step_seconds))
    end_idx = int(math.ceil((clipped[1] - grid_start).total_seconds() / step_seconds))
    start_idx = max(0, min(start_idx, steps))
    end_idx = max(0, min(end_idx, steps))
    if start_idx >= end_idx:
        return None
    return start_idx, end_idx


def expand_rule_windows(
    rule_windows: Sequence[Dict[str, Any]],
    horizon_start: datetime.datetime,
    horizon_end: datetime.datetime,
) -> List[Dict[str, Any]]:
    processed: List[Dict[str, Any]] = []
    for rule in rule_windows:
        start = rule["start"]
        end = rule["end"]
        repeat_until = rule.get("repeat_until")
        if repeat_until is None:
            if _intersect((start, end), (horizon_start, horizon_end)) is not None:
                processed.append({k: v for k, v in rule.items() if k != "repeat_until"})
            continue
        duration = end - start
        repeat_end = min(repeat_until, horizon_end)
        current_start = start
        while current_start < repeat_end:
            current_end = current_start + duration
            if _intersect((current_start, current_end), (horizon_start, horizon_end)) is not None:
                rule_copy = {k: v for k, v in rule.items() if k != "repeat_until"}
                rule_copy["start"] = current_start
                rule_copy["end"] = current_end
                processed.append(rule_copy)
            current_start += datetime.timedelta(days=1)
    return sorted(processed, key=lambda w: w["start"])


def build_baseline_arrays(
    start: datetime.datetime,
    end: datetime.datetime,
    step_min: int,
    rule_windows_processed: Sequence[Dict[str, Any]],
    settings: Dict[str, Any],
) -> Tuple[List[float], List[float], List[float]]:
    if end <= start:
        raise ValueError("build_baseline_arrays expects end > start")

    step_seconds = step_min * 60.0
    steps = int(math.ceil((end - start).total_seconds() / step_seconds))
    baseline_cfg = settings.get("baseline", {})
    indoor_lux = float(baseline_cfg.get("indoor_lux", 200.0))
    dark_lux = float(baseline_cfg.get("dark_lux", 1.0))

    light = [indoor_lux for _ in range(steps)]
    melatonin = [0.0 for _ in range(steps)]
    exercise = [0.0 for _ in range(steps)]

    for window in rule_windows_processed:
        if window.get("type") != "sleep":
            continue
        indices = _interval_to_indices(start, steps, step_min, (window["start"], window["end"]))
        if indices is None:
            continue
        s_idx, e_idx = indices
        for idx in range(s_idx, e_idx):
            light[idx] = min(light[idx], dark_lux)

    return light, melatonin, exercise


def apply_events_to_arrays(
    light: List[float],
    melatonin: List[float],
    exercise: List[float],
    events: Sequence[Dict[str, Any]],
    start: datetime.datetime,
    step_min: int,
    settings: Dict[str, Any],
) -> None:
    interventions_cfg = settings.get("interventions", {})
    steps = len(light)
    baseline_dark = float(settings.get("baseline", {}).get("dark_lux", 1.0))

    for event in events:
        event_start = event["start"]
        event_end = event.get("end")
        if event_end is None:
            fallback_min = int(event.get("duration_min", step_min))
            event_end = event_start + datetime.timedelta(minutes=fallback_min)

        indices = _interval_to_indices(start, steps, step_min, (event_start, event_end))
        if indices is None:
            continue
        s_idx, e_idx = indices

        event_type = event.get("type")
        intervention_cfg = interventions_cfg.get(event_type, {})
        channel = event.get("channel", intervention_cfg.get("channel"))
        if channel is None:
            if event_type in {"light", "dark"}:
                channel = "light"
            elif event_type == "melatonin":
                channel = "melatonin"
            elif event_type == "exercise":
                channel = "exercise"
            else:
                continue

        if channel == "light":
            lux = float(event.get("lux", intervention_cfg.get("lux", baseline_dark)))
            is_dark_event = (
                bool(event.get("is_dark"))
                or event_type == "dark"
                or lux <= baseline_dark
                or intervention_cfg.get("force_min_lux", False)
            )
            for idx in range(s_idx, e_idx):
                if is_dark_event:
                    light[idx] = min(light[idx], lux)
                else:
                    light[idx] = max(light[idx], lux)
        elif channel == "melatonin":
            dose_mg = float(event.get("dose_mg", intervention_cfg.get("dose_mg", 0.0)))
            for idx in range(s_idx, e_idx):
                melatonin[idx] += dose_mg
        elif channel == "exercise":
            mets = float(event.get("mets", intervention_cfg.get("mets", 0.0)))
            for idx in range(s_idx, e_idx):
                exercise[idx] = max(exercise[idx], mets)


def _gaussian(x: float, mu: float, sigma: float) -> float:
    sigma = max(float(sigma), 1e-6)
    z = wrap_hours(x - mu) / sigma
    return math.exp(-0.5 * z * z)


def _phase_kernel(h: float, params: Dict[str, Any]) -> float:
    a_delay = float(params.get("A_D", _LIGHT_KERNEL_DEFAULTS["A_D"]))
    mu_delay = float(params.get("mu_D", _LIGHT_KERNEL_DEFAULTS["mu_D"]))
    sigma_delay = float(params.get("sigma_D", _LIGHT_KERNEL_DEFAULTS["sigma_D"]))
    a_advance = float(params.get("A_A", _LIGHT_KERNEL_DEFAULTS["A_A"]))
    mu_advance = float(params.get("mu_A", _LIGHT_KERNEL_DEFAULTS["mu_A"]))
    sigma_advance = float(params.get("sigma_A", _LIGHT_KERNEL_DEFAULTS["sigma_A"]))
    return a_delay * _gaussian(h, mu_delay, sigma_delay) - a_advance * _gaussian(h, mu_advance, sigma_advance)


def _saturating_response(value: float, x50: float, gamma: float = 1.0) -> float:
    value = max(0.0, value)
    x50 = max(1e-6, float(x50))
    gamma = max(1e-6, float(gamma))
    num = value ** gamma
    den = num + (x50 ** gamma)
    if den <= 0.0:
        return 0.0
    return num / den


def compute_phase_delta(
    cbtmin_ref: datetime.datetime,
    start: datetime.datetime,
    step_min: int,
    light: Sequence[float],
    melatonin: Sequence[float],
    exercise: Sequence[float],
    settings: Dict[str, Any],
) -> float:
    step_h = step_min / 60.0
    prc = settings.get("prc", {})
    light_params = {**_LIGHT_KERNEL_DEFAULTS, **prc.get("light", {})}
    melatonin_params = prc.get("melatonin", {})
    exercise_params = prc.get("exercise", {})

    total_delta_h = 0.0
    for idx in range(len(light)):
        t = start + datetime.timedelta(minutes=idx * step_min)
        h = wrap_hours((t - cbtmin_ref).total_seconds() / 3600.0)

        k_light = _phase_kernel(h, light_params)
        u_light = _saturating_response(
            light[idx],
            float(light_params.get("L50", 500.0)),
            float(light_params.get("gamma", 1.0)),
        )
        total_delta_h += k_light * u_light * step_h

        mel_shift_h = float(melatonin_params.get("delta_shift_h", 0.0))
        mel_gain = float(melatonin_params.get("eta", 1.0))
        mel_h = wrap_hours(h - mel_shift_h)
        if {"A_D", "A_A", "mu_D", "mu_A"}.issubset(melatonin_params.keys()):
            k_mel = _phase_kernel(mel_h, melatonin_params)
        else:
            # Melatonin tends to be approximately opposite to light PRC around CBTmin.
            k_mel = -_phase_kernel(mel_h, light_params)
        u_mel = _saturating_response(
            melatonin[idx],
            float(melatonin_params.get("D50", 0.3)),
            float(melatonin_params.get("gamma", 1.0)),
        )
        total_delta_h += mel_gain * k_mel * u_mel * step_h

        ex_shift_h = float(exercise_params.get("delta_shift_h", 0.0))
        ex_gain = float(exercise_params.get("kappa", 1.0))
        ex_h = wrap_hours(h - ex_shift_h)
        if {"A_D", "A_A", "mu_D", "mu_A"}.issubset(exercise_params.keys()):
            k_ex = _phase_kernel(ex_h, exercise_params)
        else:
            k_ex = _phase_kernel(ex_h, light_params)
        u_ex = _saturating_response(
            exercise[idx],
            float(exercise_params.get("M50", 3.0)),
            float(exercise_params.get("gamma", 1.0)),
        )
        total_delta_h += ex_gain * k_ex * u_ex * step_h

    caps = settings.get("caps", {})
    max_advance_h = float(caps.get("max_daily_advance_h", settings.get("max_daily_advance_h", 1.5)))
    max_delay_h = float(caps.get("max_daily_delay_h", settings.get("max_daily_delay_h", 1.5)))
    total_delta_h = min(total_delta_h, max_delay_h)
    total_delta_h = max(total_delta_h, -max_advance_h)
    return total_delta_h


def propose_candidate_blocks(
    intervention: str,
    allowed_interval: Interval,
    step_min: int,
    settings: Dict[str, Any],
) -> List[Dict[str, Any]]:
    intervention_cfg = settings.get("interventions", {}).get(intervention, {})
    block_sizes = intervention_cfg.get("candidate_block_min", intervention_cfg.get("block_min", 30))
    if isinstance(block_sizes, (int, float)):
        block_minutes = [int(block_sizes)]
    else:
        block_minutes = [int(x) for x in block_sizes]
    if "block_min" in intervention_cfg and int(intervention_cfg["block_min"]) not in block_minutes:
        block_minutes.append(int(intervention_cfg["block_min"]))
    block_minutes = sorted({max(step_min, m) for m in block_minutes})

    stride_min = int(intervention_cfg.get("candidate_stride_min", settings.get("defaults", {}).get("candidate_stride_min", 30)))
    stride_min = max(step_min, stride_min)

    allowed_start, allowed_end = allowed_interval
    candidates: List[Dict[str, Any]] = []
    for block_min in block_minutes:
        block_delta = datetime.timedelta(minutes=block_min)
        start = _snap_up(allowed_start, step_min)
        while start + block_delta <= allowed_end:
            candidate: Dict[str, Any] = {
                "type": intervention,
                "start": start,
                "end": start + block_delta,
            }
            for key in ("channel", "lux", "dose_mg", "mets"):
                if key in intervention_cfg:
                    candidate[key] = intervention_cfg[key]
            candidates.append(candidate)
            start += datetime.timedelta(minutes=stride_min)
    return candidates


def score_waypoint(pred_cbtmin: datetime.datetime, target: datetime.datetime, tolerance_h: float, weight: float) -> float:
    error_h = abs(wrap_hours((pred_cbtmin - target).total_seconds() / 3600.0))
    if tolerance_h > 0 and error_h <= tolerance_h:
        return 0.0
    return max(0.0, (error_h - max(0.0, tolerance_h))) * weight


def _event_key(event: Dict[str, Any]) -> Tuple[Any, datetime.datetime, datetime.datetime]:
    return event.get("type"), event["start"], event["end"]


def pick_one_best_block(
    cbtmin_nominal: datetime.datetime,
    cbtmin_target: datetime.datetime,
    day_start: datetime.datetime,
    step_min: int,
    light: List[float],
    melatonin: List[float],
    exercise: List[float],
    allowed_intervals: Dict[str, List[Interval]],
    enabled_interventions: Sequence[str],
    used_minutes: Dict[str, float],
    selected_keys: set,
    settings: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], datetime.datetime, float, float]:
    defaults = settings.get("defaults", {})
    tolerance_h = float(defaults.get("waypoint_tolerance_h", 0.25))
    weight = float(defaults.get("waypoint_weight", 1.0))
    cost_weight = float(defaults.get("event_cost_weight", 0.0))

    current_delta_h = compute_phase_delta(cbtmin_nominal, day_start, step_min, light, melatonin, exercise, settings)
    current_pred = cbtmin_nominal + datetime.timedelta(hours=current_delta_h)
    current_loss = score_waypoint(current_pred, cbtmin_target, tolerance_h, weight)

    best_event: Optional[Dict[str, Any]] = None
    best_pred = current_pred
    best_loss = current_loss

    interventions_cfg = settings.get("interventions", {})
    for intervention in enabled_interventions:
        if intervention not in allowed_intervals:
            continue
        intervention_cfg = interventions_cfg.get(intervention, {})
        max_min_per_day = float(intervention_cfg.get("max_min_per_day", 0.0))
        already_used_min = used_minutes.get(intervention, 0.0)
        if max_min_per_day > 0 and already_used_min >= max_min_per_day:
            continue
        for allowed_interval in allowed_intervals[intervention]:
            candidates = propose_candidate_blocks(intervention, allowed_interval, step_min, settings)
            for candidate in candidates:
                candidate_key = _event_key(candidate)
                if candidate_key in selected_keys:
                    continue
                candidate_minutes = _interval_minutes((candidate["start"], candidate["end"]))
                if max_min_per_day > 0 and already_used_min + candidate_minutes > max_min_per_day:
                    continue

                light_tmp = light.copy()
                melatonin_tmp = melatonin.copy()
                exercise_tmp = exercise.copy()
                apply_events_to_arrays(light_tmp, melatonin_tmp, exercise_tmp, [candidate], day_start, step_min, settings)

                delta_h = compute_phase_delta(
                    cbtmin_nominal,
                    day_start,
                    step_min,
                    light_tmp,
                    melatonin_tmp,
                    exercise_tmp,
                    settings,
                )
                pred_cbtmin = cbtmin_nominal + datetime.timedelta(hours=delta_h)
                loss = score_waypoint(pred_cbtmin, cbtmin_target, tolerance_h, weight)
                if cost_weight > 0.0:
                    loss += cost_weight * (candidate_minutes / 60.0)
                if loss + 1e-9 < best_loss:
                    best_event = candidate
                    best_pred = pred_cbtmin
                    best_loss = loss

    return best_event, best_pred, best_loss, current_loss


def _window_offsets_for_mode(intervention_settings: Dict[str, Any], mode: str) -> Optional[Tuple[float, float]]:
    if mode == "advance":
        if "advance_window_h" in intervention_settings:
            start_h, end_h = intervention_settings["advance_window_h"]
        else:
            start_h = intervention_settings.get("advance_start_h")
            end_h = intervention_settings.get("advance_stop_h")
    else:
        if "delay_window_h" in intervention_settings:
            start_h, end_h = intervention_settings["delay_window_h"]
        else:
            start_h = intervention_settings.get("delay_start_h")
            end_h = intervention_settings.get("delay_stop_h")

    if start_h is None or end_h is None:
        return None
    start_h = float(start_h)
    end_h = float(end_h)
    if end_h < start_h:
        start_h, end_h = end_h, start_h
    return start_h, end_h


def _find_reference_time(
    intervention_settings: Dict[str, Any],
    cbtmin_nominal: datetime.datetime,
    rule_windows_processed: Sequence[Dict[str, Any]],
) -> Optional[datetime.datetime]:
    reference = intervention_settings.get("reference", "cbtmin")
    if reference == "cbtmin":
        return cbtmin_nominal
    if reference == "sleep":
        sleep_windows = [
            window for window in rule_windows_processed
            if window.get("type") == "sleep" and window["end"] <= cbtmin_nominal
        ]
        if not sleep_windows:
            return None
        return max(sleep_windows, key=lambda w: w["end"])["end"]
    return cbtmin_nominal


def _allowed_intervals_for_intervention(
    intervention: str,
    mode: str,
    cbtmin_nominal: datetime.datetime,
    day_start: datetime.datetime,
    day_end: datetime.datetime,
    rule_windows_processed: Sequence[Dict[str, Any]],
    settings: Dict[str, Any],
) -> List[Interval]:
    intervention_settings = settings.get("interventions", {}).get(intervention, {})
    reference_time = _find_reference_time(intervention_settings, cbtmin_nominal, rule_windows_processed)
    if reference_time is None:
        return []
    offsets = _window_offsets_for_mode(intervention_settings, mode)
    if offsets is None:
        return []

    start_h, end_h = offsets
    raw_interval = (
        reference_time + datetime.timedelta(hours=start_h),
        reference_time + datetime.timedelta(hours=end_h),
    )
    allowed = _intersect(raw_interval, (day_start, day_end))
    if allowed is None:
        return []

    blocked: List[Interval] = []
    for window in rule_windows_processed:
        blocked_interventions = window.get("blocked_interventions", [])
        if (
            intervention in blocked_interventions
            or "*" in blocked_interventions
            or "all" in blocked_interventions
        ):
            overlap = _intersect(allowed, (window["start"], window["end"]))
            if overlap is not None:
                blocked.append(overlap)

    return _subtract_intervals(allowed, blocked)


def plan_circadian(
    mode,  # advance or delay
    cbtmin_waypoints: List[datetime.datetime],
    enabled_interventions,  # melatonin, light, dark, exercise, ...
    rule_windows,  # datetime windows (UTC), can be repeatable
    fixed_events,  # datetime events (UTC) which are fixed
    settings,  # caps/limits, PRC models, snapping/search parameters, defaults
):
    if not cbtmin_waypoints:
        return {"cbtmin_entries": [], "events": [], "processed_rule_windows": []}

    defaults = settings.get("defaults", {})
    step_min = int(defaults.get("snap_step_min", 10))
    max_days = int(defaults.get("max_days", max(1, len(cbtmin_waypoints) - 1)))
    horizon_padding_days = int(defaults.get("horizon_padding_days", 2))
    max_blocks_per_day = int(defaults.get("max_blocks_per_day", 6))

    horizon_start = cbtmin_waypoints[0] - datetime.timedelta(days=1)
    horizon_end = cbtmin_waypoints[-1] + datetime.timedelta(days=horizon_padding_days)
    rule_windows_processed = expand_rule_windows(rule_windows, horizon_start, horizon_end)

    real_cbt_entries: List[datetime.datetime] = [cbtmin_waypoints[0]]
    planned_events: List[Dict[str, Any]] = []

    iteration_count = min(len(cbtmin_waypoints) - 1, max_days)
    for idx in range(1, iteration_count + 1):
        cbtmin_target = cbtmin_waypoints[idx]
        cbtmin_nominal = real_cbt_entries[-1] + datetime.timedelta(days=1)

        day_start = cbtmin_nominal - datetime.timedelta(days=1)
        day_end = cbtmin_nominal

        light, melatonin, exercise = build_baseline_arrays(
            day_start,
            day_end,
            step_min,
            rule_windows_processed,
            settings,
        )

        fixed_events_today: List[Dict[str, Any]] = []
        for event in fixed_events:
            event_start = event["start"]
            event_end = event.get("end")
            if event_end is None:
                duration_min = int(event.get("duration_min", step_min))
                event_end = event_start + datetime.timedelta(minutes=duration_min)
            if _intersect((event_start, event_end), (day_start, day_end)) is None:
                continue
            fixed_event = dict(event)
            fixed_event["end"] = event_end
            fixed_event["source"] = "fixed"
            fixed_events_today.append(fixed_event)
            planned_events.append(fixed_event)

        apply_events_to_arrays(light, melatonin, exercise, fixed_events_today, day_start, step_min, settings)

        allowed_intervals: Dict[str, List[Interval]] = {}
        for intervention in enabled_interventions:
            if intervention not in settings.get("interventions", {}):
                continue
            allowed = _allowed_intervals_for_intervention(
                intervention,
                mode,
                cbtmin_nominal,
                day_start,
                day_end,
                rule_windows_processed,
                settings,
            )
            if allowed:
                allowed_intervals[intervention] = allowed

        used_minutes: Dict[str, float] = {name: 0.0 for name in allowed_intervals}
        for event in fixed_events_today:
            event_type = event.get("type")
            if event_type not in used_minutes:
                continue
            used_minutes[event_type] += _interval_minutes((event["start"], event["end"]))

        selected_keys = {_event_key(event) for event in fixed_events_today if "type" in event}
        for _ in range(max_blocks_per_day):
            best_event, best_pred, best_loss, current_loss = pick_one_best_block(
                cbtmin_nominal=cbtmin_nominal,
                cbtmin_target=cbtmin_target,
                day_start=day_start,
                step_min=step_min,
                light=light,
                melatonin=melatonin,
                exercise=exercise,
                allowed_intervals=allowed_intervals,
                enabled_interventions=enabled_interventions,
                used_minutes=used_minutes,
                selected_keys=selected_keys,
                settings=settings,
            )
            if best_event is None or best_loss >= current_loss - 1e-6:
                break

            apply_events_to_arrays(light, melatonin, exercise, [best_event], day_start, step_min, settings)
            selected_keys.add(_event_key(best_event))
            best_event["source"] = "planned"
            planned_events.append(best_event)
            used_minutes[best_event["type"]] = used_minutes.get(best_event["type"], 0.0) + _interval_minutes(
                (best_event["start"], best_event["end"])
            )

            tolerance_h = float(defaults.get("waypoint_tolerance_h", 0.25))
            weight = float(defaults.get("waypoint_weight", 1.0))
            if score_waypoint(best_pred, cbtmin_target, tolerance_h, weight) <= 0.0:
                break

        delta_h = compute_phase_delta(cbtmin_nominal, day_start, step_min, light, melatonin, exercise, settings)
        real_cbt_entries.append(cbtmin_nominal + datetime.timedelta(hours=delta_h))

    return {
        "cbtmin_entries": real_cbt_entries,
        "events": planned_events,
        "processed_rule_windows": rule_windows_processed,
    }


            










