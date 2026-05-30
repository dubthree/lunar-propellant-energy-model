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
        "heating": S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t),
        "reaction": S.reaction_enthalpy_kwh(draw(P.REACTION_ENTHALPY_H2_REDUCTION)),
        # NOTE: no separate reactor_loss term here. Unlike the other thermochemical routes,
        # H2 reduction is calibrated to Leger 2025, whose full-chain figure already reflects
        # realistic reduction energy; adding a standing-loss term would double-count and
        # break that validation. The standing-loss correction is applied only to the routes
        # that lack an independent energy anchor (carbothermal, MRE, molten-salt).
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
        "heating": S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t),
        "reaction": S.reaction_enthalpy_kwh(draw(P.REACTION_ENTHALPY_CARBOTHERMAL)),
        "reactor_loss": draw(P.REACTOR_STANDING_LOSS),
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
        "heating": S.heating_kwh(
            feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t,
            fusion_kj_per_kg=draw(P.FUSION_REGOLITH), melt_fraction=1.0,
        ),
        "reactor_loss": draw(P.REACTOR_STANDING_LOSS),
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
        "heating": S.heating_kwh(feed, draw(P.CP_REGOLITH), dT, draw(P.RECUP_REGOLITH), e2t),
        "reactor_loss": draw(P.REACTOR_STANDING_LOSS),
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
    """E. PSR water mining + electrolysis -> LOX + LH2 (the only full-propellant route)."""
    dT = draw(P.T_SUBLIMATION) - draw(P.T_FEED_PSR)
    e2t = draw(P.ELECTRIC_TO_THERMAL_EFF)
    b = {
        "thermal_mining": S.thermal_mining_kwh(
            draw(P.ICE_GRADE), draw(P.CP_REGOLITH), dT, draw(P.RECUP_PSR), e2t,
        ),
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
