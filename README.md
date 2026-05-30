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

- [`paper/PAPER.md`](paper/PAPER.md) — the core model, route rankings, and validation.
- [`paper/WASTE-HEAT-OFFSET.md`](paper/WASTE-HEAT-OFFSET.md) — a quantified, Second-Law-safe
  case that compute/GPU waste heat can supply the *low-grade* thermal demand of PSR water
  mining (but not high-grade reduction heat). Backed by `lpem.waste_heat`.
- [`paper/PSR-COLOCATION.md`](paper/PSR-COLOCATION.md) — a separate, more speculative
  architecture position: PSRs as a shared compute heat-rejection + water-resource hub.

## Results

```
Route                         Yields   kWh/kg O2 (nom)  90% CI (O2)  kWh/kg propellant
Carbothermal (CH4)            LOX      13.4             12.3-15.5    13.4
PSR water mining              LOX+LH2  14.4             12.8-17.3    12.8
Molten-salt (FFC Cambridge)   LOX      15.3             12.2-21.6    15.3
Molten regolith electrolysis  LOX      18.5             12.9-31.5    18.5
H2 reduction (ilmenite)       LOX      24.6             16.9-27.6    24.6
```

Paired Monte Carlo (which route is cheapest / worst, sharing parameters across routes):
carbothermal is cheapest in 58% of trials; H2 reduction and MRE are the most expensive
route in 51% / 48% (`python -m lpem --dominance`). H2 reduction and MRE are now both
anchored to independent literature (Leger 2025 + Taylor & Carrier 1993; Carr 1963 +
terrestrial molten-oxide electrolysis).

![Route comparison](results/comparison.png)

**Headline:** carbothermal is the most energy-efficient route once all routes are on a
common electrical basis; H2 reduction and MRE are the most intensive (MRE's "low energy"
reputation does not survive a realistic full-cell voltage); and the PSR water route's
real value is that it uniquely yields fuel (LOX+LH2), not that it is lowest-energy.

These conclusions differ from v0.1: an adversarial physics review (v0.2) and a
molten-oxide-electrolysis literature review (v0.3) corrected optimistic assumptions and
added independent anchors for the H2-reduction and MRE routes. The model is built to be
moved by evidence; the git history shows it changing its mind.

## Install & run

```bash
pip install -e .              # numpy only; matplotlib optional for figures
python -m lpem                # energy comparison table
python -m lpem --dominance    # + paired-MC P(cheapest)/P(worst) per route
python -m lpem --plant-tonnes 50   # + power plant & landed-mass sizing per route
python -m lpem --waste-heat   # + low-grade compute-waste-heat offset per route
python -m lpem --benefit      # + cascade benefit & break-even probability
python -m lpem --figure results/comparison.png
python -m lpem --markdown     # tables as Markdown
pytest                        # 41 tests, including the Leger validation anchor
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
| `src/lpem/cli.py` | table / figure / markdown / plant-sizing / waste-heat output |
| `tests/` | dimensional + conservation unit tests, route sanity, arch sizing, and the Leger validation |

## Scope

Steady-state *production* energy, the **power plant size**, and **power-system landed
mass** (`lpem.arch`). Capital cost, mobility, comms, storage boil-off, site geography,
and demand are deliberately out of scope.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
