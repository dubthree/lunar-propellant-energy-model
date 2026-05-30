# A Common Electrical-Energy Basis for Comparing Lunar Oxygen and Propellant Production Routes

**Walter Kueffer**
Draft manuscript, version 0.1 (2026-05-30). Code, data, and all figures are reproducible
from the open-source model at https://github.com/dubthree/lunar-propellant-energy-model.

---

## Abstract

Lunar in-situ propellant production is widely proposed as the key to affordable cislunar
transport, yet the basic engineering question (which oxygen-extraction route costs the
least *energy* per kilogram of product) is hard to answer from the literature, because
published figures are reported on incompatible bases: hydrogen reduction as electrical
energy, carbothermal reduction as thermal energy, and molten regolith electrolysis (MRE)
with no published figure at all. Prior work compares subsets (Taylor and Carrier 1993
reviewed ~20 processes; Leger et al. 2025 modeled several on a common basis), but no
published comparison places all five of these routes, including the thermally-reported
carbothermal route and the two electrolysis routes that lack any published energy figure,
on a single electrical-equivalent basis with paired uncertainty propagation. We present a small, open,
uncertainty-quantified model that places five routes (hydrogen reduction, carbothermal
reduction, MRE, molten-salt electrolysis, and polar water-ice mining) on one
electrical-equivalent kWh/kg O2 basis under a single explicit system boundary, with
Monte-Carlo propagation of literature parameter ranges. We check the framework against
the one route with a clean published electrical figure (hydrogen reduction, Leger et al.
2025, 24.3 +/- 5.8 kWh/kg LOX): our nominal estimate (24.6) lands within ~1% of Leger's
central value, though our Monte-Carlo distribution is centered somewhat lower (median ~21),
so we report this as substantial interval overlap between two independent estimates rather
than a point match. We add historical and terrestrial cross-checks for MRE (Carr 1963, as
reported by Schreiner 2016; terrestrial molten-oxide electrolysis), noting these span
different system boundaries. Using a paired Monte Carlo that shares common parameters across
routes, we report dominance probabilities rather than overlapping error bars. Three findings
emerge: (1) carbothermal reduction is the most likely lowest-energy route (cheapest in 58%
of paired trials; it beats hydrogen reduction ~100% and MRE ~90% of the time but only ~75%
versus molten-salt and the water route), visible only once routes share a common basis,
though carbothermal is itself one of the routes without an independent energy anchor; (2) in
99% of trials the most energy-intensive route is either hydrogen reduction (51%) or MRE
(48%), and MRE's reputation as low-energy does not survive a realistic full-cell voltage;
(3) the polar water route, though mid-pack per kg O2, is the only route that yields a
complete LOX+LH2 propellant. A sensitivity analysis identifies the single highest-value
measurement for each route. We translate energy into required surface power and landed
fission-plant mass, and outline two companion analyses on reusing co-located compute
waste heat.

---

## 1. Introduction

The case for lunar propellant rests on energy: every process that turns regolith or polar
ice into liquid oxygen (and ideally liquid hydrogen) is energy-intensive, and surface
power is the binding constraint on any near-term architecture. Yet the comparison that
should drive route selection has never been made on equal footing. Three incompatibilities
recur in the literature:

1. **Thermal vs electrical energy are conflated.** Carbothermal reduction is reported as
   delivered thermal energy or "g O2/kWh thermal"; hydrogen reduction is reported as
   electrical kWh/kg. On the Moon both ultimately draw on the same scarce electrical
   supply, but they are not interchangeable at face value.
2. **System boundaries differ.** Some figures include excavation, beneficiation, and
   liquefaction; others count only the reactor.
3. **Two routes have no published figure at all.** Molten regolith electrolysis and
   molten-salt electrolysis are described qualitatively; their energy cost is asserted,
   not quantified.

The consequence is that capital allocation, power-plant sizing, and architecture choice
rest on a comparison that does not exist. This is a modeling gap, not a hardware gap,
which is precisely why it can be closed now, cheaply, and reproducibly. We build that
comparison and quantify its uncertainty.

## 2. Methods

### 2.1 Functional unit and system boundary

We compute the **electrical-equivalent energy in kWh per kg of O2 delivered to cryogenic
storage**, and additionally report kWh per kg of total propellant for the one route that
co-produces hydrogen. The system boundary is a fixed sequence of stages; every route
enables a subset, using the same stage sub-models, so all differences between routes arise
from parameters rather than inconsistent accounting:

excavation/acquisition -> beneficiation -> heating (sensible, plus fusion for melt routes)
-> reaction (reduction enthalpy or Faradaic electrolysis) -> product cleanup -> water
electrolysis (where the route produces H2O) -> gas compression -> liquefaction (LOX
always; LH2 where hydrogen is retained).

