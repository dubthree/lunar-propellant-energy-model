# lpem — Lunar Propellant Energy Model

A small, reproducible, uncertainty-quantified model that places the major lunar
oxygen / propellant extraction routes on **one common electrical-energy basis**
(kWh per kg O2, and per kg of delivered propellant) under a **single explicit system
boundary**.

It exists because the published numbers are not comparable: hydrogen reduction is
reported as electrical kWh/kg, carbothermal as *thermal*, and molten regolith / molten
salt electrolysis are not published at all. This makes a rational
which-route-costs-least-energy comparison impossible. `lpem` fixes that, and validates
itself by independently reproducing the one clean published figure (Leger et al.,
PNAS 2025: 24.3 ± 5.8 kWh/kg LOX for hydrogen reduction).

## Papers (each stands independently)

- [`paper/MANUSCRIPT.md`](paper/MANUSCRIPT.md) — **draft submission manuscript**: abstract,
  methods, two-anchor validation, sensitivity, findings, figures, references; leads with the
  core model and folds in the companion analyses.
- [`paper/PAPER.md`](paper/PAPER.md) — the core model technical note, route rankings, validation.
- [`paper/WASTE-HEAT-OFFSET.md`](paper/WASTE-HEAT-OFFSET.md) — a quantified, Second-Law-safe
  case that compute/GPU waste heat can supply the *low-grade* thermal demand of PSR water
  mining (but not high-grade reduction heat). Backed by `lpem.waste_heat`.
- [`paper/PSR-COLOCATION.md`](paper/PSR-COLOCATION.md) — a separate, more speculative
  architecture position: PSRs as a shared compute heat-rejection + water-resource hub.

## Results

```
Route                         Yields   kWh/kg O2 (nom)  90% CI (O2)  kWh/kg propellant
PSR water mining              LOX+LH2  14.0             11.8-16.4    12.5
Carbothermal (CH4)            LOX      21.1             16.1-33.1    21.1
Molten-salt (FFC Cambridge)   LOX      23.3             17.9-36.2    23.3
H2 reduction (ilmenite)       LOX      24.3             16.4-27.1    24.3
Molten regolith electrolysis  LOX      26.5             20.1-42.0    26.5
```

Paired Monte Carlo (`python -m lpem --dominance`): the PSR water route is cheapest in 99%
of trials; MRE is the most likely worst. The water route wins because it is the only
low-temperature route (sublimation ~273 K), so it alone escapes the continuous reactor
heat-loss penalty (grounded in the NASA CaRD carbothermal datum, ~63-93 kWh-thermal/kg O2)
that burdens every high-temperature route. H2 reduction matches Leger 2025 (24.3); the
high-temperature routes cluster with wide, overlapping uncertainty and are not separable.

![Route comparison](results/comparison.png)

**Headline:** the PSR water route is both the most energy-efficient (cheapest in 99% of
trials) and the only full-propellant route, because it is the only low-temperature route
and so avoids the reactor heat-loss penalty that burdens every high-temperature route.

These conclusions are the product of repeated adversarial hardening (the git history shows
the model changing its mind): a 4-agent physics review (v0.2), a molten-oxide-electrolysis
literature review (v0.3), and a five-domain weakness sweep (v0.9) that closed the
carbothermal anchor gap with the NASA CaRD datum, added the reactor heat-loss term,
fixed a Monte-Carlo sampling bug, and switched order-of-magnitude priors to log-uniform.
The model is built to be moved by evidence, not to defend a prior conclusion.

## Install & run

```bash
pip install -e .              # numpy only; matplotlib optional for figures
python -m lpem                # energy comparison table
python -m lpem --dominance    # + paired-MC P(cheapest)/P(worst) per route
python -m lpem --plant-tonnes 50   # + power plant & landed-mass sizing per route
python -m lpem --waste-heat   # + low-grade compute-waste-heat offset per route
python -m lpem --benefit      # + cascade benefit & break-even probability
python -m lpem --sensitivity mre   # tornado: which parameters drive a route's uncertainty
python scripts/make_figures.py     # regenerate manuscript figures
python -m lpem --figure results/comparison.png
python -m lpem --markdown     # tables as Markdown
pytest                        # 48 tests, including the Leger validation anchor
```

## How it is organized

| File | Purpose |
|---|---|
| `src/lpem/params.py` | **the auditable parameter table** — every uncertain number with a citation; change one line, re-run |
| `src/lpem/stages.py` | pure per-stage energy functions (heating, electrolysis, Faradaic, liquefaction, ...) |
| `src/lpem/routes.py` | declarative route definitions composing the stages |
| `src/lpem/model.py` | nominal estimate + Monte-Carlo uncertainty engine |
| `src/lpem/arch.py` | architecture extension: power (kWe) + FSP landed mass for a target output |
| `src/lpem/waste_heat.py` | low-grade compute-waste-heat offset (grade-matched), backs the waste-heat paper |
| `src/lpem/benefit.py` | bidirectional benefit + break-even enabling probability for the cascade |
| `src/lpem/sensitivity.py` | one-at-a-time tornado: which parameters drive each route's uncertainty |
| `src/lpem/cli.py` | table / figure / markdown / plant-sizing / waste-heat output |
| `tests/` | dimensional + conservation unit tests, route sanity, arch sizing, and the Leger validation |

## Scope

Steady-state *production* energy, the **power plant size**, and **power-system landed
mass** (`lpem.arch`). Capital cost, mobility, comms, storage boil-off, site geography,
and demand are deliberately out of scope.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
