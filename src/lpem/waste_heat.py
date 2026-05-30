"""Low-grade compute-waste-heat offset for lunar ISRU.

Backbone for the companion whitepaper "Compute waste heat as a low-grade thermal offset
for lunar ISRU". The premise, and its hard limit, is thermodynamic grade:

  A heat source can only supply a demand at a LOWER temperature. Compute/GPU waste heat
  rejects at ~315-350 K. So it can drive the LOW-grade ISRU demands (PSR water-ice
  sublimation, which needs heat at ~273 K; and the cold slice of feedstock preheating)
  but NOT the high-grade reduction/electrolysis heat (800-1900 C). This module quantifies
  only the offsettable (low-grade) portion. It does not claim to replace high-grade heat.

Everything is expressed per kg O2, electrical-equivalent (the electrical heating energy
the waste heat displaces), so it plugs straight into the rest of `lpem`.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import params as P
from . import stages as S
from .arch import FSP_SPECIFIC_MASS, HOURS_PER_YEAR
from .model import Draw

# Per-route thermal structure for the grade split. Regolith routes heat solid feed from
# T_feed up to T_react (sensible, the offsettable part is the slice below the reject
# temperature). The water route's heat demand is the thermal-mining term, whose target
# is the sublimation temperature; if the reject temperature exceeds it, the whole term
# is offsettable.
_REGOLITH_ROUTES = {
    "h2_reduction": (P.YIELD_H2_REDUCTION, P.T_REACT_H2_REDUCTION),
    "carbothermal": (P.YIELD_CARBOTHERMAL, P.T_REACT_CARBOTHERMAL),
    "mre": (P.YIELD_MRE, P.T_REACT_MRE),
    "molten_salt": (P.YIELD_MOLTEN_SALT, P.T_REACT_MOLTEN_SALT),
}


def offsettable_kwh_per_kg_o2(route_key: str, t_reject_k: float, draw: Draw | None = None) -> float:
    """Electrical-equivalent kWh/kg O2 that a heat source at `t_reject_k` can displace.

    For regolith routes: the sensible heating from feed temperature up to
    min(T_react, t_reject). For the water route: the full thermal-mining term if the
    reject temperature reaches the sublimation target, else a proportional slice.
    """
    d = draw or Draw(None)
    cp = d(P.CP_REGOLITH)
    e2t = d(P.ELECTRIC_TO_THERMAL_EFF)

    if route_key in _REGOLITH_ROUTES:
        yield_param, treact_param = _REGOLITH_ROUTES[route_key]
        feed = S.feed_per_kg_o2(d(yield_param))
        t_feed = d(P.T_FEED_REGOLITH)
        t_react = d(treact_param)
        recup = d(P.RECUP_REGOLITH)
        dt_offset = max(0.0, min(t_react, t_reject_k) - t_feed)
        # Fusion (for MRE) is at the melt point, far above any waste-heat grade, so it is
        # never offsettable; only the sensible slice is.
        return S.heating_kwh(feed, cp, dt_offset, recup, e2t)

    if route_key == "water_mining":
        t_feed = d(P.T_FEED_PSR)
        t_sub = d(P.T_SUBLIMATION)
        recup = d(P.RECUP_PSR)
        if t_reject_k <= t_feed:
            return 0.0
        full = S.thermal_mining_kwh(d(P.ICE_GRADE), cp, t_sub - t_feed, recup, e2t)
        if t_reject_k >= t_sub:
            return full  # source hot enough to drive the whole sublimation chain
        # Partial: only the sensible regolith heating up to the reject temperature is
        # served; the sublimation enthalpy (delivered at t_sub) is not.
        sensible_full = S.thermal_mining_kwh(d(P.ICE_GRADE), cp, t_sub - t_feed, recup, e2t)
        served_fraction = (t_reject_k - t_feed) / (t_sub - t_feed)
        # Approximate: scale the sensible portion only. Sublimation enthalpy excluded.
        return sensible_full * served_fraction * 0.5  # conservative; sublimation excluded

    raise KeyError(route_key)


@dataclass
class OffsetResult:
    route: str
    offsettable_kwh_per_kg_o2: float
    route_total_kwh_per_kg_o2: float

    @property
    def fraction_of_total(self) -> float:
        return self.offsettable_kwh_per_kg_o2 / self.route_total_kwh_per_kg_o2


def offset_summary(t_reject_k: float = 350.0) -> dict[str, OffsetResult]:
    """Per-route low-grade offset (nominal), with the fraction of route total it covers."""
    from .model import evaluate  # local import to avoid a cycle at module load

    out = {}
    for key in ("water_mining", *_REGOLITH_ROUTES):
        offset = offsettable_kwh_per_kg_o2(key, t_reject_k)
        total = evaluate(key, n=1).nominal  # nominal point estimate (rng unused for nominal)
        out[key] = OffsetResult(key, offset, total)
    return out


@dataclass
class HeatBalance:
    route: str
    compute_kw: float
    annual_o2_kg: float
    t_reject_k: float
    low_grade_demand_kw: float      # continuous low-grade thermal power the plant needs
    waste_heat_supply_kw: float     # continuous waste heat available (== compute_kw)
    covered_fraction: float         # fraction of the low-grade demand met by waste heat
    o2_supportable_kg_yr: float     # O2/yr whose low-grade heat this compute load could cover
    reactor_mass_saved_t: float     # FSP mass avoided by not supplying that heat electrically


def heat_balance(route_key: str, compute_kw: float, annual_o2_kg: float,
                 t_reject_k: float = 350.0) -> HeatBalance:
    """Match a compute waste-heat budget against a route's low-grade ISRU heat demand.

    All of the compute facility's rejected heat is at ~t_reject_k, hence available to any
    demand below it. The displaced electrical heating, if it had been supplied by the
    fission plant, also implies a saved reactor mass (via FSP specific mass).
    """
    offset_per_kg = offsettable_kwh_per_kg_o2(route_key, t_reject_k)
    demand_kwh_yr = offset_per_kg * annual_o2_kg
    demand_kw = demand_kwh_yr / HOURS_PER_YEAR
    supply_kw = compute_kw
    covered = 1.0 if demand_kw <= 0 else min(1.0, supply_kw / demand_kw)
    o2_supportable = float("inf") if offset_per_kg <= 0 else compute_kw * HOURS_PER_YEAR / offset_per_kg
    met_kw = min(demand_kw, supply_kw)
    reactor_mass_saved_kg = met_kw * FSP_SPECIFIC_MASS.nominal
    return HeatBalance(
        route=route_key, compute_kw=compute_kw, annual_o2_kg=annual_o2_kg, t_reject_k=t_reject_k,
        low_grade_demand_kw=demand_kw, waste_heat_supply_kw=supply_kw, covered_fraction=covered,
        o2_supportable_kg_yr=o2_supportable, reactor_mass_saved_t=reactor_mass_saved_kg / 1000.0,
    )