### 2.2 Thermal-to-electrical conversion

To compare a thermally-reported route against electrically-reported ones, all thermal
demand is converted to electrical-equivalent through an explicit electric-to-thermal
efficiency parameter (resistive heating, nominal 0.90). This single, visible knob is what
makes the comparison honest; a solar-thermal heating pathway would be a separate
sensitivity, not the baseline.

### 2.3 Uncertainty propagation

Every uncertain input is a triangular `(low, nominal, high)` distribution sourced from the
literature (the full parameter table, with a citation on every value, is in `params.py`).
A 20,000-trial Monte Carlo propagates these to a 90% interval per route. We propagate
stated literature ranges, not assumed Gaussian measurement error. The electrolysis cell
voltage and current efficiency of the electrochemical routes are sampled with a physical
anti-correlation (a shared operating-severity latent: higher current density raises voltage
and lowers efficiency together), avoiding unphysical parameter corners.

### 2.4 Ranking by paired Monte Carlo

Reading a ranking from five marginal error bars is a statistical error, because the routes
share parameters (regolith specific heat, heat recuperation, electrolysis efficiency,
liquefaction) that must take the same value in any given world. We therefore run a paired
Monte Carlo: one shared parameter draw per trial across all routes, evaluated trial by
trial, so we can report P(route A cheaper than route B) and P(route is cheapest / worst).

## 3. Validation

### 3.1 Hydrogen reduction against Leger 2025 (and a second anchor)

Hydrogen reduction is the only route with a clean published electrical figure: 24.3 +/-
5.8 kWh/kg LOX, with the reduction step ~55% and water electrolysis ~38% of the total
[leger2025]. We built our estimate bottom-up from first principles and independent
parameters; the largest tunable term (water-electrolysis efficiency) is set from an
independent SOEC source [hauch2020; iea2019], not from Leger's implied value.

- Nominal point estimate: **24.6 kWh/kg LOX**, within ~1% of Leger's central value and
  inside his 1-sigma interval [18.5, 30.1].
- The Monte-Carlo distribution is centered lower (median ~21, mean ~22): Leger's value sits
  near our 85th percentile, not our center. We therefore report agreement as substantial
  **interval overlap** between two independent estimates, not as a point match; the nominal
  coincidence to ~1% should not be over-read.
- Stage shares match: heating + reaction ~65% (Leger ~55%); water electrolysis ~30%
  (Leger ~38%).
- A second cross-check: Taylor and Carrier (1993) place the route at ~26 kWh/kg LOX
  (cross-technology range 18-35) [taylorcarrier1993].
- Because the model omits several one-signed terms (Section 9) that would raise totals, the
  nominal agreement with Leger and the lower distribution center are both consistent with the
  two estimates sharing a partial system boundary; we do not claim the absolute level is
  converged.

### 3.2 MRE against Carr 1963 and terrestrial molten-oxide electrolysis

MRE began as a pure first-principles estimate (nominal 18.5, median ~21, 90% CI [12.9,
31.5]). Because it has no published electrical figure, we cross-check it against three
sources that unavoidably use *different system boundaries*, so the agreement is weak and
bounding rather than a clean anchor: Carr (1963), as reported secondarily by Schreiner
(2016), gives ~26.4 kWh/kg O2 for lunar MRE [carr1963]; terrestrial molten-oxide
electrolysis of iron runs ~3.7-4.0 MWh/t metal, i.e. ~9 kWh/kg O2, a well-insulated lower
bound for a different chemistry [allanore2015]; and NASA reactor-sizing models place
*whole-system* figures (including Joule heating and duty cycle, which our standalone-reactor
boundary excludes) at ~50-120 kWh/kg O2 [schreiner2016]. Our estimate falls between these,
which given their ~9-120 spread is corroboration only in a loose sense. We did, however,
correct the oxide-melt current efficiency to match *measured* regolith-surrogate data
(70-90%, Ir anodes [allanore2015]) rather than an optimistic assumption, a change that
lowered MRE's estimate against the prior narrative.

These are the project's falsifiable tests (`tests/test_validation.py`). Only hydrogen
reduction has a like-for-like published electrical figure; the others are first-principles
estimates reported with wide intervals and as probabilities, not point claims.

## 4. Results

**Table 1.** Electrical-equivalent energy per route (20,000 trials).

