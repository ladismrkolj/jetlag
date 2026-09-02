# A Modular Additive-Forcing Model of Human Circadian Phase

**Technical whitepaper — `circadian` package**
Version 0.1 · Status: design reference for implementation

---

## Abstract

This document specifies the numerical algorithm used by the `circadian` package to
predict human circadian phase under arbitrary sequences of light exposure, drug
administration, behaviour and schedule change. The model is built on one equation —

$$\frac{d\theta}{dt} \;=\; \omega \;+\; \sum_i Z_i(\theta)\,p_i(t)$$

— in which the unforced clock is a single term and **every external influence is an
additive term summed onto it**. This is not a convenience abstraction: it is the
first-order phase reduction of a weakly perturbed limit-cycle oscillator, the standard
construction in the field. We give the derivation and, importantly, the conditions
under which it fails; for those cases we specify a second tier built on the published
Kronauer-lineage limit-cycle models, reproduced here in full with their exact
coefficients.

We then enumerate every factor the model admits, with the measured values and
equations taken from the primary literature: the irradiance–response function for
light, phase response curves (PRCs) for light at two durations, exogenous melatonin at
two doses, and exercise; the non-photic drive of the sleep–wake cycle; and the
evidence status of caffeine, meal timing and ambient temperature. We give the explicit
algorithm for converting a published PRC — which is reported as a *total shift from a
finite stimulus, against a study-specific phase marker* — into the infinitesimal
sensitivity function $Z_i(\theta)$ the model actually needs, and we quantify the two
systematic errors that step introduces.

> **Sources.** Except where explicitly flagged, every numeric value in this document is
> taken from a primary publication located via **PubMed**, and each is cited inline with
> a DOI link. Values that could not be verified against a primary source are marked
> **[UNVERIFIED]** and must be checked before use.

---

## 1. Scope and design goals

The model is required to answer questions of the form *"given what this person does
and when, where will their body clock be on day N?"* across scenarios that include but
are not limited to jet lag:

| Scenario | Representation |
|---|---|
| Single transmeridian trip | two schedule segments, different timezones |
| Multi-leg itinerary | N segments, N timezones |
| Night-shift preparation | N segments, **one** timezone, moving sleep window |
| Gradual chronotype change | N segments, one timezone, incrementally shifted schedule |
| Free-running / no schedule | one segment, no imposed sleep window |

Four design constraints follow from this:

1. **No privileged scenario.** There is no "origin"/"destination" concept in the model.
   A trip is a special case of a schedule timeline, not the other way round.
2. **Influences are additive and pluggable.** Adding meal timing, or a new drug, must
   not require modifying the oscillator, the integrator, or any existing influence.
3. **Analytic where possible, numeric where not.** Closed-form evaluation is used where
   the mathematics permits it exactly; numerical integration is the general fallback,
   not the default.
4. **Every constant is traceable.** Each influence carries its citation, its confidence
   level, and — critically — a record of which phase marker its source study used.

---

## 2. Notation, phase conventions, and the marker problem

| Symbol | Meaning | Units |
|---|---|---|
| $\theta$ | circadian phase, wrapped to $[0,24)$ | h |
| $\tau$ | intrinsic (free-running) period | h |
| $\omega = 24/\tau$ | angular rate | h phase / h real |
| $Z_i(\theta)$ | phase sensitivity (infinitesimal PRC) of influence $i$ | h shift / h real, at unit drive |
| $p_i(t)$ | normalised drive of influence $i$; $0$ = absent, $1$ = reference intensity | dimensionless |
| $I$ | photopic illuminance | lux |

**Phase zero is the estimated core body temperature minimum (CBTmin).** A positive
$Z_i p_i$ product means a **phase advance**.

### 2.1 The marker problem

Published PRCs are *not* reported against a common reference. Khalsa et al. report
against CBTmin; Burgess et al. report against dim-light melatonin onset (DLMO) and
against sleep midpoint; Youngstedt et al. report against **clock time**. These are not
interchangeable, and silently treating them as such is a first-order source of error —
DLMO and CBTmin are roughly seven hours apart, so a mis-conversion moves a PRC peak by
a quarter of the cycle.

The package therefore requires every module to record its source marker and the
conversion applied. The conversion used throughout is:

$$\theta_{\text{CBTmin}} = \theta_{\text{DLMO}} + \Delta_{\text{DLMO}\to\text{CBTmin}},
\qquad \Delta_{\text{DLMO}\to\text{CBTmin}} \approx 7\ \text{h}$$

