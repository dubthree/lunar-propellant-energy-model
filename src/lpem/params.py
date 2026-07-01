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

import math
from dataclasses import dataclass


def _tri_ppf(u: float, a: float, c: float, b: float) -> float:
    """Inverse CDF of a triangular(a, mode=c, b) distribution at u in [0, 1]."""
    if b == a:
        return a
    fc = (c - a) / (b - a)
    if u <= fc:
        return a + math.sqrt(u * (b - a) * (c - a)) if c > a else a
    return b - math.sqrt((1.0 - u) * (b - a) * (b - c)) if b > c else b


@dataclass(frozen=True)
class Param:
    """A scalar with a triangular uncertainty range and a source note.

    If `log` is True the triangular distribution is taken in log-space (a log-triangular),
    appropriate for order-of-magnitude quantities (e.g. small-scale liquefaction energy)
    where a linear triangular would under-weight the upper decade.
    """

    nominal: float
    low: float
    high: float
    cite: str = ""
    log: bool = False

    def __post_init__(self) -> None:
        if not (self.low <= self.nominal <= self.high):
            raise ValueError(
                f"Param requires low <= nominal <= high, got "
                f"({self.low}, {self.nominal}, {self.high}) [{self.cite}]"
            )
        if self.log and self.low <= 0:
            raise ValueError(f"log Param requires low > 0 [{self.cite}]")

    def ppf(self, u: float) -> float:
        """Value at quantile u in [0, 1], honoring the mode (and log-space if set).

        Used both for sampling and for correlated (shared-latent) draws, so that
        coupled parameters still respect each parameter's mode and distribution shape.
        """
        if self.low == self.high:
            return self.nominal
        if self.log:
            return math.exp(_tri_ppf(u, math.log(self.low), math.log(self.nominal), math.log(self.high)))
        return _tri_ppf(u, self.low, self.nominal, self.high)

    def sample(self, rng) -> float:
        if self.low == self.high:
            return self.nominal
        return float(self.ppf(rng.random()))


# ---------------------------------------------------------------------------
# Shared / environmental parameters
# ---------------------------------------------------------------------------

# Regolith specific heat (kJ/kg/K). Rises with temperature (~0.8 at 200 K to ~1.4
# near 1300 K); we use a constant mass-mean. Nominal 1.15 approximates the enthalpy
# integral mean over the ~250->1300+ K range (a midpoint ~1.0 understates the high-dT
# routes). Source: Schreiner et al.; Hayne et al. 2017 lunar regolith thermophysical model.
CP_REGOLITH = Param(1.15, 0.9, 1.35, "enthalpy-mean over 250-1300 K; Hayne 2017 / Schreiner")

# Cryogenic-range regolith specific heat (kJ/kg/K), for the PSR water route ONLY. The
# CP_REGOLITH nominal (1.15) is an enthalpy mean over 250-1300 K and badly overstates cp
# at cryogenic temperatures: over the water route's 70-273 K band, silicate/regolith cp
# is far lower (Debye behaviour, ~0.3-0.6 kJ/kg/K). Using the hot-route mean here would
# unfairly penalise the water route's host-regolith sensible term, so it gets its own
# cryo-range value. Hot routes keep CP_REGOLITH. Source: Hemingway 1973 lunar-sample cp;
# Ledlow 1992 / Hayne 2017 cryogenic regolith thermophysics.
CP_REGOLITH_CRYO = Param(0.45, 0.3, 0.6, "cryo-range regolith cp, 70-273 K; Hemingway 1973 / Hayne 2017")

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

# Heat recuperation fraction: how much of the sensible heat in hot product/spent feed
# is recovered to preheat incoming feed. Solid-solid recuperation in vacuum (no carrier
# gas, no counterflow geometry, granular streams) is genuinely hard; terrestrial
# gas-solid recuperators reach ~0.5-0.6 only with elaborate multistage contacting that
# does not exist here. Nominal lowered to 0.25 to reflect that difficulty; this is one
# of the two dominant sensitivities for the regolith routes.
RECUP_REGOLITH = Param(0.25, 0.05, 0.55, "vacuum solid-solid HX; engineering estimate")
RECUP_PSR = Param(0.20, 0.05, 0.40, "engineering estimate, regolith thermal mining")

