"""Route definitions.

Each route composes the shared stage functions under the common system boundary
(see the design spec). A route is a function `fn(draw) -> RouteResult`, where
`draw(param)` resolves a `Param` to a scalar (its nominal, or a Monte-Carlo sample;
see `model.py`). Keeping routes declarative and stage logic shared is what makes the
cross-route comparison honest: differences come from parameters, not from
inconsistent accounting.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import constants as C
from . import params as P
from . import stages as S


def _standing_loss(draw, param):
    """A continuous standing/environmental heat-loss term, honoring the loss-free flag.

    `Draw(..., exclude_standing_loss=True)` zeroes every continuous heat-loss term so a
    route can be evaluated in its loss-free configuration. This is used to cross-check the
    H2-reduction route against Leger 2025: the route is built bottom-up, and its LOSS-FREE
    total matches Leger's 24.3 kWh/kg LOX, which suggests Leger's full-chain figure also
    omits a continuous standing loss. The headline table charges the loss symmetrically to
    every hot route (H2 included). Resolvers without the flag (tornado, Sobol) fall through
    to the drawn value via getattr's default.
    """
    if getattr(draw, "exclude_standing_loss", False):
        return 0.0
    return draw(param)


def _thermal(draw, value):
    """A high-grade heat term a solar concentrator could supply for free at a sunlit site.

    Under `Draw(..., solar_thermal=True)` the thermal terms (sensible/fusion heating,
    reaction enthalpy, reactor standing loss) cost zero ELECTRICAL energy: they are supplied
    by solar-thermal concentrators, not resistive heaters. Electrochemical (faradaic,
    electrolysis) and cryogenic (liquefaction) terms are unaffected. The PSR water route
    never sets this flag (a permanently shadowed crater has no sun), so it stays on the
    baseline electrical basis. This is a report-only sensitivity; the default path leaves
    the flag False.
    """
    return 0.0 if getattr(draw, "solar_thermal", False) else value


@dataclass
class RouteResult:
    """Energy breakdown for one route, on a per-kg-O2 basis."""

    name: str
    yields: str  # "LOX" or "LOX+LH2"
    breakdown: dict  # stage name -> kWh per kg O2
    h2_coproduct: float  # kg usable H2 per kg O2 (0 for LOX-only routes)

    @property
    def total(self) -> float:
        return sum(self.breakdown.values())

    @property
    def total_per_kg_propellant(self) -> float:
        """kWh per kg of delivered cryo-propellant (LOX, plus LH2 if co-produced)."""
        return self.total / (1.0 + self.h2_coproduct)


# ---------------------------------------------------------------------------
# Regolith oxygen routes (LOX only; hydrogen fuel still from Earth)
# ---------------------------------------------------------------------------

def h2_reduction(draw) -> RouteResult:
    """A. Hydrogen reduction of ilmenite/regolith. Validation anchor (Leger 2025)."""
    feed = S.feed_per_kg_o2(draw(P.YIELD_H2_REDUCTION))
    dT = draw(P.T_REACT_H2_REDUCTION) - draw(P.T_FEED_REGOLITH)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    b = {
        "excavation": S.excavation_kwh(feed, draw(P.EXCAVATION_KWH_PER_KG_REGOLITH)),
        "heating": _thermal(draw, S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t)),
        "reaction": _thermal(draw, S.reaction_enthalpy_kwh(draw(P.REACTION_ENTHALPY_H2_REDUCTION))),
        # Standing loss is charged SYMMETRICALLY, like every other hot route. The route is
        # built bottom-up (excavation + heating + reaction + electrolysis + liquefaction);
        # its LOSS-FREE total matches Leger 2025's 24.3 kWh/kg LOX, which suggests Leger's
        # full-chain figure also omits a continuous standing loss. So rather than exempting
        # H2 (the old, inconsistent treatment), we charge it the shared REACTOR_STANDING_LOSS
        # in the headline and validate against Leger on the loss-free path
        # (Draw(..., exclude_standing_loss=True)). See _standing_loss and test_validation.
        "reactor_loss": _thermal(draw, _standing_loss(draw, P.REACTOR_STANDING_LOSS)),
        # H2 is recycled internally (FeTiO3 + H2 -> Fe + TiO2 + H2O; the water is split,
        # H2 returns to the reduction loop). This stage is the electrolysis energy to
        # liberate the O2; the route is LOX-only (no net H2 product).
        "water_electrolysis": S.water_electrolysis_kwh(draw(P.ELECTROLYSIS_EFFICIENCY)),
        "cleanup": draw(P.CLEANUP_KWH_PER_KG_O2),
        "compression": draw(P.COMPRESSION_KWH_PER_KG_O2),
        "liquefaction": S.liquefaction_kwh(1.0, draw(P.LIQUEFACTION_LOX)),
    }
    return RouteResult("H2 reduction (ilmenite)", "LOX", b, h2_coproduct=0.0)


def carbothermal(draw) -> RouteResult:
    """B. Carbothermal reduction (CH4 recycle). Published thermally; recast electrical."""
    feed = S.feed_per_kg_o2(draw(P.YIELD_CARBOTHERMAL))
    dT = draw(P.T_REACT_CARBOTHERMAL) - draw(P.T_FEED_REGOLITH)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    b = {
        "excavation": S.excavation_kwh(feed, draw(P.EXCAVATION_KWH_PER_KG_REGOLITH)),
        "heating": _thermal(draw, S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t)),
        "reaction": _thermal(draw, S.reaction_enthalpy_kwh(draw(P.REACTION_ENTHALPY_CARBOTHERMAL))),
        "reactor_loss": _thermal(draw, _standing_loss(draw, P.REACTOR_STANDING_LOSS)),
        # In the CH4-recycle flowsheet the liberated O ends up in water (methanation +
        # reforming loop) which is electrolyzed; H2/CH4 are recycled, O2 is the product.
        "water_electrolysis": S.water_electrolysis_kwh(draw(P.ELECTROLYSIS_EFFICIENCY)),
        "cleanup": draw(P.CLEANUP_KWH_PER_KG_O2),
        "compression": draw(P.COMPRESSION_KWH_PER_KG_O2),
        "liquefaction": S.liquefaction_kwh(1.0, draw(P.LIQUEFACTION_LOX)),
    }
    return RouteResult("Carbothermal (CH4)", "LOX", b, h2_coproduct=0.0)


def molten_regolith_electrolysis(draw) -> RouteResult:
    """C. Molten Regolith Electrolysis. First-principles estimate (no published kWh/kg)."""
    feed = S.feed_per_kg_o2(draw(P.YIELD_MRE))
    dT = draw(P.T_REACT_MRE) - draw(P.T_FEED_REGOLITH)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    b = {
        "excavation": S.excavation_kwh(feed, draw(P.EXCAVATION_KWH_PER_KG_REGOLITH)),
        "heating": _thermal(draw, S.heating_kwh(
            feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t,
            fusion_kj_per_kg=draw(P.FUSION_REGOLITH), melt_fraction=1.0,
        )),
        "reactor_loss": _thermal(draw, _standing_loss(draw, P.REACTOR_STANDING_LOSS)),
        "faradaic": S.faradaic_kwh(*S.coupled_voltage_efficiency(
            draw, P.V_CELL_MRE, P.CURRENT_EFFICIENCY_OXIDE, "severity_mre")),
        "cleanup": draw(P.CLEANUP_KWH_PER_KG_O2),
        "compression": draw(P.COMPRESSION_KWH_PER_KG_O2),
        "liquefaction": S.liquefaction_kwh(1.0, draw(P.LIQUEFACTION_LOX)),
    }
    return RouteResult("Molten regolith electrolysis", "LOX", b, h2_coproduct=0.0)


def molten_salt_electrolysis(draw) -> RouteResult:
    """D. Molten-salt / FFC Cambridge electrolysis (sub-melt, solid-state in salt)."""
    feed = S.feed_per_kg_o2(draw(P.YIELD_MOLTEN_SALT))
    dT = draw(P.T_REACT_MOLTEN_SALT) - draw(P.T_FEED_REGOLITH)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    b = {
        "excavation": S.excavation_kwh(feed, draw(P.EXCAVATION_KWH_PER_KG_REGOLITH)),
        # No regolith fusion: FFC operates below the regolith melting point.
        "heating": _thermal(draw, S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t)),
        "reactor_loss": _thermal(draw, _standing_loss(draw, P.REACTOR_STANDING_LOSS)),
        "faradaic": S.faradaic_kwh(*S.coupled_voltage_efficiency(
            draw, P.V_CELL_MOLTEN_SALT, P.CURRENT_EFFICIENCY_SALT, "severity_molten_salt")),
        "cleanup": draw(P.CLEANUP_KWH_PER_KG_O2),
        "compression": draw(P.COMPRESSION_KWH_PER_KG_O2),
        "liquefaction": S.liquefaction_kwh(1.0, draw(P.LIQUEFACTION_LOX)),
    }
    return RouteResult("Molten-salt (FFC Cambridge)", "LOX", b, h2_coproduct=0.0)


# ---------------------------------------------------------------------------
# Polar water route (full propellant: LOX + LH2)
# ---------------------------------------------------------------------------

def water_mining(draw) -> RouteResult:
    """E. PSR water mining + electrolysis -> LOX + LH2 (the only full-propellant route).

    Charged symmetrically with the hot routes: imperfect vapor capture (CAPTURE_EFFICIENCY),
    cryogenic excavation of ice-cemented regolith (ICY_EXCAVATION_SPECIFIC_ENERGY), a PSR
    environmental standing loss (PSR_STANDING_LOSS), and the ice-side thermal chain (ice
    sensible heat + captured-water reconditioning). It keeps the corrections that run in the
    water route's favor: cryo-range regolith cp (CP_REGOLITH_CRYO, not the hot-route mean).
    """
    cap = draw(P.CAPTURE_EFFICIENCY)
    dT = draw(P.T_SUBLIMATION) - draw(P.T_FEED_PSR)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    # Dry-regolith throughput per kg O2 (already includes the 1/capture-efficiency factor).
    regolith = S.water_regolith_per_kg_o2(draw(P.ICE_GRADE), cap)
    b = {
        "excavation": S.excavation_kwh(regolith, draw(P.ICY_EXCAVATION_SPECIFIC_ENERGY) / C.KJ_PER_KWH),
        "thermal_mining": S.thermal_mining_kwh(
            draw(P.ICE_GRADE), draw(P.CP_REGOLITH_CRYO), draw(P.CP_ICE), dT, draw(P.RECUP_PSR), e2t, cap,
        ),
        "psr_standing_loss": _standing_loss(draw, P.PSR_STANDING_LOSS),
        "reconditioning": draw(P.WATER_RECONDITIONING),
        "water_electrolysis": S.water_electrolysis_kwh(draw(P.ELECTROLYSIS_EFFICIENCY)),
        "cleanup": draw(P.CLEANUP_KWH_PER_KG_O2),
        "compression": draw(P.COMPRESSION_KWH_PER_KG_O2),
        "liquefaction_lox": S.liquefaction_kwh(1.0, draw(P.LIQUEFACTION_LOX)),
        "liquefaction_lh2": S.liquefaction_kwh(C.H2_PER_KG_O2, draw(P.LIQUEFACTION_LH2)),
    }
    return RouteResult("PSR water mining", "LOX+LH2", b, h2_coproduct=C.H2_PER_KG_O2)


ROUTES = {
    "h2_reduction": h2_reduction,
    "carbothermal": carbothermal,
    "mre": molten_regolith_electrolysis,
    "molten_salt": molten_salt_electrolysis,
    "water_mining": water_mining,
}
