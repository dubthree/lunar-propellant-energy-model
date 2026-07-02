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

from . import constants as C
from . import params as P
from . import stages as S
from .arch import FSP_SPECIFIC_MASS, HOURS_PER_YEAR
from .model import Draw
from .params import Param

# ---------------------------------------------------------------------------
# Delivery parameters (heat-exchanger reality the raw grade split omits)
# ---------------------------------------------------------------------------
# Real heat delivery is not free at the source temperature. Two effects were missing:
#   1. Approach delta-T (pinch): a finite temperature gap is needed to drive heat across
#      an exchanger, so a source rejecting at T_reject can only serve demands below the
#      USABLE source temperature T_reject - DT_APPROACH. In particular the latent
#      sublimation credit (delivered at T_sub ~ 273 K) is only available once
#      T_reject - DT_APPROACH >= T_sub, not the instant T_reject touches T_sub.
#   2. Exchanger effectiveness: a real exchanger delivers only a fraction of the ideal
#      heat, so the offset scales by HX_EFFECTIVENESS.
# Both are defined locally (this module owns them) as triangular Params so they sample
# under Monte Carlo like every other input; the nominal path returns the mode.
DT_APPROACH = Param(15.0, 5.0, 30.0, "HX approach/pinch delta-T (low-grade gas-solid delivery)")
HX_EFFECTIVENESS = Param(0.85, 0.70, 0.95, "low-grade heat-exchanger effectiveness")

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

    Delivery is not idealized. The usable source temperature is derated by an approach
    delta-T, `t_src = t_reject_k - DT_APPROACH`, so the source can only serve demands
    below `t_src`; and the delivered heat (hence the displaced electrical energy) is
    scaled by `HX_EFFECTIVENESS`.

    For regolith routes: the sensible heating from feed temperature up to
    min(T_react, t_src). For the water route: the host-regolith sensible slice up to
    min(t_src, T_sub), plus the water sublimation enthalpy once t_src >= T_sub.
    """
    d = draw or Draw(None)
    cp = d(P.CP_REGOLITH)
    e2t = d(P.ELECTRIC_TO_THERMAL_EFF)
    dt_approach = d(DT_APPROACH)
    hx_eff = d(HX_EFFECTIVENESS)
    t_src = t_reject_k - dt_approach  # usable (post-pinch) source temperature

    if route_key in _REGOLITH_ROUTES:
        yield_param, treact_param = _REGOLITH_ROUTES[route_key]
        feed = S.feed_per_kg_o2(d(yield_param))
        t_feed = d(P.T_FEED_REGOLITH)
        t_react = d(treact_param)
        recup = d(P.RECUP_REGOLITH)
        dt_offset = max(0.0, min(t_react, t_src) - t_feed)
        # Fusion (for MRE) is at the melt point, far above any waste-heat grade, so it is
        # never offsettable; only the sensible slice is.
        return hx_eff * S.heating_kwh(feed, cp, dt_offset, recup, e2t)

    if route_key == "water_mining":
        t_feed = d(P.T_FEED_PSR)
        t_sub = d(P.T_SUBLIMATION)
        recup = d(P.RECUP_PSR)
        ice_grade = d(P.ICE_GRADE)
        if t_src <= t_feed:
            return 0.0
        # Decompose the thermal-mining demand explicitly into (a) host-regolith sensible
        # heat from t_feed up to the served temperature min(t_src, t_sub), and (b) the
        # water sublimation enthalpy, delivered AT t_sub. A post-pinch source at t_src can
        # serve the sensible slice it reaches, plus the sublimation only once t_src >=
        # t_sub. This is continuous in the sensible part; the step at t_sub equals the
        # sublimation enthalpy (a genuine latent-heat threshold, not an artifact). The
        # approach delta-T means the latent credit needs T_reject - DT_APPROACH >= T_sub.
        regolith_per_kg_o2 = ((1.0 - ice_grade) / ice_grade) * C.WATER_PER_KG_O2
        served_dT = min(t_src, t_sub) - t_feed
        sensible = S.heating_kwh(regolith_per_kg_o2, cp, served_dT, recup, e2t)
        sublimation = 0.0
        if t_src >= t_sub:
            sublimation = (C.WATER_PER_KG_O2 * C.SUBLIMATION_H2O_KJ_PER_KG) / e2t / C.KJ_PER_KWH
        return hx_eff * (sensible + sublimation)

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


# ---------------------------------------------------------------------------
# Conduction rate-limit disclosure (see `heat_balance`)
# ---------------------------------------------------------------------------
# CRITICAL CAVEAT. The `o2_supportable_kg_yr` figure is an ENERGY-BALANCE UPPER BOUND, not
# a delivery design. It answers only "how much low-grade heat, in kWh/yr, does a compute
# load carry" versus "how much a plant needs". It does NOT show that heat can be moved into
# a granular icy PSR bed fast enough. Effective conductivity of granular regolith/ice in
# vacuum is k_eff ~ 0.001-0.01 W/m/K, and the driving temperature difference from a ~330-350 K
# reject stream down to the ~273 K sublimation front is only ~50-77 K. Conduction into the
# bed, unmodeled here, is the real rate limit; the supportable throughput below assumes it
# away. Read the numbers as "energy is not the binding constraint", never as a delivered rate.
SUPPORTABLE_CAVEAT = (
    "upper bound: energy balance only. Moving this heat into a granular icy bed "
    "(k_eff ~0.001-0.01 W/m/K in vacuum, ~50-77 K driving delta-T) is conduction-rate-"
    "limited, which is NOT modeled here."
)

# Illustrative bed-contact area (order of magnitude, NOT a delivery design). To push a
# thermal power P into the bed by conduction across a layer of thickness L with effective
# conductivity k_eff and driving delta-T, the interface flux is q'' = k_eff * dT / L and the
# required area is A = P / q''. The numbers below are deliberately coarse first-order inputs
# whose only purpose is to show the area is implausibly large, i.e. that conduction, not
# energy, binds. They are not a heat-exchanger sizing.
BED_K_EFF_W_PER_M_K = 0.003   # vacuum granular icy regolith effective conductivity (0.001-0.01)
BED_CONDUCTION_LENGTH_M = 0.1  # characteristic path, heated interface -> sublimation front


def _illustrative_contact_area_m2(thermal_kw: float, t_reject_k: float) -> float:
    """Order-of-magnitude bed-contact area to conduct `thermal_kw` into the icy bed.

    Driving delta-T is the reject-to-sublimation-front difference (t_reject minus the
    nominal T_sub). Assumptions (BED_K_EFF_W_PER_M_K, BED_CONDUCTION_LENGTH_M) are coarse
    and documented above; this is illustrative, not a design.
    """
    dt_drive = t_reject_k - P.T_SUBLIMATION.nominal
    if dt_drive <= 0 or thermal_kw <= 0:
        return float("inf")
    q_flux_w_per_m2 = BED_K_EFF_W_PER_M_K * dt_drive / BED_CONDUCTION_LENGTH_M
    return (thermal_kw * 1000.0) / q_flux_w_per_m2


@dataclass
class HeatBalance:
    """Energy-balance match of a compute waste-heat budget to a route's low-grade demand.

    NOTE the grade caveat: `o2_supportable_kg_yr` is an energy-balance upper bound, not a
    deliverable rate. Regolith-side conduction (see `SUPPORTABLE_CAVEAT`) is the unmodeled
    limiter; `contact_area_m2` is an order-of-magnitude illustration of how large that limit
    looms, not a heat-exchanger design.
    """

    route: str
    compute_kw: float
    annual_o2_kg: float
    t_reject_k: float
    low_grade_demand_kw: float      # continuous low-grade thermal power the plant needs
    waste_heat_supply_kw: float     # continuous waste heat available (== compute_kw)
    covered_fraction: float         # fraction of the low-grade demand met by waste heat
    o2_supportable_kg_yr: float     # ENERGY-BALANCE UPPER BOUND on O2/yr; see SUPPORTABLE_CAVEAT
    reactor_mass_saved_t: float     # FSP mass avoided by not supplying that heat electrically
    contact_area_m2: float          # illustrative bed-contact area to conduct the heat in


def heat_balance(route_key: str, compute_kw: float, annual_o2_kg: float,
                 t_reject_k: float = 350.0) -> HeatBalance:
    """Match a compute waste-heat budget against a route's low-grade ISRU heat demand.

    All of the compute facility's rejected heat is at ~t_reject_k, hence available (after
    the approach delta-T) to any demand below it. The displaced electrical heating, if it
    had been supplied by the fission plant, also implies a saved reactor mass (via FSP
    specific mass).

    IMPORTANT: `o2_supportable_kg_yr` is an ENERGY-BALANCE UPPER BOUND, not a delivery
    design. It says only that a compute load carries enough low-grade kWh/yr to match a
    plant of that size; it does NOT show the heat can be conducted into a granular icy PSR
    bed fast enough. In vacuum the bed's effective conductivity is k_eff ~0.001-0.01 W/m/K
    and the reject-to-sublimation driving delta-T is only ~50-77 K, so regolith-side
    conduction (unmodeled here) is the true rate limit. `contact_area_m2` is a coarse,
    illustrative estimate of the bed-interface area that limit implies, not a real design.
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
        contact_area_m2=_illustrative_contact_area_m2(compute_kw, t_reject_k),
    )


def supportable_caveat_lines(hb: HeatBalance) -> list[str]:
    """Ready-to-print disclosure lines for the supportable-throughput figure.

    The CLI (which this module does not own) should append these under the heat-balance
    block so the printed supportable-O2 number is never read as a deliverable rate.
    """
    return [
        f"    NOTE ({SUPPORTABLE_CAVEAT})",
        f"    illustrative bed-contact area to conduct {hb.compute_kw:g} kW in: "
        f"~{hb.contact_area_m2:,.0f} m^2 "
        f"(k_eff={BED_K_EFF_W_PER_M_K} W/m/K, L={BED_CONDUCTION_LENGTH_M} m, order-of-magnitude only)",
    ]
