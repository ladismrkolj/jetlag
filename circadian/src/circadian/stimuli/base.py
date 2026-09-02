"""The StimulusModule plugin contract -- the concrete answer to "every outside
influence is a function you add to the base oscillator equation."

Adding a new influence to the engine means writing one module that implements
`StimulusModule` and registering an instance of it in `registry.default_registry()`.
Nothing in `tier1/oscillator.py`, `tier1/integrate.py`, or `tier1/analytic.py` needs
to change. See `stimuli/_template.py` for a documented starting point.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar

from circadian.types import PhaseHours

TParams = TypeVar("TParams")

_VALID_CONFIDENCE = ("high", "medium", "low")


@dataclass(frozen=True)
class Citation:
    authors: str
    year: int
    title: str
    url: str | None = None


@dataclass(frozen=True)
class StimulusMetadata:
    id: str
    label: str
    citations: tuple[Citation, ...]
    confidence: str
    """'high' | 'medium' | 'low'. See docs/circadian-model.md's module reference
    table for what each level means and why (e.g. light/melatonin are 'high' on
    direct human PRC studies; meal timing is 'low' -- decent evidence for
    peripheral clocks, weak for the central pacemaker specifically)."""
    notes: str = ""
    """Must record which phase marker the source PRC was reported against (e.g.
    CBTmin vs. DLMO vs. habitual sleep onset) and how it was translated to this
    package's theta=0-at-CBTmin convention -- silently treating different papers'
    reference points as interchangeable is a real, common calibration bug."""

    def __post_init__(self) -> None:
        if self.confidence not in _VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {_VALID_CONFIDENCE}, got {self.confidence!r}"
            )


@dataclass(frozen=True)
class PulseEvent:
    t: datetime
    strength: float


class StimulusModule(Protocol[TParams]):
    """The plugin interface every stimulus (light, melatonin, exercise, ...)
    implements. `TParams` is that module's own parameter type -- e.g. light's
    might be a lux-over-time schedule, melatonin's a list of doses."""

    meta: StimulusMetadata
    default_params: TParams

    def drive(self, t: datetime, params: TParams) -> float:
        """Normalized instantaneous stimulus intensity at `t`: 0 = none, 1 = this
        module's reference intensity (whatever intensity its cited PRC was
        measured at). A pure function of time -- multi-day schedules are baked
        into `params` beforehand, not threaded through some separate mechanism.
        """
        ...

    def sensitivity(self, theta: PhaseHours) -> float:
        """Z_i(theta): phase sensitivity as a pure function of CURRENT PHASE
        ONLY (not calendar time, not what other modules are doing -- the
        defining assumption of the weak-coupling/phase-reduction approximation).
        Units: hours-of-phase-shift per hour-of-real-time at unit drive. Positive
        means phase ADVANCE.
        """
        ...

    def as_pulses(self, params: TParams) -> list[PulseEvent] | None:
        """Optional fast-path hint for the analytic integrator (tier1/analytic.py):
        if `params` reduces to discrete, non-overlapping, effectively-instantaneous
        pulses, return them; otherwise return None. Returning None for ANY enabled
        module in a registry disqualifies the WHOLE simulation from the analytic
        path -- the caller falls back to RK4. Continuous drives (e.g. imposed
        sleep/wake masking) should always return None here.
        """
        ...


@dataclass
class ActiveStimulus(Generic[TParams]):
    """A stimulus module wired up with a concrete set of parameters for one
    simulation, and whether it's switched on."""

    module: StimulusModule[TParams]
    params: TParams
    enabled: bool = True


StimulusRegistry = list["ActiveStimulus[Any]"]
"""A list of independently-configured, independently-typed active stimuli. The
`Any` here is explicit (not an omitted type parameter) because the whole point of
the registry is to hold heterogeneous modules -- light's params and melatonin's
params are different types, and nothing outside a given module ever needs to know
either type; only `drive`/`sensitivity`/`as_pulses` (called generically via the
Protocol) touch `params`."""
