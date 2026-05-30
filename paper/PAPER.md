# A Common Electrical-Energy Basis for Lunar Propellant Production Routes

**A reproducible, uncertainty-quantified model that puts five lunar oxygen /
propellant extraction routes on one common electrical-energy basis.**

Version 0.2 (2026-05-30). Source and data: this repository. Reproduce every number
with `python -m lpem`.

---

## 1. The problem: the published numbers are not comparable

Lunar in-situ resource utilization (ISRU) is usually pitched as a propellant-supply
play: make liquid oxygen (and ideally liquid hydrogen) on the Moon so vehicles need
not haul it up Earth's gravity well. The central engineering question, "which
extraction route costs the least *energy* per kg of propellant," cannot currently be
answered from the literature, because the published figures are reported on
incompatible bases:

| Route | What is published | Problem |
|---|---|---|
| Hydrogen reduction | 24.3 ± 5.8 kWh/kg LOX (Leger et al., PNAS 2025) | full-chain **electrical**; the only clean figure |
| Carbothermal | ~50 kWh/kg O2 **thermal**, ">20 g O2/kWh" | thermal basis, not electrical; boundary unclear |
| Molten regolith electrolysis (MRE) | **no peer-reviewed kWh/kg** | unquantified |
| Molten-salt / FFC Cambridge | not cleanly published | unquantified |
| PSR water mining | ~11.3 kWh/kg O2 benchmark (Leger) | different product (yields H2 too) |

Three issues compound: (1) **thermal vs electrical** energy are conflated, though on
the Moon both come from the same scarce electrical supply; (2) the **system
boundaries** differ (some figures include excavation and liquefaction, some only the
reactor); and (3) two of the five routes have **no published figure at all**. Capital
allocation, power-plant sizing, and architecture choice all rest on a comparison that
has never been made on equal footing. The absence of a common energy metric is a
recurring theme in lunar-ISRU gap assessments (e.g. ISECG 2021).

This is a modeling gap, not a hardware gap. That is precisely why it can be closed
now, cheaply, and verifiably.

## 2. Method: one boundary, one functional unit, propagated uncertainty

We define a single system boundary as a fixed sequence of stages, and compute the
**electrical-equivalent energy in kWh per kg of O2 delivered to cryogenic storage**.
Every route enables a subset of the same stages, using the same stage sub-models, so
all differences between routes come from *parameters*, not from inconsistent
accounting.

Stages: excavation/acquisition -> beneficiation -> heating (sensible, plus fusion for
melt routes) -> reaction (reduction enthalpy or Faradaic electrolysis) -> cleanup ->
water electrolysis (where the route produces H2O) -> liquefaction (LOX always; LH2
where hydrogen is kept).

Two modeling choices make the comparison honest:

- **Thermal-to-electrical conversion.** All thermal demand is converted to
  electrical-equivalent via an explicit efficiency parameter (resistive heating,
  nominal 0.90). This is the single knob that lets a thermally-reported route
  (carbothermal) be compared to electrically-reported ones. It is exposed, not buried.
- **Uncertainty propagation.** Every uncertain input is a triangular
  `(low, nominal, high)` distribution sourced from the literature (see `params.py`).
  A 20,000-trial Monte Carlo propagates these to a 90% interval on each route. We
  propagate *stated literature ranges*, not assumed Gaussian measurement error.

The model is deliberately small: pure stage functions (`stages.py`), a declarative
route table (`routes.py`), one auditable parameter file (`params.py`), and a Monte
Carlo engine (`model.py`). A domain reviewer who disagrees with a number changes one
line in `params.py` and re-runs.

## 3. Validation against Leger 2025

The only route with a clean published electrical figure is hydrogen reduction:
**24.3 ± 5.8 kWh/kg LOX**, with the reduction step ~55% and water electrolysis ~38%
of the total (Leger et al., PNAS 2025). We built our hydrogen-reduction estimate
**bottom-up from first principles and independent literature parameters**, not fitted
to Leger: the largest tunable term (water-electrolysis efficiency) is set from an
independent source (SOEC system efficiency ~0.67), not from Leger's implied ~0.55.

- **Nominal point estimate: 24.6 kWh/kg LOX**, within ~1% of Leger's 24.3 and well
  inside his 1σ interval [18.5, 30.1].
- **90% Monte-Carlo interval [16.9, 27.6]** overlaps Leger's 1σ interval heavily and
  brackets his central value.
- **Stage shares** match: heating + reaction ≈ 65% of the total (Leger ~55%); water
  electrolysis ≈ 30% (Leger ~38%).

This is the project's falsifiable test (`tests/test_validation.py`): had the
independent model landed far from Leger, the framework would be wrong. It does not.
Honest caveats: (a) the Monte-Carlo *median* (≈21) sits below the nominal because the
O2-yield prior is right-skewed, so we report both; (b) this validates only the one
route with a published figure — the other four are first-principles estimates with no
independent anchor, which is exactly why we report them with wide uncertainty and as
probabilities rather than point claims (Section 5).

## 4. Results