# Water electrolysis cell-plus-balance-of-plant efficiency (fraction of HHV). Set from
# an INDEPENDENT source (high-temperature SOEC system efficiency, Hauch et al. 2020 /
# IEA Future of Hydrogen 2019: ~0.65-0.75 system level) so the H2-reduction total is
# not fitted to Leger. (Leger's breakdown implies ~0.55 at the LOX-chain level; that is
# a cross-check, not the input.)
# HHV-basis: this is the electrical-to-H2 system efficiency on a higher-heating-value
# basis (the basis the HHV numerator in stages.py uses), so the two are consistent. SOEC
# stacks quote higher on an LHV/electrical basis (they import process heat); 0.70 HHV-system
# is the defensible balance-of-plant figure. Source: Hauch 2020 / IEA 2019, HHV-adjusted.
ELECTROLYSIS_EFFICIENCY = Param(0.70, 0.60, 0.85, "HHV-basis electrolysis system eff; Hauch 2020 / IEA 2019")

# Faradaic current efficiency (fraction of current that evolves O2 rather than driving
# side reactions / re-dissolution). Split by system, because they differ physically:
# - Oxide melt (MRE): MEASURED lunar-regolith-surrogate MOE with Ir/Ir-W anodes ran
#   ~70-90% and declined with time (Fe3+/Fe2+ shuttling, electronic conduction);
#   Allanore 2015 assumes ~90% for terrestrial iron MOE. Nominal 0.80 (was 0.65, which
#   was more pessimistic than the measured data).
# - Chloride salt (FFC): cleaner, higher efficiency.
CURRENT_EFFICIENCY_OXIDE = Param(0.80, 0.70, 0.90, "measured Ir-anode regolith MOE 70-90%; Allanore 2015")
CURRENT_EFFICIENCY_SALT = Param(0.75, 0.60, 0.90, "FFC molten chloride electrolysis")

# Liquefaction specific energy (kWh per kg of liquid), electrical.
# LOX at ~90 K: small-plant practical figure. LH2 at ~20 K: order-of-magnitude harder
# (Carnot 7% vs 43%). The 6-15 kWh/kg often quoted is for LARGE terrestrial plants; at
# lunar pilot throughput (single-digit t/yr, no LN2 precool infrastructure) small/lab
# liquefiers run far worse (~25-60+), so the nominal is set to a small-scale value.
# This figure bundles the ortho->para conversion load at 20 K (an LH2-specific cost not
# modeled separately). A PSR radiative cold sink can help, hence the still-wide low end.
# Log-uniform (order-of-magnitude span): a linear triangular would under-weight the
# upper decade for these "order of magnitude harder" cryogenic terms.
LIQUEFACTION_LOX = Param(0.50, 0.20, 1.00, "small-scale O2 liquefier; NASA CFM/CryoFILL", log=True)
LIQUEFACTION_LH2 = Param(30.0, 12.0, 60.0, "small-scale LH2 liquefier incl. ortho-para", log=True)

# Generic product-gas / water cleanup (kWh per kg O2). Small.
CLEANUP_KWH_PER_KG_O2 = Param(0.30, 0.10, 0.80, "drying/purification estimate")

# Product-gas compression before liquefaction (kWh per kg O2). Reactor/electrolyzer
# product comes off near or below 1 bar and must be compressed to the liquefier inlet;
# isothermal-ish compression work, with real-stage inefficiency. Applies to every route
# (the water route compresses both O2 and H2). Small but previously omitted.
COMPRESSION_KWH_PER_KG_O2 = Param(0.30, 0.15, 0.70, "gas compression to liquefier inlet")

