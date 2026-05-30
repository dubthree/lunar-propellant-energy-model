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
PSR water mining              LOX+LH2  11.4             10.7-12.4    10.1
Carbothermal (CH4)            LOX      12.5             11.6-14.6    12.5
Molten regolith electrolysis  LOX      13.2             11.8-18.0    13.2
Molten-salt (FFC Cambridge)   LOX      14.0             12.4-17.2    14.0
H2 reduction (ilmenite)       LOX      20.2             15.0-24.2    20.2
```

![Route comparison](results/comparison.png)

**Headline:** the best-characterized route (H2 reduction, 20.2) is the most
energy-intensive; the *unpublished* electrolysis routes (MRE, molten-salt) are
energy-competitive (~13–14) and bounded by anode life, not energy; and per-kg-O2 scoring
structurally understates the only full-propellant route (PSR water, 10.1/kg propellant).

## Install & run

```bash
pip install -e .              # numpy only; matplotlib optional for figures
python -m lpem                # energy comparison table
python -m lpem --plant-tonnes 50   # + power plant & landed-mass sizing per route
python -m lpem --figure results/comparison.png
python -m lpem --markdown     # tables as Markdown
pytest                        # 27 tests, including the Leger validation anchor
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
