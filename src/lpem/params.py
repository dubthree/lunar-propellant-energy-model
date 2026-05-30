"""Auditable parameter table.

Every uncertain input lives here as a `Param(nominal, low, high, cite)`. This is
the single file a domain reviewer needs to read to challenge the model: change a
number here, re-run, see the effect. Nothing uncertain is hard-coded in the stage
logic.

Uncertainty is represented as a triangular distribution (low, nominal, high). It is
deliberately simple and transparent: we are propagating *stated ranges from the
literature*, not claiming Gaussian measurement error.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    """A scalar with a triangular uncertainty range and a source note."""

    nominal: float
    low: float
    high: float
    cite: str = ""

    def __post_init__(self) -> None:
        if not (self.low <= self.nominal <= self.high):
            raise ValueError(
                f"Param requires low <= nominal <= high, got "
                f"({self.low}, {self.nominal}, {self.high}) [{self.cite}]"
            )

    def sample(self, rng) -> float:
        # numpy triangular(left, mode, right)
        if self.low == self.high:
            return self.nominal
        return float(rng.triangular(self.low, self.nominal, self.high))


# ---------------------------------------------------------------------------
# Shared / environmental parameters
# ---------------------------------------------------------------------------

# Regolith specific heat (kJ/kg/K). Rises with temperature (~0.8 at 200 K to ~1.4
# near 1300 K); a constant mean with a wide range is used deliberately.
# Source: Schreiner et al.; Hayne et al. 2017 lunar regolith thermophysical model.
CP_REGOLITH = Param(1.0, 0.8, 1.3, "Hayne 2017 / Schreiner regolith cp")

# Latent heat of fusion of regolith/basalt (kJ/kg), for melt-based routes (MRE).
FUSION_REGOLITH = Param(470.0, 350.0, 520.0, "basalt LoF; Ghiorso & Sack 1995, Navrotsky 2009")

# Feed temperature (K). Equatorial/mid-latitude daytime regolith feed.
T_FEED_REGOLITH = Param(250.0, 230.0, 290.0, "lunar surface daytime temp")

# PSR feed temperature (K) for the water route.
T_FEED_PSR = Param(70.0, 40.0, 110.0, "PSR floor temps, Diviner (Hayne 2017)")

# Excavation specific energy (kWh per kg regolith moved). 79 J/kg for a continuous
# bucket drum on dry simulant => 0.0000219 kWh/kg. Tiny vs thermal, included for
# completeness. Source: Mueller, extraterrestrial excavation review.
EXCAVATION_KWH_PER_KG_REGOLITH = Param(2.19e-5, 1.5e-5, 5.0e-5, "Mueller 79 J/kg drum")

# Heat recuperation fraction: how much of the sensible heat in hot product/spent
# feed is recovered to preheat incoming feed. Solid-solid recuperation is hard, so
# the range is modest. This is one of the two dominant sensitivities.
# Low end ~0.10 reflects early reactors with little heat recovery (the regime that
# produces Leger 2025's reported right tail to ~53 kWh/kg LOX).
RECUP_REGOLITH = Param(0.40, 0.10, 0.65, "engineering estimate, solid-solid HX")
RECUP_PSR = Param(0.20, 0.05, 0.40, "engineering estimate, regolith thermal mining")

# Water electrolysis cell-plus-balance-of-plant efficiency (fraction of HHV). Set from
# an INDEPENDENT source (high-temperature SOEC system efficiency, Hauch et al. 2020 /
# IEA Future of Hydrogen 2019: ~0.65-0.75 system level) so the H2-reduction total is
# not fitted to Leger. (Leger's breakdown implies ~0.55 at the LOX-chain level; that is
# a cross-check, not the input.)
ELECTROLYSIS_EFFICIENCY = Param(0.67, 0.60, 0.75, "SOEC system eff; Hauch 2020 / IEA 2019")

# Faradaic current efficiency for molten-oxide / molten-salt electrolysis (fraction
# of current that goes to O2 evolution rather than side reactions / re-dissolution).
CURRENT_EFFICIENCY = Param(0.80, 0.60, 0.95, "molten oxide electrolysis estimate")

# Liquefaction specific energy (kWh per kg of liquid), electrical.
# LOX at ~90 K: small-plant practical figure. LH2 at ~20 K: order-of-magnitude
# harder (Carnot 7% vs 43%); terrestrial best ~6, typical 10-15. A lunar radiative
# cold sink can help, hence the wide low end.
LIQUEFACTION_LOX = Param(0.50, 0.20, 1.00, "small-scale O2 liquefier; NASA CFM/CryoFILL")
LIQUEFACTION_LH2 = Param(10.0, 6.0, 15.0, "H2 liquefaction lit. range; Carnot-limited")

# Generic product-gas / water cleanup (kWh per kg O2). Small.
CLEANUP_KWH_PER_KG_O2 = Param(0.30, 0.10, 0.80, "drying/purification estimate")

# Electric-to-thermal efficiency: fraction of electrical input delivered as useful
# heat to the feed (resistive heater with radiation/conduction losses). This is the
# factor that puts thermally-reported routes (carbothermal) onto the common electrical
# basis: electrical = thermal_demand / ELECTRIC_TO_THERMAL_EFF. Solar-thermal heating
# would be a separate sensitivity, not this baseline.
ELECTRIC_TO_THERMAL_EFF = Param(0.90, 0.75, 0.98, "resistive heating w/ losses")

# Reaction temperatures (K) by route.
T_REACT_H2_REDUCTION = Param(1273.0, 1073.0, 1373.0, "800-1100 C; Leger 2025 / ESA ProSPA")
T_REACT_CARBOTHERMAL = Param(1700.0, 1600.0, 1900.0, "near/at melt; Sierra Space")
T_REACT_MRE = Param(1900.0, 1800.0, 2000.0, "~1600 C+ molten; Blue Alchemist")
T_REACT_MOLTEN_SALT = Param(1200.0, 1170.0, 1230.0, "900-950 C; FFC Cambridge")

# O2 yield as weight fraction of processed feed (kg O2 per kg feed).
YIELD_H2_REDUCTION = Param(0.020, 0.014, 0.044, "1.4-4.4 wt%; Leger/ESA ProSPA")
YIELD_CARBOTHERMAL = Param(0.20, 0.12, 0.28, ">20 wt%; Sierra/NASA JSC CaRD")
YIELD_MRE = Param(0.20, 0.10, 0.33, "fraction of ~40% O liberated; estimate")
YIELD_MOLTEN_SALT = Param(0.30, 0.18, 0.38, "up to 96% of available O; FFC")

# Reaction enthalpy beyond sensible heating (kWh per kg O2). For H2 reduction this
# covers the endothermic reduction + water-gas chemistry net of recycle. Modeled as
# a small additive term; heating dominates.
REACTION_ENTHALPY_H2_REDUCTION = Param(2.5, 1.0, 4.0, "ilmenite reduction net enthalpy")
# Net of the Sabatier exotherm credit (CO2 + 4H2 -> CH4 + 2H2O is exothermic, ~1.4
# kWh/kg O2 credit); the range spans uncertainty in the reduction endotherm and how
# the Sabatier credit is allocated across the recycle loop.
REACTION_ENTHALPY_CARBOTHERMAL = Param(3.0, 1.5, 5.0, "carbothermal net enthalpy, post-Sabatier credit")

# Electrolysis cell voltage (V) for molten-oxide / molten-salt routes (drives the
# Faradaic energy). MRE molten oxide ~2.5 V; FFC molten salt ~3.0 V.
V_CELL_MRE = Param(2.5, 2.0, 3.5, "molten oxide electrolysis cell voltage")
V_CELL_MOLTEN_SALT = Param(3.0, 2.6, 3.4, "FFC Cambridge cell voltage")

# --- Water route (PSR ice) ---
# Ice grade: weight fraction water in mined icy regolith.
ICE_GRADE = Param(0.056, 0.040, 0.100, "LCROSS 5.6+-2.9 wt%; CLPA 4-10 wt%")
# Sublimation reach temperature (K): warm enough to drive off water under vacuum.
T_SUBLIMATION = Param(273.0, 250.0, 300.0, "thermal mining target temp")