**Worked check.** Burgess et al. (2008) place the 3 mg melatonin advance peak ~5 h
*before* DLMO and the delay peak ~11 h *after* DLMO
([DOI](https://doi.org/10.1113/jphysiol.2007.143180)). Converting:

- advance peak: $-5 - 7 = -12$ h relative to CBTmin
- delay peak: $+11 - 7 = +4$ h relative to CBTmin

The shipped Next.js heuristic in this same repository (`app/lib/jetlag.ts`) uses
`melatonin_advance = -11.5` and `melatonin_delay = +4` relative to CBTmin. The delay
constant reproduces exactly; the advance constant lands within 0.5 h. This is a useful
consistency check on both the conversion offset and the existing app's constants, and
it is the reason the conversion is made explicit rather than folded silently into a
fitted curve.

> $\Delta_{\text{DLMO}\to\text{CBTmin}} \approx 7$ h is the value used by the
> open-source Arcascope `circadian` reference implementation (`cbt_to_dlmo: 7.0`).
> It is a population approximation with real inter-individual spread. **[PARTIALLY
> VERIFIED — widely used, but the ±spread should be sourced before clinical use.]**

---

## 3. The core equation (Tier 1)

### 3.1 Statement

$$\boxed{\;\frac{d\theta}{dt} \;=\; \underbrace{\omega}_{\text{base}} \;+\; \underbrace{\sum_i Z_i(\theta)\,p_i(t)}_{\text{one term per influence}}\;}$$

With no influences registered, $d\theta/dt = \omega = 24/\tau$ and the oscillator
free-runs: phase drifts against local clock time at $(24/\tau - 1)$ hours per 24 h. At
$\tau = 24.2$ h this is $-11.9$ min/day — the clock runs late, which is the classic
temporal-isolation result.

### 3.2 Why the terms add

Take any self-sustained oscillator $\dot{\mathbf{x}} = \mathbf{F}(\mathbf{x})$ with a
stable limit cycle of period $\tau$. Define the asymptotic phase $\theta(\mathbf{x})$ on
the basin of attraction. Under a weak perturbation $\varepsilon\mathbf{q}(t)$,

$$\dot{\mathbf{x}} = \mathbf{F}(\mathbf{x}) + \varepsilon\,\mathbf{q}(t)
\;\Longrightarrow\;
\dot\theta = \omega + \varepsilon\,\mathbf{Z}(\theta)\cdot\mathbf{q}(t) + O(\varepsilon^2)$$

where $\mathbf{Z}(\theta) = \nabla_{\mathbf{x}}\theta |_{\text{limit cycle}}$ is the
infinitesimal phase response curve, obtainable as the periodic solution of the adjoint
variational equation $\dot{\mathbf{Z}} = -D\mathbf{F}^\top \mathbf{Z}$ normalised by
$\mathbf{Z}\cdot\mathbf{F} = \omega$ (Malkin's theorem; the standard construction in
Winfree/Kuramoto phase-reduction theory).

Two consequences matter here:

- **Additivity is a theorem, not a modelling choice.** To first order in $\varepsilon$,
  independent perturbations superpose. This is precisely what licenses "one term per
  influence, summed".
- **It is first order only.** Everything below is $O(\varepsilon^2)$ error, and
  $\varepsilon$ is not small for bright light.

### 3.3 Where it breaks

The reduction discards amplitude. A sufficiently strong, well-timed stimulus does not
merely translate the oscillator along its cycle — it drives the state toward the
singularity, collapsing amplitude and producing **Type 0** resetting. Czeisler et al.
(1989) demonstrated exactly this in humans with bright light
([DOI](https://doi.org/10.1126/science.2734611)). A phase-only model *structurally
cannot* represent it: there is no amplitude variable to suppress.

Empirically, the stimuli in §6 at their *tested* intensities produce Type **1**
(weak) resetting — Khalsa et al. (2003) and St Hilaire et al. (2012) both fit Type 1
curves — so Tier 1 is defensible in the tested regime. Outside it (multi-hour very
bright light near the singularity; several strong stimuli coinciding), Tier 2 (§7) is
required.

**Practical rule used by the package:** Tier 1 is the default; Tier 2 is the reference
model used to *derive* and *validate* $Z_i$, and the fallback for strong or coincident
stimuli.

---

## 4. Numerical algorithms

### 4.1 Fixed-step RK4 (general path)

State is the single unwrapped scalar $\theta$. One step of classical RK4:

$$
k_1 = f(\theta, t),\quad
k_2 = f(\theta + \tfrac{h}{2}k_1,\, t + \tfrac{h}{2}),\quad
k_3 = f(\theta + \tfrac{h}{2}k_2,\, t + \tfrac{h}{2}),\quad
k_4 = f(\theta + h k_3,\, t + h)
$$

$$\theta_{n+1} = \theta_n + \tfrac{h}{6}(k_1 + 2k_2 + 2k_3 + k_4)$$

with $f(\theta,t) = \omega + \sum_i Z_i(\mathrm{wrap}_{24}(\theta))\,p_i(t)$.

Two implementation points:

- $\theta$ is integrated **unwrapped**; it is wrapped to $[0,24)$ only when passed into
  a $Z_i$ (which is periodic and defined on that domain) and when reporting. Wrapping
  the integration state would corrupt the RK4 stages across cycle boundaries.
- Net phase shift is reported relative to free-running drift:
  $\Delta\phi = (\theta_{\text{end}} - \theta_{\text{start}}) - \omega T$. This isolates
  the effect of the influences from the passage of time, which is what "your clock
  shifted by X hours" conventionally means.

### 4.2 Step size

Default $h = 0.1$ h (6 min). The binding constraint is **not** the oscillator (24 h
timescale) but the drive signals: a light onset or a melatonin absorption ramp evolves
over ~0.5–1 h, so $h \lesssim (\text{fastest drive ramp})/5$. Cost is negligible — a
10-day simulation is ~2400 steps of a scalar ODE. Global error is $O(h^4)$; the test
suite asserts the empirical convergence ratio on halving $h$ is ≈16.

### 4.3 Exact analytic path (pulse-reducible schedules)

When every enabled influence reduces to discrete, non-overlapping, effectively
instantaneous pulses, the ODE is solvable in closed form and no integration is needed.
Between pulses the dynamics are linear ($\dot\theta = \omega$); at each pulse the phase
jumps by the PRC value evaluated at the phase of arrival:

```
sort pulses by time
θ ← θ₀
for each pulse (t_k, s_k) with owning module m:
    θ ← θ + ω·(t_k − t_{k−1})        # exact coast, no truncation error
    θ ← θ + m.sensitivity(wrap24(θ))·s_k   # instantaneous kick
θ_end ← θ + ω·(T − t_last)
```

This is $O(\text{number of pulses})$ rather than $O(T/h)$ and is **exact** on the coast
segments. Its practical role is twofold: fast "what if I take melatonin at 22:00"
queries, and as a **cross-validation oracle** — the test suite asserts the RK4 path
converges to the analytic answer as $h\to0$ for any schedule where both are legal.

Note that realistic full simulations rarely qualify: an imposed sleep/wake schedule
produces a continuous masking drive, which disqualifies the analytic path. This is
expected and correct — the analytic path is an exact special case, not the common one.

### 4.4 Time representation and DST

All times are timezone-aware `datetime` objects; local wall-clock time is resolved per
instant through the IANA database (`zoneinfo`), never through a cached numeric UTC
offset. A schedule segment crossing a daylight-saving transition therefore resolves
correctly on both sides automatically. (The heuristic model shipped in this repo's
Next.js app computes one fixed offset per timezone and reuses it for the whole trip;
that model is an hour wrong for every day after a transition.)

---

## 5. The schedule timeline

The only scenario primitive is an ordered list of segments:

```python
ScheduleSegment(
    start:              datetime,                    # tz-aware
    sleep_window_local: tuple[time, time] | None,     # None ⇒ free-running
    tz:                 str | None,                   # IANA name; None ⇒ unchanged
    label:              str,
)
ScheduleTimeline = list[ScheduleSegment]
```

`tz=None` meaning "unchanged from the previous segment" is what makes the same
structure express both a multi-timezone itinerary and a same-timezone night-shift
rotation without special-casing either. Initial phase is estimated from whichever
segment is *active* at simulation start (CBTmin ≈ wake − 3 h), not from a hardcoded
"origin".

> **A note on why this generality is not merely cosmetic.** Diekman & Bose (2017) show
> that the change in **daylength** encountered during **north–south** travel can cause
> jet lag *even when no time zones are crossed*
> ([DOI](https://doi.org/10.1016/j.jtbi.2017.10.002)). A model whose input is "hours of
> timezone difference" cannot express that scenario at all; a model whose input is a
> timeline of light and schedule can.

---

## 6. Factors: measured values and equations

### 6.0 Summary table

| Influence | Source study | Stimulus | Reported effect | Confidence |
|---|---|---|---|---|
| Light | Khalsa 2003 | 6.7 h, ~10 000 lx | PRC peak-to-trough **5.02 h** | High |
| Light | St Hilaire 2012 | 1 h, ~8000 lx | PRC peak-to-trough **2.20 h** | High |
| Light (dose) | Zeitzer 2000 | 6.5 h, varied | half-max delay at **~100 lx** | High |
| Melatonin | Burgess 2008 | 3.0 mg ×3 d | max adv **1.8 h**, max delay **1.3 h** | High |
| Melatonin | Burgess 2010 | 0.5 mg ×3 d | similar magnitude, later optimum | High |
| Exercise | Youngstedt 2019 | 1 h moderate ×3 d | amplitude ≈ bright light of equal duration | Medium |
| Sleep–wake (non-photic) | St Hilaire 2007 | behavioural | acts independently and with light | Medium |
| Caffeine | Burke 2015 | ~200 mg, bedtime−3 h | **~40 min delay** (single timing) | Low |
| Meal timing | — | — | peripheral clocks; central effect unclear | Low |
| Ambient temperature | — | — | weak in humans | Low / stub |

### 6.1 Light

**Irradiance response.** Zeitzer et al. (2000) established that both phase resetting
and acute melatonin suppression follow a **logistic** (not linear, not log-linear)
dose–response, and — the headline result — that **half of the maximal phase-delaying
response to ~9000 lx is obtained at just over 1% of that intensity, i.e. ordinary room
light of ~100 lx** ([DOI](https://doi.org/10.1111/j.1469-7793.2000.00695.x)). n = 23,
6.5 h exposure in the early biological night.

The operational consequence is large: modelling indoor light as "not bright light,
therefore negligible" is wrong by roughly a factor of two at the half-max point. The
Kronauer-lineage models encode this saturation in Process L (§7).

Two functional forms appear in the literature:

$$\alpha(I) = \alpha_0\left(\frac{I}{I_0}\right)^{p} \quad\text{(Jewett99 / Forger99: unbounded power law)}$$

$$\alpha(I) = \alpha_0\,\frac{I^{p}}{I^{p} + I_0} \quad\text{(Hannay19: saturating Hill form)}$$

The Hill form is the better-behaved choice for a stimulus module because it saturates;
the power law does not and must be used only within its fitted range.

**Phase response.** Two PRCs from the same laboratory under comparable conditions:

| Duration | Intensity | Fitted peak-to-trough | Type | Source |
|---|---|---|---|---|
| 6.7 h | ~10 000 lx fixed / 5000–9000 lx free gaze | **5.02 h** | 1 | Khalsa 2003 ([DOI](https://doi.org/10.1113/jphysiol.2003.040477)) |
| 1 h | ~8000 lx | **2.20 h** | 1 | St Hilaire 2012 ([DOI](https://doi.org/10.1113/jphysiol.2012.227892)) |

Shape: phase **delays** when the stimulus is centred *before* CBTmin, **advances**
when centred *after*, with the crossover at CBTmin. A `<3 lux` dim-light control
produced no discernible PRC.

> **Correction to a common simplification.** Khalsa et al. explicitly report that
> **"no prolonged 'dead zone' of photic insensitivity was apparent"** during the
> subjective day. The flat mid-day dead zone that appears in many popular
> summaries (and in schematic PRC figures) is not supported by this dataset. The
> light module's $Z(\theta)$ should therefore be *reduced* but **not zeroed** across
> the subjective day.

**The duration nonlinearity — and why it matters for calibration.** The 1 h PRC
amplitude is ~40% of the 6.7 h amplitude despite delivering only ~15% of the exposure
duration. Response is therefore strongly sublinear in duration. Expressed as an
implied per-hour sensitivity at the PRC peak:

$$Z_{\text{6.7h}} \approx \frac{5.02/2}{6.7} \approx 0.37\ \text{h/h},
\qquad
Z_{\text{1h}} \approx \frac{2.20/2}{1} \approx 1.10\ \text{h/h}$$

A threefold discrepancy. **This means a single duration-independent $Z_{\text{light}}$
does not exist**, and any implementation that fits $Z$ from one PRC and applies it to
arbitrary exposure durations will be wrong — over-predicting long exposures if fitted
on 1 h data, under-predicting short ones if fitted on 6.7 h data. §8 specifies the
correction.

### 6.2 Exogenous melatonin

| Dose | Advance peak | Delay peak | Max advance | Max delay | Source |
|---|---|---|---|---|---|
| 3.0 mg | ~5 h before DLMO (≈ CBTmin − 12 h) | ~11 h after DLMO (≈ CBTmin + 4 h) | **1.8 h** | **1.3 h** | Burgess 2008 ([DOI](https://doi.org/10.1113/jphysiol.2007.143180)) |
| 0.5 mg | 2–4 h before DLMO (9–11 h before sleep midpoint) | shortly after wake | comparable | comparable | Burgess 2010 ([DOI](https://doi.org/10.1210/jc.2009-2590)) |

Both PRCs come from the same three-day ultradian protocol with placebo subtraction
(n = 27 and n = 34 respectively). Key findings the module encodes:

- The melatonin PRC is roughly **antiphase to the light PRC** — its advance region sits
  in the afternoon, where light's does not.
- There is a **dead zone during the first half of habitual sleep**: taking melatonin as
  a hypnotic at bedtime has minimal phase-shifting effect. (Burgess et al. state this
  explicitly.)
- **Dose changes the optimal timing, not primarily the magnitude.** The optimum is
  *later* for the lower dose; given at their respective optima, 0.5 mg and 3.0 mg
  produce similarly sized shifts. A dose parameter must therefore shift the curve, not
  merely scale it — a scaling-only implementation is qualitatively wrong.

### 6.3 Exercise

Youngstedt et al. (2019) produced the first well-powered human exercise PRCs (n = 99:
51 older, 48 young; 1 h moderate treadmill at 65–75% heart-rate reserve, three
consecutive days, eight times of day, 90-min ultrashort sleep–wake protocol, aMT6s
phase markers) ([DOI](https://doi.org/10.1113/JP276943)).

| Clock time | Effect |
|---|---|
| 07:00 | phase **advance** (peak) |
| 13:00–16:00 | phase **advance** (second peak — novel finding) |
| 16:00 | minimal |
| 19:00–22:00 | phase **delay** (peak) |
| 02:00 | minimal |

Two findings materially affect the model:

1. **The exercise PRC is bimodal in its advance region** (morning *and* afternoon),
   unlike light. The afternoon advance region is a novel result of this study.
2. **Amplitudes are "comparable to expectations for bright light of equal duration."**
   Exercise is not a negligible perturbation, and should not be modelled as a token
   effect. No significant age or sex differences were found.

⚠️ **Conversion caveat.** These are reported in **clock time**, not against CBTmin. Converting
to $\theta$ requires assuming the study population's CBTmin clock time (~04:00–05:00 for a
conventional schedule), which injects roughly **±1 h of phase uncertainty** into the
resulting $Z_{\text{exercise}}(\theta)$. This uncertainty is a property of the conversion, not
of the study, and must be recorded in the module's metadata.

### 6.4 Sleep–wake schedule (non-photic drive)

St Hilaire et al. (2007) extended the Kronauer-lineage model with a non-photic
component driven by the sleep–wake cycle and its associated behaviours, which "acts
both independently and concomitantly with light stimuli"
([DOI](https://doi.org/10.1016/j.jtbi.2007.04.001)). This is the literature precedent
for the package's core claim that influences beyond light belong in the same additive
structure.

The imposed sleep/wake module carries two distinct effects, which should not be
conflated:

- **Masking**: during an imposed sleep window the eyes are closed, so the light drive
  is gated toward zero regardless of ambient illuminance. This is arguably the single
  largest real-world determinant of light exposure and is often the dominant term.
- **Direct non-photic drive**: the behavioural effect itself, per St Hilaire 2007.

> ⚠️ **[UNVERIFIED — must be transcribed before implementation]** The exact functional
> form and coefficients of the St Hilaire 2007 non-photic term ($N_s$, $\sigma$, $\rho$)
> could not be retrieved from an accessible full-text source during preparation of this
> document (the PMC full text returned empty and two mirrors were unreachable). They
> must be transcribed directly from the published paper, §2 and its parameter table,
> before this module is calibrated. Do **not** implement them from recollection.

### 6.5 Caffeine — *a correction to this project's earlier design*

An earlier design note for this package asserted that caffeine has *no* established
direct phase-shifting effect and should be excluded from the model. **That assertion is
wrong and is retracted here.**

Burke et al. (2015), in a double-blind, placebo-controlled, ~49-day within-subject
study, found that a caffeine dose equivalent to a double espresso (~200 mg) taken **3 h
before habitual bedtime induced a ~40 min phase delay** of the circadian melatonin
rhythm — **nearly half the magnitude of the delay produced by 3 h of ~3000 lux evening
bright light**. In vitro, caffeine lengthened the circadian period of molecular
oscillations dose-dependently via adenosine-receptor/cAMP signalling
([DOI](https://doi.org/10.1126/scitranslmed.aac5125)).

The correct status is therefore: **a real, replicated, non-trivial phase-delaying
effect at one tested timing, with no full PRC mapped.** The module is included at
`confidence='low'` with a single calibrated point and an explicitly flagged assumed
shape, rather than excluded. The distinction that matters is *"one point measured, curve
unknown"* — not *"no effect."*

### 6.6 Meal timing

Included at `confidence='low'`. Feeding is a well-established zeitgeber for
**peripheral** oscillators (liver, gut), but evidence that meal timing shifts the
**central** SCN pacemaker in humans — which is what $\theta$ represents here — is
substantially weaker. The module exists so the architecture can express it and so the
uncertainty is recorded in one place, not because a defensible human central-pacemaker
PRC exists. **[No primary human central-pacemaker PRC located; treat as structural
placeholder.]**

### 6.7 Ambient temperature

Stub; `drive()` returns 0. A weak zeitgeber in humans with no human PRC suitable for
calibration located. Present to document the extension point.

---

## 7. Tier 2: full limit-cycle models

Tier 2 exists to (a) derive and validate $Z_i$ by direct numerical perturbation, and
(b) handle the strong-stimulus regime where §3.3 applies. Three published models are
specified. All three share the Process L photoreceptor state $n$.

### 7.1 Jewett–Forger–Kronauer 1999 ("Revised limit cycle oscillator", a.k.a. Kronauer99)

Jewett, Forger & Kronauer, *J Biol Rhythms* 1999;14(6):493–499
([DOI](https://doi.org/10.1177/074873049901400608)).

$$\alpha = \alpha_0 (I/I_0)^{p}$$
$$\hat{B} = G\,\alpha\,(1-n)(1-0.4x)(1-0.4x_c)$$
$$\frac{dx}{dt} = \frac{\pi}{12}\left[x_c + \mu\left(\tfrac{1}{3}x + \tfrac{4}{3}x^3 - \tfrac{256}{105}x^7\right) + \hat{B}\right]$$
$$\frac{dx_c}{dt} = \frac{\pi}{12}\left[q\hat{B}x_c - x\left(\left(\frac{24}{0.99729\,\tau_x}\right)^2 + k\hat{B}\right)\right]$$
$$\frac{dn}{dt} = 60\left[\alpha(1-n) - \beta n\right]$$

| Parameter | Value |
|---|---|
| $\tau_x$ | 24.2 |
| $\mu$ | 0.13 |
| $G$ | 19.875 |
| $\alpha_0$ | 0.16 |
| $\beta$ | 0.013 |
| $k$ | 0.55 |
| $q$ | 1/3 |
| $p$ | 0.6 |
| $I_0$ | 9500 |

From the paper's own abstract, two useful internal facts: peak light sensitivity on the
limit cycle occurs **~4 h before CBTmin** and is **3× the minimum sensitivity**; the
critical phase corresponds to **0.8 h after the minimum of $x$**. Aschoff's rule (period
shortening with increasing light intensity) is built in.

### 7.2 Forger–Jewett–Kronauer 1999 ("simpler model")

Forger, Jewett & Kronauer, *J Biol Rhythms* 1999;14(6):532–537
([DOI](https://doi.org/10.1177/074873099129000867)). Replaces the degree-7 nonlinearity
with a classic cubic van der Pol term, and — per the abstract — predicts three-pulse PRC
and two-pulse amplitude-reduction experiments "with as much, or more, accuracy" than the
degree-7 models.

$$\hat{B} = G(1-n)\,\alpha\,(1-0.4x)(1-0.4x_c)$$
$$\frac{dx}{dt} = \frac{\pi}{12}\left[x_c + \hat{B}\right]$$
$$\frac{dx_c}{dt} = \frac{\pi}{12}\left[\mu\left(x_c - \tfrac{4}{3}x_c^3\right) - x\left(\left(\frac{24}{0.99669\,\tau_x}\right)^2 + k\hat{B}\right)\right]$$
$$\frac{dn}{dt} = 60\left[\alpha(1-n) - \beta n\right]$$

| Parameter | Value |
|---|---|
| $\tau_x$ | 24.2 |
| $\mu$ | 0.23 |
| $G$ | 33.75 |
| $\alpha_0$ | 0.05 |
| $\beta$ | 0.0075 |
| $k$ | 0.55 |
| $p$ | 0.50 |
| $I_0$ | 9500 |

### 7.3 Hannay–Booth–Forger 2019 (macroscopic)

Hannay, Booth & Forger, *J Biol Rhythms* 2019;34(6):658–671
([DOI](https://doi.org/10.1177/0748730419878298)). Derived by systematic reduction from
a high-dimensional model of the SCN neural network, so its variables carry physiological
interpretation. State is **amplitude $R$ and phase $\Psi$** — polar coordinates — which
makes it the most natural Tier-2 partner for a phase-reduced Tier 1: $\Psi$ *is* the
phase variable, and $R$ is exactly the amplitude that Tier 1 discards.

$$\alpha = \alpha_0\frac{I^{p}}{I^{p}+I_0}, \qquad \hat{B} = G(1-n)\alpha$$

$$\frac{dR}{dt} = -\gamma R + \frac{K\cos\beta_1}{2}R(1-R^4) + \underbrace{\frac{A_1}{2}\hat{B}(1-R^4)\cos(\Psi+\beta_{L1}) + \frac{A_2}{2}\hat{B}R(1-R^8)\cos(2\Psi+\beta_{L2})}_{\text{light} \to \text{amplitude}}$$

$$\frac{d\Psi}{dt} = \frac{2\pi}{\tau} + \frac{K}{2}\sin\beta_1(1+R^4) + \underbrace{\sigma\hat{B} - \frac{A_1}{2}\hat{B}\left(R^3+\frac{1}{R}\right)\sin(\Psi+\beta_{L1}) - \frac{A_2}{2}\hat{B}(1+R^8)\sin(2\Psi+\beta_{L2})}_{\text{light} \to \text{phase}}$$

$$\frac{dn}{dt} = 60\left[\alpha(1-n) - \delta n\right]$$

| Parameter | Value | | Parameter | Value |
|---|---|---|---|---|
| $\tau$ | 23.84 | | $\beta_{L1}$ | −0.0026 |
| $K$ | 0.06358 | | $\beta_{L2}$ | −0.957756 |
| $\gamma$ | 0.024 | | $\sigma$ | 0.0400692 |
| $\beta_1$ | −0.09318 | | $G$ | 33.75 |
| $A_1$ | 0.3855 | | $\alpha_0$ | 0.05 |
| $A_2$ | 0.1977 | | $\delta$ | 0.0075 |
| $p$ | 1.5 | | $I_0$ | 9325 |

Note the $d\Psi/dt$ equation: a constant base rate plus additive forcing terms — the
same structure as Tier 1, but with amplitude-dependent coefficients. Tier 1 is
recoverable from it by fixing $R$ at its entrained value.

### 7.4 ⚠️ Parameter-set mixing hazard

The Jewett99 and Forger99 parameter sets are **not interchangeable**, despite sharing
symbol names: $\mu$ differs by ~1.8×, $G$ by ~1.7×, $\alpha_0$ by 3.2×, $\beta$ by 1.7×.
Mixing them silently produces a model that is neither.

This is not hypothetical. Rea et al. (2022), reviewing "the Kronauer99 model", tabulate
published values of $\alpha_0 = 0.05$, $\beta = 0.0075$, $G = 33.75$ (the **Forger99**
Process L set) alongside $\mu = 0.13$, $q = 0.33$, $k = 0.55$ (the **Jewett99** Process P
set), with $p = 0.6$ and a footnote acknowledging that the source used $p = 0.5$
([DOI](https://doi.org/10.3389/fnins.2022.965525)). Their $\mu$, $q$, $k$, $p$, $I_0$
values independently corroborate the Jewett99 Process P values given in §7.1.

**Rule:** pick one published model and use its complete parameter set. The package
stores each set in a separate module and never merges them.

### 7.5 Model provenance note

The equations in §7.1–7.3 were transcribed from the open-source Arcascope `circadian`
reference implementation and cross-checked against the parameter values independently
tabulated by Rea et al. (2022) for the Process P/L constants, and against each paper's
abstract for structural claims. They should still be verified against the primary
papers' own equation displays before being relied on quantitatively — a transcription
error in a single exponent would be silent and would corrupt every derived $Z_i$.

---

## 8. Algorithm: deriving $Z_i(\theta)$ from a published PRC

This is the step that connects §6's measurements to §3's equation, and it is where most
of the achievable accuracy is won or lost.

A published PRC gives the **total** shift $\Delta\phi_{\text{PRC}}(\theta_c; D, A)$ from
a stimulus of duration $D$ and amplitude $A$ centred at phase $\theta_c$. The model needs
the **infinitesimal** sensitivity $Z_i(\theta)$. They are related by

$$\Delta\phi_{\text{PRC}}(\theta_c; D, A) \;=\; \int_{\theta_c - D/2}^{\theta_c + D/2} Z_i(\theta)\,p_i(A)\;d\theta$$

### Method A — direct deconvolution (used for light, melatonin, exercise)

1. **Convert the phase axis** to $\theta$ (CBTmin-anchored) using §2.1. Record the
   conversion and its uncertainty in module metadata.
2. **Normalise the drive**: define $p_i = 1$ at the study's stimulus intensity, so
   $Z_i$ is expressed per unit of *that* stimulus.
3. **Deconvolve the duration**. For short $D$, $Z_i(\theta_c) \approx
   \Delta\phi_{\text{PRC}}(\theta_c)/D$. For long $D$ this over-smooths and must be
   corrected (below).
4. **Fit a periodic basis** — a truncated Fourier series in $\theta$ (typically 2–3
   harmonics) — by least squares, enforcing $Z_i(\theta+24)=Z_i(\theta)$.
5. **Record the fit residual** as the module's stated accuracy.

### The duration-response correction

Step 3's naive division is exactly what §6.1's two-PRC comparison falsifies: dividing
the 6.7 h PRC by 6.7 and the 1 h PRC by 1 gives values differing by 3×. Define a
saturating duration-response factor $\eta(D)$ with $\eta(D)\to 1$ as $D\to0$:

$$Z_i(\theta) = \frac{\Delta\phi_{\text{PRC}}(\theta; D)}{D\,\eta(D)}$$

The two light PRCs give two constraints on $\eta$: taking $\eta(1) \approx 1$ as the
reference, consistency requires $\eta(6.7) \approx 0.34$ — i.e. the seventh hour of
exposure contributes roughly a third as much per hour as the first. A saturating form
such as $\eta(D) = \frac{D_{1/2}}{D_{1/2}+D}\cdot\frac{D_{1/2}+1}{D_{1/2}}$ fitted to
those two points is the minimum defensible treatment; three or more durations would be
needed to fit it properly. **This is a genuine open gap**, and any single-duration
calibration must state the duration it is valid for.

### Method B — numerical adjoint / direct perturbation (Tier 2 derived)

Where a Tier 2 model is available and trusted, $Z_i$ can be obtained without any PRC
study, by direct measurement on the model:

```
for θ_k in linspace(0, 24, N):
    entrain Tier-2 model to steady state
    advance to phase θ_k
    branch A: integrate forward with no stimulus     → φ_A(T)
    branch B: integrate forward with a small pulse ε → φ_B(T)
    Z(θ_k) ← (φ_B − φ_A) / (ε · pulse_duration)
smooth / fit Fourier basis over θ_k
```

with $T$ several cycles so transients decay. Formally this approximates the adjoint
solution; the pulse must be small enough that the response is linear in $\varepsilon$
(verify by halving $\varepsilon$ and confirming $Z$ is unchanged).

**The cross-check that matters:** $Z_i$ derived by Method A (from human data) and by
Method B (from the Tier-2 model) should agree in sign, zero-crossings and rough
magnitude. Where they do not, at least one of the model, the calibration, or the marker
conversion is wrong. This comparison is the single most informative validation the
package can run.

---

## 9. Individual parameters

| Parameter | Default | Basis |
|---|---|---|
| $\tau$ | 24.18 h | Czeisler 1999: mean intrinsic period across young **and** older adults, tight distribution ([DOI](https://doi.org/10.1126/science.284.5423.2177)) |
| PRC amplitude scale | 1.0 | population average by construction |
| Chronotype offset | 0.0 h | shifts the CBTmin ← wake estimate |

Czeisler et al.'s result is worth stating precisely because it overturned an earlier
consensus: intrinsic period averages **24.18 h in both young and older individuals**,
with a tight distribution comparable to other species, and **does not shorten with age**
as previously reported. Earlier estimates (medians of ~25 h, ranges of 13–65 h) were
artefacts of subjects being exposed to light levels sufficient to confound period
estimation.

The default $\tau = 24.2$ h used in code is this value rounded; either is defensible.

---

## 10. Validation targets

Ordered by how much they constrain the implementation:

1. **Free-running period.** Empty registry ⇒ drift of exactly $(24/\tau - 1)$ h per 24 h.
   Analytic, exact, no tolerance needed. *(Implemented.)*
2. **RK4 order.** Halving $h$ reduces global error ≈16×. *(Implemented.)*
3. **Analytic ≡ numeric.** RK4 converges to the closed-form pulse answer as $h\to0$.
4. **Superposition.** Two modules together ≈ sum of each alone (validates the additive
   architecture; catches accidental coupling between modules).
5. **PRC shape.** Each module's $Z_i$ reproduces its source study's sign pattern,
   zero-crossings and peak locations.
6. **PRC magnitude.** Simulating the source study's own protocol reproduces its
   headline number: 5.02 h peak-to-trough for Khalsa's 6.7 h protocol; 2.20 h for
   St Hilaire's 1 h protocol; 1.8 h / 1.3 h max advance/delay for Burgess 3 mg.
7. **East–west asymmetry.** Equal-magnitude eastward and westward shifts should
   re-entrain at measurably different rates.

> ⚠️ **Do not over-constrain target 7.** Diekman & Bose (2017) show the east–west
> asymmetry depends on *both* the traveller's endogenous period *and* daylength, and
> that **"the critical factor is not simply whether the endogenous period is greater
> than or less than 24 h as is commonly assumed"**
> ([DOI](https://doi.org/10.1016/j.jtbi.2017.10.002)). A test asserting "east is always
> slower" would encode a folk simplification the literature contradicts. Assert only
> that the two directions differ, under stated $\tau$ and photoperiod.

---

## 11. Beyond simulation: optimal scheduling (future work)

Once the forward model exists, "when should I get light to shift fastest?" becomes an
optimal-control problem rather than a new model. Serkh & Forger (2014) solved exactly
this on the Kronauer model ([DOI](https://doi.org/10.1371/journal.pcbi.1003523)),
reporting four principles worth encoding as tests for any future scheduler:

1. For **dim light and small shifts**, optimal schedules perturb circadian amplitude
   only slightly.
2. For **bright light and large shifts**, optimal schedules move along the **shortest
   path in phase space** — which necessarily passes through reduced amplitude, and
   therefore *cannot be represented in Tier 1 at all*.
3. **Short light pulses are less effective than sustained light** for rapid
   re-entrainment.
4. **Daytime should be significantly shorter when delaying the clock than when
   advancing it** — an asymmetry that falls out of the optimisation rather than being
   assumed.

Principle 2 is the sharpest statement of Tier 1's limits: the *optimal* large-shift
strategy is precisely the regime where phase reduction is invalid.

---

## 12. Known limitations

1. **First-order theory.** Tier 1 is $O(\varepsilon)$; bright light is not weak.
2. **Duration-response is under-determined** (§8) — two data points, ≥3 needed.
3. **Marker conversion injects error** — ±1 h for clock-time-reported PRCs (exercise).
4. **Population averages throughout.** Real PRC amplitudes vary with age, prior light
   history, season and genotype; none of that is modelled.
5. **CBTmin is estimated, not measured** (wake − 3 h). All phase predictions inherit
   this error.
6. **St Hilaire 2007 non-photic coefficients are not yet transcribed** (§6.4).
7. **Sleep/alertness is not modelled.** Predicting *how someone feels* requires a
   homeostatic process (Borbély's Process S) on top of $\theta$; deliberately out of
   scope here, which is why this model predicts phase and nothing else.
8. **Not a medical device.**

---

## 13. References

All records located via **PubMed**; DOI links below.

1. **Czeisler CA, et al.** Stability, precision, and near-24-hour period of the human circadian pacemaker. *Science*. 1999;284(5423):2177–2181. [DOI](https://doi.org/10.1126/science.284.5423.2177)
2. **Czeisler CA, et al.** Bright light induction of strong (type 0) resetting of the human circadian pacemaker. *Science*. 1989;244(4910):1328–1333. [DOI](https://doi.org/10.1126/science.2734611)
3. **Zeitzer JM, Dijk DJ, Kronauer RE, Brown EN, Czeisler CA.** Sensitivity of the human circadian pacemaker to nocturnal light: melatonin phase resetting and suppression. *J Physiol*. 2000;526(Pt 3):695–702. [DOI](https://doi.org/10.1111/j.1469-7793.2000.00695.x)
4. **Khalsa SBS, Jewett ME, Cajochen C, Czeisler CA.** A phase response curve to single bright light pulses in human subjects. *J Physiol*. 2003;549(Pt 3):945–952. [DOI](https://doi.org/10.1113/jphysiol.2003.040477)
5. **St Hilaire MA, Gooley JJ, Khalsa SBS, Kronauer RE, Czeisler CA, Lockley SW.** Human phase response curve to a 1 h pulse of bright white light. *J Physiol*. 2012;590(13):3035–3045. [DOI](https://doi.org/10.1113/jphysiol.2012.227892)
6. **Burgess HJ, Revell VL, Eastman CI.** A three pulse phase response curve to three milligrams of melatonin in humans. *J Physiol*. 2008;586(2):639–647. [DOI](https://doi.org/10.1113/jphysiol.2007.143180)
7. **Burgess HJ, Revell VL, Molina TA, Eastman CI.** Human phase response curves to three days of daily melatonin: 0.5 mg versus 3.0 mg. *J Clin Endocrinol Metab*. 2010;95(7):3325–3331. [DOI](https://doi.org/10.1210/jc.2009-2590)
8. **Youngstedt SD, Elliott JA, Kripke DF.** Human circadian phase-response curves for exercise. *J Physiol*. 2019;597(8):2253–2268. [DOI](https://doi.org/10.1113/JP276943)
9. **Burke TM, et al.** Effects of caffeine on the human circadian clock in vivo and in vitro. *Sci Transl Med*. 2015;7(305):305ra146. [DOI](https://doi.org/10.1126/scitranslmed.aac5125)
10. **Jewett ME, Forger DB, Kronauer RE.** Revised limit cycle oscillator model of human circadian pacemaker. *J Biol Rhythms*. 1999;14(6):493–499. [DOI](https://doi.org/10.1177/074873049901400608)
11. **Forger DB, Jewett ME, Kronauer RE.** A simpler model of the human circadian pacemaker. *J Biol Rhythms*. 1999;14(6):532–537. [DOI](https://doi.org/10.1177/074873099129000867)
12. **St Hilaire MA, Klerman EB, Khalsa SBS, Wright KP Jr, Czeisler CA, Kronauer RE.** Addition of a non-photic component to a light-based mathematical model of the human circadian pacemaker. *J Theor Biol*. 2007;247(4):583–599. [DOI](https://doi.org/10.1016/j.jtbi.2007.04.001)
13. **Hannay KM, Booth V, Forger DB.** Macroscopic models for human circadian rhythms. *J Biol Rhythms*. 2019;34(6):658–671. [DOI](https://doi.org/10.1177/0748730419878298)
14. **Rea MS, Nagare R, Bierman A, Figueiro MG.** The circadian stimulus-oscillator model: improvements to Kronauer's model of the human circadian pacemaker. *Front Neurosci*. 2022;16:965525. [DOI](https://doi.org/10.3389/fnins.2022.965525)
15. **Serkh K, Forger DB.** Optimal schedules of light exposure for rapidly correcting circadian misalignment. *PLoS Comput Biol*. 2014;10(4):e1003523. [DOI](https://doi.org/10.1371/journal.pcbi.1003523)
16. **Diekman CO, Bose A.** Reentrainment of the circadian pacemaker during jet lag: east-west asymmetry and the effects of north-south travel. *J Theor Biol*. 2017;437:261–285. [DOI](https://doi.org/10.1016/j.jtbi.2017.10.002)
17. **Roach GD, Sargent C.** Interventions to minimize jet lag after westward and eastward flight. *Front Physiol*. 2019;10:927. [DOI](https://doi.org/10.3389/fphys.2019.00927)

**Software referenced:** Arcascope `circadian` — open-source Python implementations of
the Forger99, Jewett99 and Hannay19 models, used here as a transcription cross-check
(<https://github.com/Arcascope/circadian>). The primary publications remain the source
of truth.
