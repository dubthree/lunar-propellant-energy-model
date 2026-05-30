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

Full write-up and findings: [`paper/PAPER.md`](paper/PAPER.md).

## Results

```
Route                         Yields   kWh/kg O2 (nom)  90% CI (O2)  kWh/kg propellant
Carbothermal (CH4)            LOX      13.4             12.3-15.5    13.4
PSR water mining              LOX+LH2  14.4             12.8-17.3    12.8
Molten-salt (FFC Cambridge)   LOX      15.3             13.7-18.6    15.3
Molten regolith electrolysis  LOX      21.9             17.9-29.0    21.9
H2 reduction (ilmenite)       LOX      24.6             16.9-27.6    24.6
```

Paired Monte Carlo (which route is cheapest / worst, sharing parameters across routes):
carbothermal is cheapest in 70% of trials; MRE and H2 reduction are the most expensive
route in 63% / 36% (`python -m lpem --dominance`).

![Route comparison](results/comparison.png)

**Headline:** carbothermal is the most energy-efficient route once all routes are on a
common electrical basis; H2 reduction and MRE are the most intensive (MRE's "low energy"
reputation does not survive a realistic full-cell voltage); and the PSR water route's
real value is that it uniquely yields fuel (LOX+LH2), not that it is lowest-energy.

These v0.2 conclusions differ from v0.1, which an adversarial physics review corrected
(optimistic liquefaction and near-thermodynamic electrolysis assumptions). The model is
built to be moved by evidence.

## Install & run

```bash
pip install -e .              # numpy only; matplotlib optional for figures
python -m lpem                # energy comparison table
python -m lpem --dominance    # + paired-MC P(cheapest)/P(worst) per route
python -m lpem --plant-tonnes 50   # + power plant & landed-mass sizing per route
python -m lpem --figure results/comparison.png
python -m lpem --markdown     # tables as Markdown
pytest                        # 29 tests, including the Leger validation anchor
```

## How it is organized

| File | Purpose |
|---|---|
| `src/lpem/params.py` | **the auditable parameter table** — every uncertain number with a citation; change one line, re-run |
| `src/lpem/stages.py` | pure per-stage energy functions (heating, electrolysis, Faradaic, liquefaction, ...) |
| `src/lpem/routes.py` | declarative route definitions composing the stages |
| `src/lpem/model.py` | nominal estimate + Monte-Carlo uncertainty engine |
| `src/lpem/arch.py` | architecture extension: power (kWe) + FSP landed mass for a target output |
| `src/lpem/cli.py` | table / figure / markdown / plant-sizing output |
| `tests/` | dimensional + conservation unit tests, route sanity, arch sizing, and the Leger validation |

## Scope

Steady-state *production* energy, the **power plant size**, and **power-system landed
mass** (`lpem.arch`). Capital cost, mobility, comms, storage boil-off, site geography,
and demand are deliberately out of scope.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