# Electric-to-thermal efficiency: fraction of electrical input delivered as useful
# heat to the feed (resistive heater with radiation/conduction losses). This is the
# factor that puts thermally-reported routes (carbothermal) onto the common electrical
# basis: electrical = thermal_demand / ELECTRIC_TO_THERMAL_EFF. Solar-thermal heating
# would be a separate sensitivity, not this baseline.
ELECTRIC_TO_THERMAL_EFF = Param(0.90, 0.75, 0.98, "resistive heating w/ losses")

# Continuous reactor heat loss (kWh per kg O2), electrical-equivalent. A hot reactor
# (800-1900 C) radiating/conducting to its surroundings loses heat continuously,
# independent of the per-kg sensible heating; this is omitted by the sensible-heat-only
# stages. The ONLY measured carbothermal datum (NASA CaRD brassboard) implies ~63-93 kWh
# THERMAL/kg O2 for the reduction step, dominated by this loss at demonstrated (tiny)
# scale. A scaled, well-insulated plant amortizes it over far more throughput, so the
# true value is highly scale-dependent and uncertain: nominal 8 (a moderately-insulated
# scaled plant), range 2 (large well-insulated) to 30 (near the brassboard upper bound),
# log-uniform. Applied to all high-temperature routes; the low-temperature water route
# (sublimation at ~273 K) is exempt. This term is what was missing when carbothermal
# appeared "cheapest". Source: CaRD (NTRS 20230008393), de-rated for scale.
REACTOR_STANDING_LOSS = Param(8.0, 2.0, 30.0, "continuous reactor heat loss; CaRD upper bound de-rated", log=True)

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

# Full operating DECOMPOSITION cell voltage (V) = reversible potential + anode/cathode
# overpotential + concentration overpotential + ohmic (iR) drop, at the design current
# density. NOT the thermodynamic floor (~1.5-2.3 V; Allanore 2015 Fig. 6). IMPORTANT:
# this is distinct from the 16-34 V "applied voltages" in lunar MRE concept papers, which
# are Joule-HEATING voltages to keep the melt molten, not decomposition voltages. Sibille
# /Dominguez recorded electrochemical operation "below 10 V" (~6 V at 0.5 A/cm2). Nominal
# 3.5 V (mid of the 2.5-4 V full-cell band), wide range to 6 V.
V_CELL_MRE = Param(3.5, 2.2, 6.0, "MOE decomposition cell voltage; Sibille/Allanore")
V_CELL_MOLTEN_SALT = Param(3.0, 2.6, 3.6, "FFC Cambridge full cell voltage")

# --- Water route (PSR ice) ---
# Ice grade: weight fraction water in mined icy regolith. Lower bound widened to ~1 wt%
# (0.010): LCROSS returned 5.6+-2.9 wt% at Cabeus, but neutron-spectrometer and CLPA
# surveys show much of the polar cold-trap inventory sits at 1-2 wt% or lower, and a
# real plant sited on average (not best-case) terrain must survive that lean tail. This
# widens the water route's expensive tail without moving its mode; it does not change the
# ranking (the route is dominated by grade-independent electrolysis and liquefaction).
ICE_GRADE = Param(0.056, 0.010, 0.100, "LCROSS 5.6+-2.9 wt%; lean CLPA/neutron tail to ~1 wt%")
# Sublimation reach temperature (K): warm enough to drive off water under vacuum.
T_SUBLIMATION = Param(273.0, 250.0, 300.0, "thermal mining target temp")