| Route | Yields | kWh/kg O2 (nominal) | 90% CI | kWh/kg propellant |
|---|---|---|---|---|
| Carbothermal (CH4) | LOX | 13.4 | 12.3-15.5 | 13.4 |
| PSR water mining | LOX+LH2 | 14.4 | 12.8-17.3 | **12.8** |
| Molten-salt (FFC) | LOX | 15.3 | 12.2-21.6 | 15.3 |
| Molten regolith electrolysis | LOX | 18.5 (median 21) | 12.9-31.5 | 18.5 |
| H2 reduction (ilmenite) | LOX | 24.6 (median 21) | 16.9-27.6 | 24.6 |

The single value is the deterministic nominal (all parameters at their cited value). For
the right-skewed electrochemical routes the Monte-Carlo *median* differs materially:
notably MRE and hydrogen reduction share a median of ~21 kWh/kg O2, so although their
nominals differ (18.5 vs 24.6) they are statistically tied as the two most intensive routes
(Table 2). For plant sizing, prefer the median and the interval over the nominal.

![Figure 1](../results/fig-routes.png)

**Figure 1.** The five routes on a common electrical-energy basis (nominal + 90%
Monte-Carlo interval); the shaded band is Leger 2025's 1-sigma for hydrogen reduction.

**Table 2.** Paired-Monte-Carlo dominance.

| Route | P(cheapest) | P(worst) |
|---|---|---|
| Carbothermal (CH4) | 0.58 | 0.00 |
| Molten-salt (FFC) | 0.22 | 0.00 |
| PSR water mining | 0.19 | 0.00 |
| Molten regolith electrolysis | 0.02 | 0.48 |
| H2 reduction (ilmenite) | 0.00 | 0.51 |

Carbothermal beats hydrogen reduction in 100% of paired trials and MRE in ~90%. Molten-salt
and the water route trade second place and are not separable.

## 5. Sensitivity analysis

A one-at-a-time tornado analysis (each parameter swept low-to-high, all others nominal;
`python -m lpem --sensitivity <route>`) identifies the dominant uncertainty for each route
and, with it, the single highest-value measurement:

| Route | Dominant driver (swing, kWh/kg O2) | Next |
|---|---|---|
| H2 reduction | O2 yield (13.3) | heat recuperation (9.1), cp (5.3) |
| Carbothermal | reaction enthalpy (3.5) | yield (1.8), electrolysis eff (1.7); flat tornado |
| MRE | **cell voltage (15.9)** | yield (3.8), current efficiency (3.7) |
| Molten-salt | current efficiency (5.6) | cell voltage (4.5) |
| PSR water | **LH2 liquefaction (6.0)** | electrolysis eff (1.7), ice grade (1.0) |

Two practical conclusions: MRE's entire energy verdict hinges on one unmeasured number,
its full-cell decomposition voltage; pinning it with reactor data is the highest-value
measurement this model identifies. The water route's verdict hinges on small-scale LH2
liquefaction performance. The route ranking itself is robust: carbothermal's lead and the
hydrogen-reduction/MRE disadvantage survive across the parameter ranges (Section 4).

## 6. Findings

**Finding 1: Carbothermal is the most likely lowest-energy route, visible only on a common
basis.** Cheapest in 58% of paired trials; it beats hydrogen reduction in ~100% of trials
and MRE in ~90%, but only ~75% versus molten-salt and the water route, so it is the most
likely winner, not a certain one. Its high O2 yield (>20 wt%) means it heats only ~5 kg of
regolith per kg O2, versus ~50 kg for hydrogen reduction. Recast from its usual thermal
basis onto the common electrical basis, it comes out ahead, a comparison not previously
made. One caveat we state plainly: unlike hydrogen reduction and MRE, carbothermal has no
independent published energy figure, and its lead rests on an assumed high yield and a
first-principles reaction enthalpy that includes a Sabatier exotherm credit. Its lead is
robust to its *own* parameters (flat tornado, Section 5) but is model-internal pending a
measured electrical figure.

**Finding 2: Hydrogen reduction and MRE are the two most energy-intensive, and MRE's
"low energy" reputation does not survive a realistic cell voltage.** On the Monte-Carlo
median they are tied (~21 kWh/kg O2 each) and one of the two is the worst route in 99% of
trials (hydrogen reduction 51%, MRE 48%). Hydrogen reduction pays to heat ~50 kg regolith
per kg O2 at low ilmenite yield plus a separate electrolysis step; it is reliably poor.
MRE is the high-variance one (median ~21, CI [12.9, 31.5]): its Faradaic term depends on
the full decomposition voltage (~3.5 V including overpotential and ohmic drop), not the
~1.7 V thermodynamic floor, and not the 16-34 V Joule-*heating* voltages sometimes quoted
from concept papers. With measured current efficiency, MRE is the single worst route
whenever its cell voltage runs high.

