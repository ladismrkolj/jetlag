# Mathematical Modelling of the Human Circadian Clock

**A review of the theory, published equations, parameter values, and numerical methods**

Version 0.2 · Literature review

---

## Scope and how to read this

This document reviews how the human circadian pacemaker is modelled quantitatively:
what the published models are, what their equations and coefficients actually are, what
the measured phase-response data say, and — in Section 7 — which numerical algorithms
research groups concretely use to integrate, calibrate, analyse and optimise these
models.

It is a literature review, not a specification for any particular implementation.

> **Sources.** Every numeric value below is taken from a primary publication located via
> **PubMed**, cited inline with a DOI link. Values that could not be verified against an
> accessible primary source are marked **[UNVERIFIED]** and should be checked before use.
> Where a value comes from a reference software implementation rather than a paper, that
> is stated explicitly.

**Contents**

1. [What the models represent](#1-what-the-models-represent)
2. [Families of model](#2-families-of-model)
3. [The light input pathway](#3-the-light-input-pathway-process-l)
4. [The models in full: equations and parameters](#4-the-models-in-full-equations-and-parameters)
5. [Phase reduction and phase response curves: the theory](#5-phase-reduction-and-phase-response-curves-the-theory)
6. [Empirical phase response curves: the data](#6-empirical-phase-response-curves-the-data)
7. [Numerical algorithms used in the literature](#7-numerical-algorithms-used-in-the-literature)
8. [Individual variation](#8-individual-variation)
9. [Experimental protocols behind the data](#9-experimental-protocols-behind-the-data)
10. [Open problems](#10-open-problems)
11. [References](#11-references)

---

## 1. What the models represent

### 1.1 The pacemaker and its observable markers

Human circadian models represent the central pacemaker in the suprachiasmatic nuclei
(SCN). The SCN itself is not directly observable in humans, so every model is calibrated
against **phase markers** — measurable rhythms driven by the pacemaker:

| Marker | What it is | Notes |
|---|---|---|
| CBTmin | Core body temperature minimum | Classic reference; requires constant-routine conditions to unmask |
| DLMO | Dim-light melatonin onset | Most widely used today; salivary or plasma melatonin under dim light |
| aMT6s | Urinary 6-sulphatoxymelatonin | Melatonin metabolite; used where repeated blood/saliva sampling is impractical |

**The marker problem.** Different studies report phase against different markers, and
they are not interchangeable. DLMO precedes CBTmin by roughly 7 h, so mistaking one for
the other displaces a phase response curve by about a quarter of a cycle.

```math
\theta_{\text{CBTmin}} = \theta_{\text{DLMO}} + \Delta
```

where the offset Δ is approximately 7 h.

> The 7 h offset is the value used by the open-source Arcascope `circadian` reference
> implementation (`cbt_to_dlmo = 7.0`). It is a population approximation with real
> inter-individual spread. **[PARTIALLY VERIFIED — widely used, spread not sourced here.]**

A worked consistency check on this conversion appears in §6.2.

### 1.2 Phase shifts, PRCs, and resetting type

A **phase response curve** (PRC) plots the phase shift produced by a stimulus against
the circadian phase at which it was applied. Two classes are distinguished:

- **Type 1 (weak) resetting** — the PRC has a continuous shape with average slope 1;
  shifts are modest and the oscillator's amplitude is largely preserved.
- **Type 0 (strong) resetting** — large stimuli drive the oscillator near its
  singularity, amplitude collapses, and phase can be reset to essentially any value.
  Czeisler et al. (1989) demonstrated Type 0 resetting in humans with bright light
  ([DOI](https://doi.org/10.1126/science.2734611)).

This distinction is the main reason amplitude appears as a state variable in most
models: a phase-only description cannot represent amplitude suppression.

---

## 2. Families of model

### 2.1 Limit-cycle oscillator models (van der Pol lineage)

The dominant lineage in human circadian modelling. A self-sustained oscillator with two
state variables (a pacemaker variable and its derivative-like companion) is driven by a
light-derived signal. Descended from Kronauer's 1990 model, refined by Jewett, Forger &
Kronauer (1999), simplified by Forger, Jewett & Kronauer (1999), and extended with a
non-photic input by St Hilaire et al. (2007).

Characteristics: reproduces Type 0 resetting, amplitude suppression, and Aschoff's rule
(period varying with light intensity). Requires numerical integration; no closed form.

### 2.2 Phase-only (phase-reduced) models

A single phase variable evolving at a constant intrinsic rate plus additive
stimulus-dependent terms. Formally justified as the first-order reduction of a
limit-cycle model (§5). Cheap, analytically tractable, and directly parameterised by
measured PRCs — at the cost of discarding amplitude and therefore Type 0 behaviour.

### 2.3 Macroscopic / mean-field models

Hannay, Booth & Forger (2019) derive low-dimensional models *systematically* from a
high-dimensional model of the SCN neuronal population, rather than positing an
oscillator phenomenologically ([DOI](https://doi.org/10.1177/0748730419878298)). The
resulting state variables — a collective amplitude `R` and phase `Ψ` — retain a
physiological interpretation (degree of synchrony among neurons, and mean phase).

### 2.4 Comparison

| Family | State | Amplitude represented | Type 0 | Closed form | Typical use |
|---|---|---|---|---|---|
| Limit-cycle (van der Pol lineage) | x, xc, n | Yes | Yes | No | Phase prediction, protocol design |
| Phase-only | θ | No | No | For idealised inputs | Fast estimation, PRC-driven scheduling |
| Macroscopic / mean-field | R, Ψ, n | Yes (as synchrony) | Yes | No | Physiologically interpretable prediction |

---

## 3. The light input pathway (Process L)

### 3.1 Irradiance–response

Zeitzer et al. (2000) established the human dose–response to nocturnal light: both
phase resetting and acute melatonin suppression follow a **logistic** function of
illuminance, and — the headline result — **half of the maximal phase-delaying response
to ~9000 lux is reached at just over 1% of that intensity, i.e. ordinary room light of
about 100 lux** ([DOI](https://doi.org/10.1111/j.1469-7793.2000.00695.x)). n = 23, 6.5 h
exposure in the early biological night.

The practical consequence is that indoor light is not negligible; it sits near the
steep part of the response curve.

### 3.2 The activation function α(I)

Two functional forms appear in the literature.

Jewett99 and Forger99 use an unbounded power law:

```math
\alpha(I) = \alpha_0 \left(\frac{I}{I_0}\right)^{p}
```

Hannay19 uses a saturating Hill form:

```math
\alpha(I) = \alpha_0 \frac{I^{p}}{I^{p} + I_0}
```

The Hill form saturates and is therefore better behaved outside the fitted range; the
power law is unbounded and must be used only within it.

### 3.3 Photoreceptor activation dynamics

All the models below carry a photoreceptor-activation state `n` in [0, 1] with
first-order kinetics — activation proportional to α(I) on the unactivated fraction,
and spontaneous decay:

```math
\frac{dn}{dt} = 60 \left[\alpha(I)(1-n) - \beta n\right]
```

The factor 60 sets the timescale (the state equilibrates in minutes, fast relative to
the 24 h oscillator).

### 3.4 Spectral weighting

Photopic illuminance (lux) weights light by the human *visual* sensitivity curve, which
is not the sensitivity of the circadian phototransduction pathway. Rea and colleagues
developed circadian light (CL) and circadian stimulus (CS) metrics incorporating the
melanopsin-driven pathway and a blue–yellow spectral opponent mechanism
([DOI](https://doi.org/10.3389/fnins.2022.965525)). Substituting CS for lux required
changing the saturation constant from I₀ = 9500 to I₀ = 0.7, the mathematical asymptote
of the CS scale.

For single-light-source experiments the spectral question is moot (relative
effectiveness is irrelevant when only one spectrum is used); it matters for mixed
real-world light.

---

## 4. The models in full: equations and parameters

> **Transcription note.** The equations in §4.1–4.4 were transcribed from the
> open-source Arcascope `circadian` reference implementation and cross-checked against
> the parameter values independently tabulated by Rea et al. (2022) and against each
> paper's abstract for structural claims. They should be verified against each paper's
> own equation display before quantitative use — a single wrong exponent would be silent.

### 4.1 Jewett, Forger & Kronauer 1999 — revised limit cycle oscillator

*J Biol Rhythms* 1999;14(6):493–499 ([DOI](https://doi.org/10.1177/074873049901400608)).
Often referred to as "Kronauer99". Uses a degree-7 nonlinearity so that amplitude
recovery is slow near the singularity and fast near the limit cycle.

```math
\alpha = \alpha_0 (I/I_0)^{p}
```

```math
\hat{B} = G \alpha (1-n)(1-0.4x)(1-0.4x_c)
```

```math
\frac{dx}{dt} = \frac{\pi}{12}\left[x_c + \mu\left(\tfrac{1}{3}x + \tfrac{4}{3}x^3 - \tfrac{256}{105}x^7\right) + \hat{B}\right]
```

```math
\frac{dx_c}{dt} = \frac{\pi}{12}\left[q\hat{B}x_c - x\left(\left(\frac{24}{0.99729\ \tau_x}\right)^2 + k\hat{B}\right)\right]
```

```math
\frac{dn}{dt} = 60\left[\alpha(1-n) - \beta n\right]
```

| Parameter | Value |
|---|---|
| τₓ | 24.2 |
| μ | 0.13 |
| G | 19.875 |
| α₀ | 0.16 |
| β | 0.013 |
| k | 0.55 |
| q | 1/3 |
| p | 0.6 |
| I₀ | 9500 |

From the paper's own description: peak light sensitivity on the limit cycle occurs
**about 4 h before CBTmin** and is **three times the minimum sensitivity**; the critical
phase corresponds to **0.8 h after the minimum of x**. A direct effect of light on
period is included, so that period decreases as intensity increases (Aschoff's rule).

### 4.2 Forger, Jewett & Kronauer 1999 — the simpler (cubic) model

*J Biol Rhythms* 1999;14(6):532–537 ([DOI](https://doi.org/10.1177/074873099129000867)).
Replaces the degree-7 nonlinearity with the classic cubic van der Pol term. The authors
report it predicts a three-pulse PRC experiment and a two-pulse amplitude-reduction
study "with as much, or more, accuracy" than the degree-7 models.

```math
\hat{B} = G(1-n) \alpha (1-0.4x)(1-0.4x_c)
```

```math
\frac{dx}{dt} = \frac{\pi}{12}\left[x_c + \hat{B}\right]
```

```math
\frac{dx_c}{dt} = \frac{\pi}{12}\left[\mu\left(x_c - \tfrac{4}{3}x_c^3\right) - x\left(\left(\frac{24}{0.99669\ \tau_x}\right)^2 + k\hat{B}\right)\right]
```

```math
\frac{dn}{dt} = 60\left[\alpha(1-n) - \beta n\right]
```

| Parameter | Value |
|---|---|
| τₓ | 24.2 |
| μ | 0.23 |
| G | 33.75 |
| α₀ | 0.05 |
| β | 0.0075 |
| k | 0.55 |
| p | 0.50 |
| I₀ | 9500 |

### 4.3 St Hilaire et al. 2007 — non-photic extension

*J Theor Biol* 2007;247(4):583–599 ([DOI](https://doi.org/10.1016/j.jtbi.2007.04.001)).
Extends the light-driven model with a non-photic drive from the sleep–wake cycle and
its associated behaviours, which "acts both independently and concomitantly with light
stimuli". This is the principal published precedent for treating non-photic influences
in the same framework as light.

The model was validated against phase predictions for a blind subject entrained to a
scheduled sleep–wake cycle, constant-routine protocols, forced-desynchrony protocols
(day lengths around 20 h and 28 h), and both bright (5000–10 000 lux) and dim (1.5 lux)
light exposures.

> ⚠️ **[UNVERIFIED]** The exact functional form and coefficients of the non-photic term
> could not be retrieved from an accessible full text for this review (the PubMed
> Central full text returned empty and two mirrors were unreachable). They must be
> transcribed directly from the published paper before use.

### 4.4 Hannay, Booth & Forger 2019 — macroscopic model

*J Biol Rhythms* 2019;34(6):658–671 ([DOI](https://doi.org/10.1177/0748730419878298)).
State is collective amplitude `R` and phase `Ψ`.

```math
\alpha = \alpha_0\frac{I^{p}}{I^{p}+I_0}
```

```math
\hat{B} = G(1-n)\alpha
```

```math
\frac{dR}{dt} = -\gamma R + \frac{K\cos\beta_1}{2}R(1-R^4) + \frac{A_1}{2}\hat{B}(1-R^4)\cos(\Psi+\beta_{L1}) + \frac{A_2}{2}\hat{B}R(1-R^8)\cos(2\Psi+\beta_{L2})
```

```math
\frac{d\Psi}{dt} = \frac{2\pi}{\tau} + \frac{K}{2}\sin\beta_1(1+R^4) + \sigma\hat{B} - \frac{A_1}{2}\hat{B}\left(R^3+\frac{1}{R}\right)\sin(\Psi+\beta_{L1}) - \frac{A_2}{2}\hat{B}(1+R^8)\sin(2\Psi+\beta_{L2})
```

```math
\frac{dn}{dt} = 60\left[\alpha(1-n) - \delta n\right]
```

| Parameter | Value | Parameter | Value |
|---|---|---|---|
| τ | 23.84 | β_L1 | −0.0026 |
| K | 0.06358 | β_L2 | −0.957756 |
| γ | 0.024 | σ | 0.0400692 |
| β₁ | −0.09318 | G | 33.75 |
| A₁ | 0.3855 | α₀ | 0.05 |
| A₂ | 0.1977 | δ | 0.0075 |
| p | 1.5 | I₀ | 9325 |

Two things are worth noting structurally. First, the phase equation has the form
"constant base rate + additive light terms", which is the same shape as a phase-only
model but with amplitude-dependent coefficients — the two families connect here.
Second, the `1/R` term means the phase equation is **singular at R = 0**; any
integration must guard against amplitude approaching zero (see §7.7).

### 4.5 Parameter-set mixing hazard

The Jewett99 and Forger99 sets share symbol names but are **not interchangeable**:
μ differs by about 1.8×, G by 1.7×, α₀ by 3.2×, β by 1.7×.

This is not hypothetical. Rea et al. (2022), reviewing "the Kronauer99 model", tabulate
published values of α₀ = 0.05, β = 0.0075, G = 33.75 (the **Forger99** Process L set)
alongside μ = 0.13, q = 0.33, k = 0.55 (the **Jewett99** Process P set), with p = 0.6 and
a footnote noting the source used p = 0.5
([DOI](https://doi.org/10.3389/fnins.2022.965525)). Their μ, q, k, p and I₀ values do
independently corroborate the Jewett99 Process P values in §4.1.

**Practical rule:** adopt one published model and use its complete parameter set.

---

## 5. Phase reduction and phase response curves: the theory

### 5.1 The reduction

Take a self-sustained oscillator with a stable limit cycle of period τ:

```math
\dot{\mathbf{x}} = \mathbf{F}(\mathbf{x})
```

Define the asymptotic phase θ(**x**) on the basin of attraction. Under a weak
perturbation ε**q**(t), the dynamics reduce to a single phase equation:

```math
\dot{\mathbf{x}} = \mathbf{F}(\mathbf{x}) + \varepsilon \mathbf{q}(t) \Longrightarrow \dot\theta = \omega + \varepsilon \mathbf{Z}(\theta)\cdot\mathbf{q}(t) + O(\varepsilon^2)
```

where **Z**(θ) is the **infinitesimal PRC**, the gradient of asymptotic phase evaluated
on the limit cycle. It is obtained as the periodic solution of the adjoint variational
equation

```math
\dot{\mathbf{Z}} = -D\mathbf{F}^\top \mathbf{Z}
```

subject to the normalisation

```math
\mathbf{Z}\cdot\mathbf{F} = \omega
```

(Malkin's theorem; the standard construction in Winfree/Kuramoto phase-reduction
theory). For multiple independent perturbations this generalises to

```math
\frac{d\theta}{dt} = \omega + \sum_i Z_i(\theta) p_i(t)
```

**Additivity of separate influences is therefore a first-order theorem, not a modelling
convenience** — but it is *only* first order.

### 5.2 Validity limits

The reduction discards amplitude. Consequences:

- Type 0 resetting cannot be represented at all.
- Errors are O(ε²), and ε is not small for bright light.
- Serkh & Forger's optimal large-shift schedules move the state along the shortest path
  in phase space, which necessarily passes through reduced amplitude (§7.4) — precisely
  the regime a phase-only description cannot express.

Empirically, the stimuli in §6 produced Type 1 curves at the intensities tested, so
phase-only descriptions are defensible in that tested range.

---

## 6. Empirical phase response curves: the data

### 6.1 Light

| Duration | Intensity | Fitted peak-to-trough | Type | n | Source |
|---|---|---|---|---|---|
| 6.7 h | ~10 000 lx fixed gaze / 5000–9000 lx free gaze | **5.02 h** | 1 | 21 | Khalsa 2003 ([DOI](https://doi.org/10.1113/jphysiol.2003.040477)) |
| 1 h | ~8000 lx | **2.20 h** | 1 | 18 | St Hilaire 2012 ([DOI](https://doi.org/10.1113/jphysiol.2012.227892)) |

Shape: phase **delays** when the stimulus is centred *before* CBTmin, **advances** when
centred *after*, crossing zero at the critical phase near CBTmin. A `<3 lux` dim-light
control produced no discernible PRC.

> **On the "dead zone".** Khalsa et al. explicitly report that **no prolonged dead zone
> of photic insensitivity was apparent** during the subjective day. The flat mid-day
> region drawn in many schematic PRCs is not supported by that dataset.

**Duration is strongly nonlinear.** The 1 h PRC amplitude is ~40% of the 6.7 h amplitude
despite delivering only ~15% of the exposure. Expressed as implied shift per hour of
exposure at the PRC peak:

For the 6.7 h exposure:

```math
\frac{5.02/2}{6.7} \approx 0.37\ \text{h/h}
```

For the 1 h exposure:

```math
\frac{2.20/2}{1} \approx 1.10\ \text{h/h}
```

A threefold discrepancy. Any single duration-independent sensitivity function is
therefore an approximation valid only near the duration it was fitted at.

### 6.2 Exogenous melatonin

| Dose | Advance peak | Delay peak | Max advance | Max delay | n | Source |
|---|---|---|---|---|---|---|
| 3.0 mg | ~5 h before DLMO | ~11 h after DLMO | **1.8 h** | **1.3 h** | 27 | Burgess 2008 ([DOI](https://doi.org/10.1113/jphysiol.2007.143180)) |
| 0.5 mg | 2–4 h before DLMO (9–11 h before sleep midpoint) | shortly after wake | comparable | comparable | 34 | Burgess 2010 ([DOI](https://doi.org/10.1210/jc.2009-2590)) |

Findings that matter for modelling:

- The melatonin PRC is roughly **antiphase to the light PRC**; its advance region falls
  in the afternoon.
- There is a **dead zone during the first half of habitual sleep** — melatonin taken as
  a hypnotic at bedtime has minimal phase-shifting effect.
- **Dose changes the optimal timing more than the magnitude.** The optimum is later for
  the lower dose; given at their respective optima, 0.5 mg and 3.0 mg produce similarly
  sized shifts. A dose parameter must therefore translate the curve, not merely scale it.

**Worked marker conversion.** Applying Δ ≈ 7 h from §1.1 to the 3.0 mg curve:
advance peak −5 − 7 = **−12 h relative to CBTmin**; delay peak +11 − 7 = **+4 h relative
to CBTmin**. This is a useful check that the conversion is being applied consistently.

### 6.3 Exercise

Youngstedt et al. (2019): n = 99 (51 older, 48 young), 1 h moderate treadmill exercise at
65–75% heart-rate reserve on three consecutive days, eight times of day, 90-minute
ultrashort sleep–wake protocol, aMT6s phase markers
([DOI](https://doi.org/10.1113/JP276943)).

| Clock time | Effect |
|---|---|
| 07:00 | phase advance (peak) |
| 13:00–16:00 | phase advance (second peak) |
| 16:00 | minimal |
| 19:00–22:00 | phase delay (peak) |
| 02:00 | minimal |

Two notable findings: the advance region is **bimodal** (morning *and* afternoon — the
afternoon advance is novel to this study), and amplitudes are **"comparable to
expectations for bright light of equal duration"**. No significant age or sex differences.

⚠️ This PRC is reported in **clock time**, not against a phase marker. Converting to a
marker-referenced phase requires assuming the population's CBTmin clock time
(~04:00–05:00 on a conventional schedule), injecting roughly ±1 h of uncertainty.

### 6.4 Caffeine

Burke et al. (2015), a double-blind placebo-controlled ~49-day within-subject study,
found that a caffeine dose equivalent to a double espresso (~200 mg) taken **3 h before
habitual bedtime induced a ~40 min phase delay** of the circadian melatonin rhythm —
**nearly half the magnitude of the delay produced by 3 h of ~3000 lux evening bright
light**. In vitro, caffeine lengthened the period of molecular oscillations
dose-dependently through adenosine-receptor/cAMP signalling
([DOI](https://doi.org/10.1126/scitranslmed.aac5125)).

Status: a real, measured phase-delaying effect at **one tested timing**; no full PRC has
been mapped. This is materially different from "no effect", and also from having a curve.

### 6.5 Influences with weaker or absent human PRCs

- **Meal timing.** Well established as a zeitgeber for *peripheral* oscillators (liver,
  gut). Evidence that it shifts the *central* pacemaker in humans is substantially
  weaker. **[No primary human central-pacemaker PRC located for this review.]**
- **Ambient temperature.** A weak zeitgeber in humans; no human PRC suitable for
  calibration located here.

### 6.6 Converting a published PRC into a sensitivity function

A published PRC gives the **total** shift from a stimulus of finite duration D and
amplitude A centred at phase θ_c. A phase-only model needs the **infinitesimal**
sensitivity Z(θ). They are related by

```math
\Delta\phi_{\text{PRC}}(\theta_c; D, A) = \int_{\theta_c - D/2}^{\theta_c + D/2} Z(\theta) p(A) \ d\theta
```

The practical procedure used in the literature is:

1. Convert the phase axis to a common marker (§1.1), recording the conversion.
2. Normalise the drive so that p = 1 at the study's stimulus intensity.
3. Deconvolve duration: for short D, Z(θ_c) ≈ Δφ/D. For long D this over-smooths, and
   the nonlinearity in §6.1 must be accounted for.
4. Fit a periodic basis (a truncated Fourier series, typically 2–3 harmonics) by least
   squares, enforcing 24 h periodicity.

Step 3 is where the two light PRCs bite: naive division gives 0.37 h/h from one study
and 1.10 h/h from the other. With only two durations published, a duration-response
correction is under-determined — three or more would be needed to fit one properly.

---

## 7. Numerical algorithms used in the literature

### 7.1 Integrating the ODEs

The models in §4 are 3-dimensional and non-stiff under normal light regimes.

- **Fixed-step RK4** is the common choice in reference implementations. Step sizes on
  the order of minutes (roughly 0.01–0.1 h) are used. The binding constraint is not the
  24 h oscillator dynamics but resolving **light on/off transitions** and the fast
  photoreceptor state `n`, whose kinetics carry a factor of 60.
- **Adaptive embedded Runge–Kutta** (e.g. Dormand–Prince RK45) is used where higher
  accuracy is wanted. Note that realistic light schedules are piecewise-constant, so the
  right-hand side is **discontinuous**; adaptive steppers should be run piecewise
  between light-schedule breakpoints rather than allowed to straddle a discontinuity,
  which otherwise causes step-size collapse and silent accuracy loss.
- **Burn-in.** Models are entrained to the subject's habitual light/sleep schedule for
  a simulated week or more before the window of interest, so that reported results are
  independent of the assumed initial condition.

### 7.2 Computing a PRC from a model

Two distinct algorithms, answering different questions:

**(a) Direct perturbation** — the approach used to generate model PRCs comparable with
experiment:

```
for each of N phases θ_k spanning one cycle:
    entrain the model to steady state
    advance to θ_k
    run branch A: no stimulus              → final phase φ_A
    run branch B: the stimulus of interest → final phase φ_B
    PRC(θ_k) ← φ_B − φ_A          (measured after transients decay)
```

Cost is O(N) full simulations. It captures **finite-amplitude** effects, which is what
experiments actually measure, and it can produce Type 0 curves.

**(b) Adjoint / variational method** — integrate the adjoint equation
Ż = −DFᵀZ backwards along the limit cycle with normalisation Z·F = ω. This yields the
infinitesimal PRC in a single pass, far more cheaply, but is valid only in the
infinitesimal limit.

Comparing (a) at small stimulus amplitude against (b) is a standard internal
consistency check.

### 7.3 Entrainment maps and Poincaré maps

Diekman & Bose (2017) analyse re-entrainment with **one-dimensional entrainment maps**
([DOI](https://doi.org/10.1016/j.jtbi.2017.10.002)). The construction:

1. Define a map taking the oscillator's phase at the start of day *n* to its phase at
   the start of day *n+1* under the destination light–dark cycle.
2. **Fixed points** of the map are entrained states; stability follows from the slope.
3. **Re-entrainment time** is the number of iterations to converge — far cheaper than
   simulating and inspecting long trajectories.
4. The **unstable fixed point** partitions the phase circle into basins, determining
   whether a traveller re-entrains by advancing or delaying (orthodromic vs antidromic
   re-entrainment).

Using this they computed re-entrainment times "for travel between any two points on the
globe at any time of the day and year", and reached two results worth flagging:

- The east–west asymmetry depends on **both** the traveller's endogenous period **and**
  daylength — "the critical factor is not simply whether the endogenous period is
  greater than or less than 24 h as is commonly assumed."
- The change in **daylength** during **north–south** travel can cause jet lag **even
  when no time zones are crossed**.

### 7.4 Optimal control of light schedules

Serkh & Forger (2014) computed mathematically optimal light schedules for rapid
re-entrainment ([DOI](https://doi.org/10.1371/journal.pcbi.1003523)). Method:

- Optimal schedules are **bang-bang** — light is either at maximum or off. This is a
  *property* of the optimal solution, not an assumption.
- The infinite-dimensional control problem therefore collapses to finding a finite set
  of **switching times**, which is what the algorithm searches over.
- The "slam shift" schedule is used as the optimisation starting point.
- Over 1000 optimal schedules were computed across situations and light levels.

Their four reported principles:

1. For **dim light and small shifts**, optimal schedules perturb amplitude only slightly.
2. For **bright light and large shifts**, optimal schedules follow the **shortest path in
   phase space** (necessarily through reduced amplitude).
3. **Short light pulses are less effective than sustained light** for rapid re-entrainment.
4. **Daytime should be significantly shorter when delaying than when advancing.**

### 7.5 Parameter fitting and model comparison

Rea et al. (2022) give an explicit, reproducible protocol
([DOI](https://doi.org/10.3389/fnins.2022.965525)):

- **Metrics:** mean absolute error (MAE) in predicted ΔDLMO, R², and the percentage of
  subjects predicted within 1 h.
- **Validation across four independent datasets** using calibrated personal light
  measurements.
- **Systematic one-at-a-time parameter sweeps** over published ranges:

| Parameter | Published | Range swept |
|---|---|---|
| α₀ | 0.05 | 0.01–0.19 |
| β | 0.0075 | 0.0025–0.0200 |
| p | 0.6 | 0.1–1.0 |
| μ | 0.13 | 0.01–0.30 |
| q | 0.33 | 0.15–1.00 |
| k | 0.55 | 0.15–0.95 |
| G | 33.75 | derived from α₀, β — excluded |
| I₀ | 9500 | fixed (0.7 when using CS) |

- **Result:** the originally published values were within ±10% of the best achievable
  accuracy across the datasets, so no re-fitting was justified.
- **Benchmark accuracy:** MAE ≈ 1 h for both Kronauer99 and Forger99 on independent
  ambulatory data (error < 1 h in 53% and 54% of subjects respectively); their revised
  CS-oscillator model reached MAE ≈ 0.61–0.79 h with 75–88% of subjects within 1 h.

That ~1 h MAE figure is a realistic accuracy expectation for this class of model on
real-world ambulatory light data.

### 7.6 Estimating phase from data

Where the goal is to infer a person's current phase from measurements rather than
predict forward:

- **Level-set Kalman filtering / Bayesian state-space estimation.** A framework
  integrating multi-timescale physiological data from wearables to estimate circadian
  phase *and its uncertainty*, using a state estimation method called the level set
  Kalman filter. Reported to outperform previous phase-estimation methods, and to permit
  attributing estimation error to different noise sources — finding internal noise
  unrelated to external stimuli to be a crucial factor. Published in *SIAM J Appl Math*
  ([DOI](https://doi.org/10.1137/22m1509680)), preprint
  [arXiv:2207.09406](https://arxiv.org/abs/2207.09406).
  **[Author list not verified in this review.]**
- **Particle filtering** is also used for ambulatory phase estimation, with accuracy
  reported to depend on initialisation, recording duration, and light exposure.

### 7.7 Practical numerical notes

- **Phase wrapping.** Integrate phase unwrapped; wrap to [0, 24) only when evaluating
  periodic functions or reporting. Wrapping the integration state corrupts multi-stage
  Runge–Kutta steps that straddle a cycle boundary.
- **Amplitude singularity.** The Hannay19 phase equation contains an explicit `1/R`
  term and is singular at R = 0. Integration must guard against amplitude approaching
  zero — which is exactly what strong stimuli drive it toward.
- **Discontinuous inputs.** Integrate piecewise across light-schedule breakpoints (§7.1).
- **Reporting shifts.** A phase shift is conventionally reported *relative to the
  free-running drift* over the same interval, not as raw phase change, so that the
  passage of time is not counted as a shift.

---

## 8. Individual variation

| Parameter | Value | Source |
|---|---|---|
| Intrinsic period τ | **24.18 h** mean | Czeisler 1999 ([DOI](https://doi.org/10.1126/science.284.5423.2177)) |

Czeisler et al.'s result overturned an earlier consensus and is worth stating precisely:
intrinsic period averages **24.18 h in both young and older individuals**, with a tight
distribution comparable to other species, and **does not shorten with age**. Earlier
estimates (medians around 25 h, ranges of 13–65 h) were artefacts of subjects being
exposed to light levels sufficient to confound period estimation.

Other sources of inter-individual variation reported across the PRC literature: PRC
amplitude, prior light history, season, and chronotype. Youngstedt et al. found no
significant age or sex difference in the exercise PRC.

---

## 9. Experimental protocols behind the data

Understanding the protocols explains what the numbers do and do not mean.

- **Constant routine (CR).** Extended wakefulness, semi-recumbent posture, dim light,
  evenly distributed caloric intake — removes the masking effects of sleep, posture and
  activity so that endogenous phase can be measured. Used pre- and post-stimulus to
  compute a phase shift as a difference (Khalsa 2003, St Hilaire 2012).
- **Forced desynchrony.** Scheduling day lengths far from 24 h (e.g. 20 h or 28 h) so
  the pacemaker cannot entrain, allowing intrinsic period to be estimated free of light
  confounds (Czeisler 1999).
- **Ultradian light–dark cycles.** Short alternating light/dark blocks (e.g. 2.5 h light
  / 1.5 h dark in dim light) used to distribute light exposure evenly while a drug is
  administered (Burgess 2008, 2010).
- **Placebo subtraction.** Each subject's shift under drug minus their own shift under
  placebo (a free-run), isolating the drug effect (Burgess 2008, 2010).
- **Calibrated ambulatory light measurement.** Real-world validation requires
  device-specific calibration; wrist-worn sensors misrepresent corneal light exposure,
  and uncalibrated consumer devices show substantial inter-device variability
  (Rea 2022).

---

## 10. Open problems

1. **Duration–response is under-determined.** Two published light PRC durations; a
   proper duration-response function needs three or more.
2. **Marker conversion injects error** — roughly ±1 h for PRCs reported in clock time.
3. **Non-photic coefficients are not widely reproduced.** The St Hilaire 2007 non-photic
   parameters are not carried in most open reference implementations.
4. **Meal timing and temperature lack usable human central-pacemaker PRCs.**
5. **Caffeine has one measured point, not a curve.**
6. **Population averages throughout.** PRC amplitude varies with age, light history,
   season and genotype; almost none of this is parameterised in published models.
7. **Real-world accuracy plateaus near 1 h MAE** on ambulatory data — the limiting
   factor appears to be light-exposure measurement as much as model structure.

---

## 11. References

All records located via **PubMed** unless otherwise noted.

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
18. Wearable data assimilation to estimate the circadian phase. *SIAM J Appl Math*. [DOI](https://doi.org/10.1137/22m1509680); preprint: A level set Kalman filter approach to estimate the circadian phase and its uncertainty from wearable data, [arXiv:2207.09406](https://arxiv.org/abs/2207.09406). **[Author list not verified.]**

**Software referenced:** Arcascope `circadian` — open-source Python implementations of
the Forger99, Jewett99 and Hannay19 models, used here as a transcription cross-check
(<https://github.com/Arcascope/circadian>). The primary publications remain the source
of truth.
