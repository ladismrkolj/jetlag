from typing import Dict, Callable
import numpy as np


def K_light(h: np.ndarray) -> np.ndarray:
    """
    Dead-simple linear PRC: 1 hour of stimulus = ±1 hour shift.
    h = hours since CBTmin in [0,24).
    - [0, 12): advance region (K = -1)
    - [12, 24): delay region (K = +1)
    """
    result = np.ones_like(h, dtype=np.float32)
    result[h < 12.0] = -1.0
    return result


def cbtmin_next_from_stimuli(
    cbtmin_ref: float,
    stim: Dict[str, np.ndarray],                          # channel -> array length N; "timepoints" -> float array (hours mod 24)
    K: Dict[str, Callable[[np.ndarray], np.ndarray]],     # channel -> PRC K(h) vectorized
    drift_h: float = 0.0,                                 # tau - 24 (hours/day)
    max_advance_h: float = 1.5,                            # cap magnitude (advance is negative)
    max_delay_h: float = 1.5,                              # cap magnitude
) -> float:
    """
    Minimal PRC integrator on a uniform 24h grid ending at cbtmin_ref.

    Conventions:
      - cbtmin_ref: CBT minimum phase (hours mod 24, e.g., 4.0 for 04:00)
      - Integration window: [cbtmin_ref - 24h, cbtmin_ref) mod 24
      - Phase h: hours since CBTmin in [0,24)
      - delta_h < 0 advances CBTmin; delta_h > 0 delays CBTmin
      - stim arrays are assumed to already be "effective stimulus" (post-transform).
      - stim dict must include "timepoints" key with array of floats (hours mod 24) for each sample.
    """
    # Extract timepoints and compute dt_h array from intervals
    timepoints = stim["timepoints"]
    N = len(timepoints)
    if isinstance(timepoints, list):
        timepoints = np.array(timepoints, dtype=np.float32)
    
    # Compute time step for each sample
    if N > 1:
        dt_h_array = np.diff(timepoints, n=1).astype(np.float32)  # N-1 intervals
        # Pad to N elements by repeating the last interval
        dt_h_array = np.append(dt_h_array, dt_h_array[-1])
    else:
        raise ValueError("stim must have at least 2 timepoints")

    # Phase relative to cbtmin_ref: h = (timepoint - cbtmin_ref) mod 24
    # h in [0, 24): 0 = at CBTmin, increases forward through the day
    h = np.mod(timepoints - cbtmin_ref, 24.0).astype(np.float32)

    delta_h = float(drift_h)

    for ch, u in stim.items():
        if ch == "timepoints" or ch not in K:
            continue
        if u.shape[0] != N:
            raise ValueError(f"stim[{ch}] length {u.shape[0]} != N={N}")
        delta_h += float(np.sum(K[ch](h) * u * dt_h_array, dtype=np.float64))

    # Cap daily shift
    delta_h = max(-max_advance_h, min(delta_h, max_delay_h))

    return np.mod(cbtmin_ref + delta_h, 24.0)


if __name__ == "__main__":
    # --- Example: CBTmin at 04:00, add 1h bright light 06:00-07:00 (should ADVANCE) ---
    dt_h = 10 / 60.0  # 10 minutes in hours
    N = int(24 / dt_h)

    cbtmin_ref = 4.0  # CBTmin at 04:00 (hours mod 24)

    # Build timepoints array (hours mod 24) and stimulus data
    # Window: 24 hours before cbtmin_ref, ending just before cbtmin_ref
    timepoints = [np.mod(cbtmin_ref - 24.0 + i * dt_h, 24.0) for i in range(N)]
    stim = {"timepoints": timepoints, "light": np.zeros(N, dtype=np.float32)}

    # Put unit "effective light stimulus" from 06:00 to 07:00
    for i in range(N):
        t_hour = timepoints[i]
        if 6.0 <= t_hour < 7.0:
            stim["light"][i] = 1.0

    K = {"light": K_light}

    cbtmin_next = cbtmin_next_from_stimuli(
        cbtmin_ref=cbtmin_ref,
        stim=stim,
        K=K,
        drift_h=0.0,
        max_advance_h=1.5,
        max_delay_h=1.5,
    )

    shift_h = cbtmin_next - cbtmin_ref
    # Handle wrap-around: if advance is large (>12h), account for mod 24
    if shift_h > 12.0:
        shift_h = shift_h - 24.0
    elif shift_h < -12.0:
        shift_h = shift_h + 24.0
    shift_min = shift_h * 60.0

    print(f"CBTmin ref:  {cbtmin_ref:.2f}h")
    print(f"CBTmin next: {cbtmin_next:.2f}h")
    print(f"Shift (min): {shift_min:.1f}")

    # --- Quick sanity: move light to 22:00-23:00 (should DELAY) ---
    stim2 = {"timepoints": timepoints, "light": np.zeros(N, dtype=np.float32)}
    for i in range(N):
        t_hour = timepoints[i]
        if 22.0 <= t_hour < 23.0:
            stim2["light"][i] = 1.0

    cbtmin_next2 = cbtmin_next_from_stimuli(cbtmin_ref, stim2, K)
    shift_h2 = cbtmin_next2 - cbtmin_ref
    if shift_h2 > 12.0:
        shift_h2 = shift_h2 - 24.0
    elif shift_h2 < -12.0:
        shift_h2 = shift_h2 + 24.0
    shift_min2 = shift_h2 * 60.0

    print("\nSanity check (light 22:00-23:00):")
    print(f"CBTmin next: {cbtmin_next2:.2f}h")
    print(f"Shift (min): {shift_min2:.1f}")
