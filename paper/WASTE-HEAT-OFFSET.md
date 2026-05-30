# Compute Waste Heat as a Low-Grade Thermal Offset for Lunar ISRU

**A quantified, thermodynamically-bounded case: data-center / GPU waste heat can supply
the low-grade thermal demand of lunar water-ice ISRU, but not the high-grade reduction
heat. It is well-matched to the PSR water route and nearly useless for the others.**

Version 0.1 (2026-05-30). Backed by the `lpem` model in this repository
(`python -m lpem --waste-heat`). A companion architecture study (PSR co-location) is a
separate document; this paper makes only the narrow, defensible claim.

---

## 1. The idea, and its hard limit

Space compute (lunar-surface data centers, autonomy/processing hardware) generates large
quantities of waste heat that must be rejected. Lunar ISRU is thermally limited. The
tempting pitch is "use the compute waste heat to power ISRU." Stated that broadly, it is
wrong, and a reviewer will reject it on the Second Law: **heat flows only to lower
temperature.** Compute waste heat rejects at roughly **315–350 K** (GPU junctions ~360–
375 K; coolant/radiator interface lower). The reduction and electrolysis routes need
**high-grade** heat — hydrogen reduction 1073–1373 K, carbothermal ~1900 K, molten
regolith electrolysis ~1900 K, molten-salt ~1200 K. You cannot drive any of them with
350 K heat. Compute waste heat therefore **cannot replace** the dominant ISRU heat
demand.

There is exactly one exception, and it is the strategically important one.

## 2. Where grade matches: PSR water-ice sublimation

Thermal mining of polar water ice raises icy regolith from the PSR floor (~40–110 K) to
the sublimation point (~273 K) and supplies the heat of sublimation **at ~273 K**. A
heat source at 315–350 K is comfortably above that, so it is thermodynamically valid to
drive the entire water-extraction thermal chain with compute waste heat. The same is
true, marginally, of the *cold slice* of feedstock preheating for any route (from feed
temperature up to ~350 K), but that is a tiny fraction of the heat a reduction route
needs.

## 3. Method

We extend the `lpem` common-basis energy model (which already resolves each route's
heating demand against temperature) with a grade filter: given a reject temperature
`T_reject`, the **offsettable** energy is the electrical-equivalent heating a source at
`T_reject` could displace — the sensible slice from feed temperature up to
`min(T_react, T_reject)` for regolith routes, and the full thermal-mining term for the
water route when `T_reject ≥ 273 K`. High-grade reaction heat, fusion, and all
*electrical* loads (electrolysis work, liquefaction, compression) are excluded by
construction. See `src/lpem/waste_heat.py`; reproduce with `python -m lpem --waste-heat`.

## 4. Results

Offsettable low-grade thermal demand at `T_reject = 350 K` (per kg O2, electrical-
equivalent displaced; route totals from the `lpem` v0.3 baseline):

| Route | Offsettable (kWh/kg O2) | % of route total |
|---|---|---|
| **PSR water mining** | **2.08** | **14.5%** |
| H2 reduction (ilmenite) | 1.33 | 5.4% |
| Carbothermal (CH4) | 0.13 | 1.0% |
| Molten regolith electrolysis | 0.13 | 0.7% |
| Molten-salt (FFC) | 0.09 | 0.6% |

The water route is the clear beneficiary: its **entire** thermal-mining demand is
low-grade and so fully offsettable, ~14.5% of its total energy. The reduction routes
gain almost nothing (H2 reduction's 5.4% is only because its low ilmenite yield forces a
large feed mass through the cold preheat slice; the energy that matters — the 1073 K
reduction heat — is untouchable).

**Magnitude.** The constraint is not heat *quantity*; it is that the low-grade demand is
small. A 50 t O2/yr water plant needs only **~12 kW** of continuous low-grade heat, so a
~12 kW compute load covers it entirely, displacing ~12 kWe of fission heating and **~2.7 t
of landed reactor mass** (at ~225 kg/kWe). Conversely a 100 kW compute facility's rejected
heat could serve the low-grade demand of **~420 t O2/yr** of water mining — far more than
any near-term plant. Co-located compute waste heat does not merely help; it *saturates*
the low-grade ISRU heat demand.

## 5. What this is, and is not

- It **is**: a free (otherwise-dumped) heat stream that exactly covers the low-grade
  thermal demand of the PSR water route, eliminating ~14% of its production energy and
  the corresponding reactor mass, and giving a co-located compute facility a productive
  heat sink instead of a pure radiator load.
- It is **not**: a replacement for ISRU's high-grade reduction/electrolysis heat (Second
  Law), and it is **not** a large energy win in absolute terms (~1–3 kWh/kg O2). The
  value is that it is free, and that it lands specifically on the water route — the only
  route that yields complete propellant (LOX + LH2).

## 6. Limitations

- **Co-location is assumed, not shown.** Orbital data-center waste heat cannot reach the
  surface; this requires a *surface* (ideally PSR-adjacent) compute facility, and heat
  transport (heat pipes / pumped loops) from racks to the regolith, with losses not
  modeled here. The co-location architecture is treated in the separate PSR-co-location
  study.
- **Electrical loads dominate the water route** (electrolysis, LH2 liquefaction); waste
  heat does nothing for those, so the offset ceiling is ~14% regardless of how much
  compute heat is available.
- **Solar-thermal concentrators** are the obvious competing low-grade (and high-grade)
  heat source; the case for compute waste heat rests on the compute existing anyway for
  its own reasons, not on heat being scarce.
- Reject temperature is taken as a fixed 315–350 K; a real coolant loop has a glide and
  a pinch that would modestly reduce the usable fraction.

## 7. Reproduce

```
pip install -e .
python -m lpem --waste-heat           # offset table + a 50 t/yr water heat balance
pytest tests/test_waste_heat.py
```

## Sources
- `lpem` energy model (this repo) — route thermal demand split by temperature.
- Leger et al. 2025 (PNAS); NASA CFM/CryoFILL — water-route thermal mining and liquefaction.
- Colaprete et al. 2010 (LCROSS) — PSR ice grade and sublimation context.
