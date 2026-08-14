# circadian

A from-scratch circadian rhythm phase-shift engine.

## What this is

The existing app (`app/lib/jetlag.ts`, in the repo root's Next.js frontend) models jet
lag with a single heuristic scalar ("CBTmin") that gets walked forward by a hand-tuned,
capped daily shift, gated by fixed clock-hour windows for exactly three interventions
(light, melatonin, exercise). This package is a different, more general approach: a
real oscillator with one small base equation, where every outside influence — light,
melatonin, exercise, meals, an imposed sleep/wake schedule, temperature, or anything
added later — is a term summed into that equation, not a hardcoded special case. It
also generalizes past a single origin→destination trip to an arbitrary sequence of
schedule segments, which covers multi-leg trips and non-travel scenarios like preparing
a worker for a night shift.

See [`docs/circadian-model.md`](docs/circadian-model.md) for the full math, citations,
and a guide to adding a new stimulus module.

## Relationship to the rest of the repo

This package is **standalone**: it is not imported by, and does not import, anything
under `app/`. It is not wired into the Next.js app or its API routes, and it is not a
backend service — there is deliberately no revival of the Python backend that this
repo removed in favor of a pure-frontend jet lag calculator (see the repo root
`README.md`). This is a research/library artifact for modeling circadian phase shifts
in general, of which jet lag is one example scenario.

## Setup

```bash
cd circadian
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -e ".[dev]"
```

## Running the checks

```bash
pytest              # test suite
mypy src/           # strict type checking
ruff check .         # lint
```

## Trying it out

```bash
python examples/single_trip.py
python examples/multi_leg_trip.py
python examples/night_shift_prep.py
```

Each prints a summary of the simulated phase trajectory. Install the `plot` extra
(`pip install -e ".[dev,plot]"`) to also render a chart via `scripts/plot_trajectory.py`.