`python -m lpem` (20,000 trials, seed 12345):

| Route | Yields | kWh/kg O2 (nominal) | 90% CI (O2) | kWh/kg propellant |
|---|---|---|---|---|
| Carbothermal (CH4) | LOX | 13.4 | 12.3–15.5 | 13.4 |
| PSR water mining | LOX+LH2 | 14.4 | 12.8–17.3 | **12.8** |
| Molten-salt (FFC Cambridge) | LOX | 15.3 | 13.7–18.6 | 15.3 |
| Molten regolith electrolysis | LOX | 21.9 | 17.9–29.0 | 21.9 |
| H2 reduction (ilmenite) | LOX | 24.6 | 16.9–27.6 | 24.6 |

The "nominal" column is the point estimate with every parameter at its cited value; it
is exactly reproducible and hand-checkable from `params.py`. Because several priors
(notably O2 yield) are right-skewed, the Monte-Carlo median can sit below the nominal;
the 90% interval is the honest measure of spread.

![Comparison](../results/comparison.png)

### 4b. Ranking the routes properly (paired Monte Carlo)

Reading a ranking off five overlapping error bars is a statistical error: the routes
share parameters (regolith cp, heat recuperation, electrolysis efficiency, liquefaction)
that must take the *same* value in any given world. We therefore run a **paired** Monte
Carlo — one shared parameter draw per trial across all routes — and report how often
each route is the cheapest or the most expensive (`python -m lpem --dominance`):

| Route | P(cheapest) | P(worst) |
|---|---|---|
| Carbothermal (CH4) | 0.70 | 0.00 |
| PSR water mining | 0.22 | 0.00 |
| Molten-salt (FFC Cambridge) | 0.07 | 0.00 |
| H2 reduction (ilmenite) | 0.00 | 0.36 |
| Molten regolith electrolysis | 0.00 | 0.63 |

This is the honest basis for the findings below: it tells us which orderings the
evidence supports and which are noise.

## 5. Three findings

**Finding 1 — Carbothermal is the most energy-efficient route, and it only shows once
all routes share a common electrical basis.** Carbothermal reduction is the cheapest
route in 70% of paired trials and beats hydrogen reduction and MRE essentially always
(P > 0.95). The reason is structural: its high O2 yield (>20 wt%) means it heats only
~5 kg of regolith per kg O2, versus ~50 kg for hydrogen reduction. This route's strong
"g O2/kWh" figures were previously reported only on a *thermal* basis; recast onto the
electrical basis used by every other route, it comes out ahead. That is exactly the
comparison the field could not make before.

**Finding 2 — The two most energy-intensive routes are hydrogen reduction and MRE, for
opposite structural reasons — and MRE's "low energy" reputation does not survive a
realistic cell voltage.** Together these two are the most expensive route in 99% of
trials. Hydrogen reduction (24.6) pays for heating ~50 kg of regolith per kg O2 at low
ilmenite yield, plus a separate water-electrolysis step. Molten regolith electrolysis
(21.9) is dominated by its Faradaic term: using a realistic *full* cell voltage (~3.5 V,
which includes anode/concentration overpotential and ohmic drop through a poorly
conducting oxide melt) and an oxide-melt current efficiency (~0.65, degraded by
electronic conduction and Fe³⁺/Fe²⁺ shuttling), MRE is **not** energy-competitive.
The common framing of MRE as low-energy comes from quoting near-thermodynamic voltages
(~1.7 V); that does not hold at useful current density. MRE's case must rest on its
metal co-product and on avoiding water electrolysis, not on energy. This finding is
sensitive to the assumed cell voltage, which has no published lunar-regolith value;
the wide CI [17.9, 29.0] reflects that, and pinning it down is the highest-value
measurement this model identifies.

**Finding 3 — Per-kg-O2 scoring understates the only full-propellant route, but the
advantage is narrow and boundary-dependent.** PSR water mining is the only route that
co-produces usable hydrogen, so it alone delivers a *complete* propellant (LOX + LH2)
rather than LOX with fuel still shipped from Earth. It is mid-pack per kg O2 (14.4) but,
credited for the fuel it also yields, it is competitive per kg of propellant (12.8). The
honest size of this edge is small: it is the cheapest route in only 22% of paired
trials, and the figure **excludes** two punishing, route-specific costs — small-scale
LH2 liquefaction (we use ~30 kWh/kg, far above the large-plant ~10) and months-long
zero-boil-off storage at 20 K (Carnot ceiling ~7% vs ~43% for LOX), with no lunar CFM
demo to date. The defensible claim is narrow: the water route's value is that it
*closes the hydrogen loop*, not that it is lowest-energy.

*(These conclusions differ from this project's v0.1, which ranked the water route
cheapest and called MRE energy-competitive. Those results were artifacts of optimistic
liquefaction and near-thermodynamic electrolysis assumptions; an adversarial physics
review corrected the nominals, and the conclusions changed. The model is built to be
moved by evidence — see the git history.)*

## 5b. From energy to power plant and landed mass

