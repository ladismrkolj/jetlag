import datetime
from typing import Dict, Callable
import numpy as np


def K_light(h: np.ndarray) -> np.ndarray:
    """
    Simple, physiological-looking light PRC.
    h = hours since CBTmin in [0,24).
    Positive => delay contribution, Negative => advance contribution.
    """
    delay = 0.08 * np.exp(-0.5 * ((h - 18.0) / 3.0) ** 2)      # evening/night delay lobe
    advance = 0.10 * np.exp(-0.5 * ((h - 3.5) / 2.5) ** 2)     # morning advance lobe
    return delay - advance


def cbtmin_next_from_stimuli(
    cbtmin_ref: datetime.datetime,
    stim: Dict[str, np.ndarray],                          # channel -> array length N
    K: Dict[str, Callable[[np.ndarray], np.ndarray]],     # channel -> PRC K(h) vectorized
    dt_min: int,
    drift_h: float = 0.0,                                 # tau - 24 (hours/day)
    max_advance_h: float = 1.5,                            # cap magnitude (advance is negative)
    max_delay_h: float = 1.5,                              # cap magnitude
) -> datetime.datetime:
    """
    Minimal PRC integrator on a uniform 24h grid ending at cbtmin_ref.

    Conventions:
      - Integration window: [cbtmin_ref - 24h, cbtmin_ref)
      - Phase h: hours since CBTmin in [0,24)
      - delta_h < 0 advances CBTmin; delta_h > 0 delays CBTmin
      - stim arrays are assumed to already be "effective stimulus" (post-transform).
    """
    dt_h = dt_min / 60.0

    any_arr = next(iter(stim.values()))
    N = int(any_arr.shape[0])

    # Phase grid for the 24h window ending at CBTmin (last sample just before CBTmin)
    offsets_h = (-24.0 + dt_h * np.arange(N, dtype=np.float32))
    h = np.mod(offsets_h, 24.0).astype(np.float32)

    delta_h = float(drift_h)

    for ch, u in stim.items():
        if ch not in K:
            continue
        if u.shape[0] != N:
            raise ValueError(f"stim[{ch}] length {u.shape[0]} != N={N}")
        delta_h += float(np.sum(K[ch](h) * u, dtype=np.float64) * dt_h)

    # Cap daily shift
    delta_h = max(-max_advance_h, min(delta_h, max_delay_h))

    return cbtmin_ref + datetime.timedelta(hours=delta_h)


if __name__ == "__main__":
    # --- Example: CBTmin today at 04:00 UTC, add 1h bright light 06:00-07:00 (should ADVANCE) ---
    dt_min = 10
    N = int(24 * 60 / dt_min)

    cbtmin_today = datetime.datetime(2026, 2, 14, 4, 0)
    t0 = cbtmin_today - datetime.timedelta(hours=24)

    stim = {"light": np.zeros(N, dtype=np.float32)}

    # Put unit "effective light stimulus" from 06:00 to 07:00 on the absolute clock
    for i in range(N):
        t = t0 + datetime.timedelta(minutes=i * dt_min)
        if datetime.time(6, 0) <= t.time() < datetime.time(7, 0):
            stim["light"][i] = 1.0

    K = {"light": K_light}

    cbtmin_next = cbtmin_next_from_stimuli(
        cbtmin_ref=cbtmin_today,
        stim=stim,
        K=K,
        dt_min=dt_min,
        drift_h=0.0,
        max_advance_h=1.5,
        max_delay_h=1.5,
    )

    shift_min = (cbtmin_next - cbtmin_today).total_seconds() / 60.0

    print("CBTmin today:", cbtmin_today)
    print("CBTmin next :", cbtmin_next)
    print("Shift (min) :", shift_min)

    # --- Quick sanity: move light to 22:00-23:00 (should DELAY) ---
    stim2 = {"light": np.zeros(N, dtype=np.float32)}
    for i in range(N):
        t = t0 + datetime.timedelta(minutes=i * dt_min)
        if datetime.time(22, 0) <= t.time() < datetime.time(23, 0):
            stim2["light"][i] = 1.0

    cbtmin_next2 = cbtmin_next_from_stimuli(cbtmin_today, stim2, K, dt_min)
    shift_min2 = (cbtmin_next2 - cbtmin_today).total_seconds() / 60.0

    print("\nSanity check (light 22:00-23:00):")
    print("CBTmin next :", cbtmin_next2)
    print("Shift (min) :", shift_min2)