# Vapor-capture efficiency: fraction of sublimated water actually captured (tent / cold
# trap) rather than lost to the vacuum over fissured, unconsolidated PSR terrain. Direct
# thermal mining sublimates water into vacuum and recaptures it on a cold surface; real
# capture over rubble is leaky, so to DELIVER 1 kg of water you must sublimate 1/eta kg,
# and the mining heat and regolith throughput scale by 1/eta. Nominal 0.75 (an engineering
# target for a shrouded/tented cold-trap head); wide because no lunar-relevant demonstration
# exists. This is a NEW loss charged to the water route, previously exempted. Source:
# Sowers/Dreyer thermal-mining concept; Kornuta 2019 CisLunar Marketplace capture estimates.
CAPTURE_EFFICIENCY = Param(0.75, 0.50, 0.95, "PSR vapor capture over fissured terrain; Sowers/Kornuta")

# Icy-regolith excavation specific energy (kJ per kg regolith moved). The hot routes move
# dry simulant with a bucket drum at ~79 J/kg (EXCAVATION_KWH_PER_KG_REGOLITH). Ice-cemented
# regolith at 40-110 K is NOT dry simulant: it behaves like concrete (UCS tens of MPa), and
# cutting/ripping it costs orders of magnitude more. Terrestrial rock-cutting specific
# energies run ~50-250 kJ/kg; a purely radiant thermal-mining head that sublimates in place
# (no mechanical cutting) could be far lower. This spans >2 decades, so log-triangular with a
# wide range and a moderate nominal. Applied to the water route's regolith throughput (which
# already carries the 1/capture-efficiency factor). Source: Zacny lunar-drilling/cutting data;
# terrestrial rock-mechanics specific-energy range.
ICY_EXCAVATION_SPECIFIC_ENERGY = Param(30.0, 2.0, 200.0, "icy-regolith cutting kJ/kg; Zacny / rock-mechanics", log=True)

# PSR environmental standing loss (kWh per kg O2), electrical-equivalent. The water-route
# analog of REACTOR_STANDING_LOSS: a ~273 K sublimation zone radiates continuously to the
# cold PSR sky (sigma*(273^4 - 70^4) ~ 313 W/m2) and conducts into surrounding cold regolith
# that yields no captured water. It is real and continuous, but much SMALLER than the hot
# routes' loss because the driving temperature is 273 K, not 1300-1900 K (radiation ~ T^4).
# Nominal 1.5, log-triangular 0.3 (well-shrouded, small footprint) to 8 (leaky, large
# conductive contact). Charged to the water route only. Source: radiative estimate at 273 K;
# scaled by analogy to the reactor standing-loss term.
PSR_STANDING_LOSS = Param(1.5, 0.3, 8.0, "273 K sublimation-zone radiative/conductive loss", log=True)

# Ice specific heat (kJ/kg/K), for sensible heating of the ice itself from PSR feed
# temperature to the sublimation point. Water-ice cp falls steeply with temperature
# (~1.4 near 100 K to ~2.1 near 273 K; CRC / Feistel-Wagner 2006); we use a band-mean.
# This is the ice-side sensible term the old thermal-mining model omitted (it heated only
# the dry host regolith). NOT recuperated: the water leaves the boundary as vapor.
CP_ICE = Param(1.75, 1.4, 2.1, "water-ice cp band-mean 70-273 K; CRC / Feistel-Wagner 2006")

# Captured-water reconditioning (kWh per kg O2), electrical-equivalent. Water captured on
# the cold trap refreezes (passive, radiative, ~free), then must be re-melted (latent heat
# of fusion 334 kJ/kg) and warmed to the electrolyzer feed temperature before splitting.
# Per kg O2 that is WATER_PER_KG_O2 ~ 1.13 kg of captured water: ~1.13*334/3600 ~ 0.10 kWh
# to melt, plus a small warm-up, delivered at the electric-to-thermal efficiency. Cleanup
# (drying/purification) does not cover this phase-change energy, so it is a separate small
# term. Nominal 0.12; range 0.06-0.25. Charged to the water route only. Source: CRC water
# enthalpy of fusion; engineering warm-up estimate.
WATER_RECONDITIONING = Param(0.12, 0.06, 0.25, "refreeze/re-melt (334 kJ/kg) + warm captured water")
