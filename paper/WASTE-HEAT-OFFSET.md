# Compute Waste Heat as a Low-Grade Thermal Offset for Lunar ISRU

**A quantified, thermodynamically-bounded case: data-center / GPU waste heat can supply
the low-grade thermal demand of lunar water-ice ISRU, but not the high-grade reduction
heat. It is well-matched to the PSR water route and nearly useless for the others.**

Version 0.2 (2026-07-01). Backed by the `lpem` model in this repository
(`python -m lpem --waste-heat`). A companion architecture study (PSR co-location) is a
separate document; this paper makes only the narrow, defensible claim. This version
derates delivery through an explicit heat-exchanger pinch and effectiveness, and updates
the route totals to the v0.13 model (which charges every route, including water, its
continuous standing losses).

---

## 1. The idea, and its hard limit

Space compute (lunar-surface data centers, autonomy/processing hardware) generates large
quantities of waste heat that must be rejected. Lunar ISRU is thermally limited. The
tempting pitch is "use the compute waste heat to power ISRU." Stated that broadly, it is
wrong, and a reviewer will reject it on the Second Law: **heat flows only to lower
temperature.** Compute waste heat rejects at roughly **315-350 K** (GPU junctions ~360-
375 K; coolant/radiator interface lower). The reduction and electrolysis routes need
**high-grade** heat, hydrogen reduction 1073-1373 K, carbothermal ~1900 K, molten
regolith electrolysis ~1900 K, molten-salt ~1200 K. You cannot drive any of them with
350 K heat. Compute waste heat therefore **cannot replace** the dominant ISRU heat
demand.

There is exactly one exception, and it is the strategically important one.

## 2. Where grade matches: PSR water-ice sublimation

Thermal mining of polar water ice raises icy regolith from the PSR floor (~40-110 K) to
the sublimation point (~273 K) and supplies the heat of sublimation **at ~273 K**. A
heat source at 315-350 K is comfortably above that, so it is thermodynamically valid to
drive the entire water-extraction thermal chain with compute waste heat. The same is
true, marginally, of the *cold slice* of feedstock preheating for any route (from feed
temperature up to ~350 K), but that is a tiny fraction of the heat a reduction route
needs.

## 3. Method

We extend the `lpem` common-basis energy model (which already resolves each route's
heating demand against temperature) with a grade filter: given a reject temperature
`T_reject`, the usable source temperature is first derated by a heat-exchanger approach
delta-T (nominal 15 K, range 5-30) and delivered heat is scaled by an exchanger
effectiveness (nominal 0.85, range 0.70-0.95). The **offsettable** energy is then the
electrical-equivalent heating that derated source could displace: the sensible slice from
feed temperature up to `min(T_react, T_src)` for regolith routes, and the full
thermal-mining term for the water route when `T_src ≥ 273 K`. High-grade reaction heat,
fusion, and all *electrical* loads (electrolysis work, liquefaction, compression) are
excluded by construction. See `src/lpem/waste_heat.py`; reproduce with
`python -m lpem --waste-heat`.

## 4. Results

Offsettable low-grade thermal demand at `T_reject = 350 K` (per kg O2, electrical-
equivalent displaced after pinch and effectiveness; route totals from the current `lpem`
model, v0.13):

| Route | Offsettable (kWh/kg O2) | % of route total |
|---|---|---|
| **PSR water mining** | **1.77** | **11.1%** |
| H2 reduction (ilmenite) | 0.96 | 3.0% |
| Carbothermal (CH4) | 0.10 | 0.5% |
| Molten regolith electrolysis | 0.10 | 0.4% |
| Molten-salt (FFC) | 0.06 | 0.3% |

The water route is the clear beneficiary: its **entire** thermal-mining demand is
low-grade and so fully offsettable (scaled only by the exchanger effectiveness), ~11% of
its total energy. The high-temperature routes gain almost nothing (the share is even
smaller than in earlier model versions, because their totals rose once continuous reactor
heat loss was charged; the low-grade preheat slice is a sliver of a larger denominator,
and the energy that matters, the 1073-1900 K reactor heat, is untouchable by a 350 K
source).