The energy figures only matter through what they cost to *supply*. The `lpem.arch`
module converts kWh/kg into the continuous electrical power a route needs for a target
production rate, and the landed mass of the fission-surface-power (FSP) system that
implies (~225 kg/kWe; NASA's 40 kWe concept targeted 150 but reportedly exceeded it).
Run with `python -m lpem --plant-tonnes 50`:

**Power plant for a modest 50 t O2/yr pilot:**

| Route | Power kWe (nom) | 90% CI | Power-sys mass (t) | 100-kWe units |
|---|---|---|---|---|
| Carbothermal | 85 | 79–105 | 19.2 | 0.9 |
| PSR water mining | 91 | 83–117 | 20.5 | 0.9 |
| Molten-salt (FFC) | 97 | 89–125 | 21.9 | 1.0 |
| Molten regolith electrolysis | 139 | 117–194 | 31.2 | 1.4 |
| H2 reduction (ilmenite) | 156 | 110–185 | 35.1 | 1.6 |

Two consequences fall out. First, even a *small* 50 t/yr oxygen plant consumes one to
~1.6 of NASA's planned FY2030 100-kWe reactors; production-scale ISRU implies reactor
*farms*, consistent with the CLPA 2.8 MW plant. Second, **route choice swings landed
power-system mass by ~16 tonnes** for the same oxygen output (carbothermal ~19 t vs MRE
~31 t and H2 reduction ~35 t). Landing 16 tonnes on the Moon dominates any
reactor-chemistry preference, which reframes route selection as a power-and-mass
decision, not a chemistry one — the quantitative form of the power-energetics-resource
coupling that dominates lunar-ISRU architecture.

The *magnitude* of this swing is sensitive to the FSP specific mass (it scales
linearly; at the optimistic 150 kg/kWe target the swing is ~11 t, at a heavier 350 it
is ~25 t), and this model assumes an **all-fission** architecture. A solar-plus-storage
plant would be dominated instead by regenerative-fuel-cell / battery mass for the
~14-day night, a shared term this model does not include. The *direction* (route choice
is a first-order mass driver) is robust; the exact tonnage is not.

A cross-check, reported not fitted: CLPA sizes a ~450 t/yr water plant at ~2.0 MWe;
our production-only figure is lower because the CLPA number includes mining mobility,
thermal management, comms, and margin outside this boundary (see below).

## 6. Limitations (explicit)

- **Steady-state production energy, power, and power-system mass only.** Capital cost,
  mobility, comms, site logistics, and demand are out of scope.
- **Omitted energy terms bias all totals low, in one direction.** The boundary does not
  yet include: standing radiative/conductive heat loss from continuously hot reactors
  (worst for the hottest route, MRE at ~1900 K); comminution/beneficiation grinding;
  electrolyzer/reactor heat-rejection parasitics; and, for the water route specifically,
  months-long LH2 zero-boil-off refrigeration and power delivery into the permanently
  shadowed resource. These are all one-signed (they raise energy), so the absolute kWh/kg
  figures are best read as *lower bounds*; the route *ranking* is more robust than the
  absolute levels because most omitted terms hit the already-expensive routes hardest.
- **Triangular priors, sampled independently.** Ranges encode literature spread, not
  formal measurement uncertainty. Parameters that are physically coupled (cell voltage
  vs current efficiency; O2 yield vs reaction temperature) are drawn independently, which
  can widen the tails of the electrochemical routes; treat MRE/molten-salt intervals as
  indicative, not precise. The MRE/molten-salt figures are first-principles estimates
  with no independent anchor, explicitly labeled, intended to be challenged.
- **Cell voltage and heat recuperation dominate** the MRE and regolith spreads
  respectively; both are the parameters most worth pinning down with reactor data.
- **No site geography.** The power-resource geographic decoupling at the poles (the best
  sunlight is kilometers from the ice) is not modeled; nor is solar-thermal process heat,
  which could lower the high-temperature routes' mass relative to all-electric.

## 7. Reproduce

```
pip install -e .
python -m lpem                     # the energy table above
python -m lpem --dominance         # + paired-MC P(cheapest)/P(worst)
python -m lpem --plant-tonnes 50   # + power plant & landed-mass sizing
python -m lpem --figure out.png    # the figure
pytest                             # 29 tests incl. the Leger validation
```

## Sources

Parameters trace to the captured lunar-ISRU corpus; load-bearing figures:
- Leger et al., PNAS 2025 — H2 reduction 24.3 ± 5.8 kWh/kg LOX, stage breakdown, water benchmark.
- Sierra Space / NASA JSC CaRD — carbothermal thermal figure and yields.
- Blue Origin "Blue Alchemist", Lunar Resources, Helios — MRE temperatures and status.
- Metalysis / FFC Cambridge — molten-salt voltages and O recovery.
- Colaprete et al. 2010 (LCROSS) — PSR ice grade 5.6 ± 2.9 wt%.
- NASA CFM/ZBO (Plachta; CryoFILL) — liquefaction and Carnot penalties.
- Mueller excavation review — specific excavation energy.

See `params.py` for the per-parameter citation on every number.
