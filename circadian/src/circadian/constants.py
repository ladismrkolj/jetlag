"""Package-wide default constants."""

from __future__ import annotations

DEFAULT_TAU_HOURS = 24.2
"""Population-average intrinsic circadian period. Czeisler CA, et al. 'Stability,
precision, and near-24-hour period of the human circadian pacemaker.'
Science. 1999;284(5423):2177-2181."""

DEFAULT_STEP_HOURS = 0.1
"""Default RK4 step size (6 minutes). Small relative to the oscillator's own ~24h
timescale on purpose: it exists to resolve drive-signal transitions (e.g. a light
pulse turning on/off), not the oscillator's own dynamics. See
docs/circadian-model.md, 'Numeric methods'."""

HOURS_PER_DAY = 24.0

CBTMIN_BEFORE_WAKE_HOURS = 3.0
"""Heuristic offset used to estimate CBTmin from a habitual wake time (CBTmin is
typically ~2-3h before habitual wake). Matches the existing app's `sleepEnd - 3h`
(app/lib/jetlag.ts) for continuity."""