**Magnitude.** The constraint is not heat *quantity*; it is that the low-grade demand is
small. A 50 t O2/yr water plant needs only **~10 kW** of continuous low-grade heat, so a
~12 kW compute load covers it entirely, displacing that fission heating and **~2.3 t of
landed reactor mass** (at ~225 kg/kWe). Conversely, on energy grounds alone a 100 kW
compute facility's rejected heat could serve the low-grade demand of roughly **500 t
O2/yr** of water mining, far more than any near-term plant. Two caveats keep this honest.
First, these supportable-throughput figures are energy-balance upper bounds, not delivery
designs: moving the heat into a granular icy bed (effective conductivity ~0.001-0.01
W/m/K in vacuum, ~50-77 K driving delta-T) is conduction-rate-limited, and an illustrative
contact-area estimate for conducting even 12 kW into the bed is on the order of 5,000 m^2
(k_eff = 0.003 W/m/K, 0.1 m path). Delivery engineering, not energy supply, is the binding
constraint. Second, within the energy boundary, co-located compute waste heat does not
merely help; it *saturates* the low-grade ISRU heat demand.

## 5. What this is, and is not

- It **is**: a free (otherwise-dumped) heat stream that covers the low-grade thermal
  demand of the PSR water route, eliminating ~11% of its production energy and the
  corresponding reactor mass, and giving a co-located compute facility a productive heat
  sink instead of a pure radiator load.
- It is **not**: a replacement for ISRU's high-grade reduction/electrolysis heat (Second
  Law), and it is **not** a large energy win in absolute terms (~1-3 kWh/kg O2). The
  value is that it is free, and that it lands specifically on the water route, the only
  route that yields complete propellant (LOX + LH2).

## 6. Limitations

- **Co-location is assumed, not shown.** Orbital data-center waste heat cannot reach the
  surface; this requires a *surface* (ideally PSR-adjacent) compute facility, and heat
  transport (heat pipes / pumped loops) from racks to the regolith, with losses not
  modeled here. The co-location architecture is treated in the separate PSR-co-location
  study.
- **Electrical loads dominate the water route** (electrolysis, LH2 liquefaction); waste
  heat does nothing for those, so the offset ceiling is ~11% regardless of how much
  compute heat is available.
- **Delivery is conduction-limited.** The model bounds the *energy* a waste stream can
  displace; it does not design the regolith-side heat exchanger. Conducting heat into a
  granular icy bed at cryogenic temperature is severely rate-limited (see Section 4), so
  the supportable-throughput numbers are upper bounds.
- **Solar-thermal concentrators** are the obvious competing low-grade (and high-grade)
  heat source; the case for compute waste heat rests on the compute existing anyway for
  its own reasons, not on heat being scarce.
- **Reject temperature.** We take the compute coolant-loop reject as ~330 K nominal (a
  315-360 K band). The GPU *junction* is hotter (~360-375 K, i.e. ~90 C, the figure the
  program literature quotes), but the loop that actually reaches the regolith is cooler;
  this paper's reject temperature is the loop/radiator-interface value, not the junction.
  The water-route offset is insensitive to the exact value within this band: any
  post-pinch source temperature above the ~273 K sublimation target serves the *entire*
  low-grade thermal-mining slice, so the headline offset is the same at 330 K as at the
  350 K used for the table (at 330 K the derated source is ~315 K, still comfortably
  above 273 K). The pinch and exchanger effectiveness are now modeled explicitly
  (approach delta-T nominal 15 K, range 5-30; effectiveness nominal 0.85, range
  0.70-0.95); the sublimation credit vanishes if the post-pinch source falls below 273 K.

## 7. Reproduce

```
pip install -e .
python -m lpem --waste-heat           # offset table + a 50 t/yr water heat balance
pytest tests/test_waste_heat.py
```

## Sources
- `lpem` energy model (this repo), route thermal demand split by temperature.
- Leger et al. 2025 (PNAS); NASA CFM/CryoFILL, water-route thermal mining and liquefaction.
- Colaprete et al. 2010 (LCROSS), PSR ice grade and sublimation context.