**Finding 3: Per-kg-O2 scoring understates the only full-propellant route.** Polar water
mining is the only route that co-produces usable hydrogen, so it alone yields a complete
LOX+LH2 propellant rather than LOX with fuel still shipped from Earth. It is mid-pack per
kg O2 (14.4) but its value is closing the hydrogen loop, not lowest energy; the apparent
per-propellant edge (12.8) is within uncertainty and excludes small-scale LH2 liquefaction
and zero-boil-off storage.

## 7. From energy to power plant and landed mass

Energy matters through what it costs to supply. Converting kWh/kg into continuous surface
power and the landed mass of the fission-surface-power (FSP) system it implies
(`lpem.arch`), even a modest 50 t O2/yr plant requires ~85-156 kWe, comparable to NASA's
40-kWe FSP concept [fsp40kwe] scaled up (and roughly one to ~1.6 units of the later
100-kWe FY2030 target). Route choice swings landed power-system mass by
~16 t (carbothermal ~19 t vs hydrogen reduction ~35 t) for the same oxygen output. The
direction is robust; the magnitude scales with the FSP specific mass and assumes an
all-fission architecture (a solar-plus-storage plant would be dominated by night-survival
storage mass, not modeled here).

## 8. Companion analyses (compute waste-heat integration)

Two companion analyses, kept modular, examine reusing co-located compute waste heat:

- **Low-grade thermal offset** (`WASTE-HEAT-OFFSET.md`). By the Second Law, compute waste
  heat (~330 K) can supply only low-grade ISRU demand. At the nominal 350 K reject
  temperature, comfortably above the ~273 K sublimation target, it can in principle cover
  the water route's full thermal-mining term (~2.1 kWh/kg O2, ~14% of the route; Figure 2);
  this offset falls off sharply and excludes the sublimation enthalpy if compute rejects
  below ~273 K. It cannot supply high-grade reduction/electrolysis heat at all.

  ![Figure 2](../results/fig-waste-heat.png)

  **Figure 2.** Low-grade, waste-heat-offsettable energy per route (T_reject = 350 K).

- **PSR co-location** (`PSR-COLOCATION.md`). A permanently shadowed region is both a
  cryogenic radiative sink for compute and the location of the water resource. Under an
  explicit radiator energy balance, PSR siting saves a median ~46 t of radiator mass per MW
  of compute (nominal 51; 90% CI ~11-290, the wide upper tail reflecting and heuristically
  capping sunlit cases that cannot reject at all; Figure 3), and in ~18% of sampled
  conditions a sunlit 330 K radiator cannot reject at 330 K without active cooling. The
  heat cascade itself is a modest bonus (saves ~2.7 t reactor for the reference plant,
  break-even enabling probability ~38%); co-location is justified by the compute siting
  economics, not the cascade.

  ![Figure 3](../results/fig-radiator.png)

  **Figure 3.** Radiator mass saved by PSR siting vs a sunlit site (nominal ~51 t/MW).

## 9. Limitations

- Steady-state production energy, power, and FSP landed mass only; capital cost, mobility,
  comms, site logistics, and demand are out of scope.
- Omitted energy terms are one-signed (they raise totals): standing radiative loss from
  continuously hot reactors (worst for the hottest route, MRE), comminution/beneficiation,
  electrolyzer heat-rejection parasitics, and, for the water route, months-long LH2
  zero-boil-off and power delivery into permanent shadow. Absolute kWh/kg figures are best
  read as lower bounds; the ranking is more robust than the levels.
- Three of five routes lack a direct independent electrical anchor.
- O2 yield and reaction temperature are sampled independently (a residual idealization).
- Site geography and solar-thermal process heat are not modeled.

## 10. Reproducibility

```
pip install -e .
python -m lpem                 # Table 1
python -m lpem --dominance     # Table 2
python -m lpem --sensitivity mre   # Section 5 tornado
python -m lpem --plant-tonnes 50   # Section 7
python -m lpem --waste-heat --benefit   # Section 8
python scripts/make_figures.py     # Figures 1-3
pytest                         # 48 tests, incl. the validation anchors
```

## References

See `paper/REFERENCES.md` (full bibliography with DOIs/URLs) and `paper/references.bib`.
Key sources: Leger et al. 2025 (PNAS) [leger2025]; Taylor & Carrier 1993
[taylorcarrier1993]; Carr 1963 [carr1963]; Allanore 2015 (J. Electrochem. Soc.)
[allanore2015]; Schreiner et al. 2016 (Adv. Space Res.) [schreiner2016]; Kornuta et al.
2019 (REACH) [kornuta2019]; Hauch et al. 2020 (Science) [hauch2020]; Colaprete et al. 2010
(Science) [colaprete2010].
