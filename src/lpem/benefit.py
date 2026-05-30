"""Bidirectional benefit of the compute / ISRU waste-heat cascade, and a break-even
probability for whether it is worth designing in.

This captures the benefit the waste-heat-offset paper left on the table: the cascade
helps BOTH sides. The ISRU plant gets free low-grade heat (reactor mass saved); the
compute facility, sited in a permanently shadowed region (PSR), gets a cryogenic radiative
cold sink and so needs far less radiator mass than at a sunlit site. We total both in the
common currency that dominates lunar cost (landed mass, tonnes).

The benefit is only realized if a chain of enabling conditions holds (surface compute
exists, it is co-located with the water op, the water route is pursued, the heat
integration is engineered). Rather than assert those subjective probabilities, we compute
the BREAK-EVEN joint probability P* = integration_cost / benefit: if you believe the chain
is more likely than P*, designing in the heat integration pays for itself in expectation.
That is the honest, decision-useful form of "estimate the probability of the benefits".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .arch import FSP_SPECIFIC_MASS, HOURS_PER_YEAR
from .model import Draw
from .params import Param
from .waste_heat import offsettable_kwh_per_kg_o2

SIGMA = 5.670374e-8  # Stefan-Boltzmann, W/m^2/K^4

# --- Compute / radiator parameters ---
COMPUTE_KW = Param(12.0, 5.0, 50.0, "co-located surface compute load (kW); reference case")
T_REJECT_K = Param(330.0, 315.0, 360.0, "compute coolant/radiator temperature")
RADIATOR_EMISSIVITY = Param(0.85, 0.78, 0.92, "radiator IR emissivity (OSR/second-surface)")
RADIATOR_AREAL_MASS = Param(7.0, 4.0, 12.0, "deployable radiator areal mass, kg/m^2")

# Explicit radiator energy balance (replaces the opaque 'effective sink temperature').
# Net rejection per m^2 = eps*sigma*(T_rad^4 - T_env^4) - absorbed_solar. The two sites
# differ in the environmental IR temperature the radiator exchanges with, and in the
# absorbed solar flux:
# - PSR: permanent shadow (zero solar) and a cryogenic ~40-110 K terrain/sky.
# - Sunlit equator: warm terrain IR (~250-350 K seen by a vertical/oriented panel) plus
#   absorbed solar even for a sun-avoiding OSR coating (alpha~0.1 of the 1361 W/m^2
#   constant times a geometric incidence factor); the band spans good vs poor orientation.
T_ENV_PSR_K = Param(70.0, 40.0, 110.0, "PSR terrain/sky IR temperature")
T_ENV_EQ_K = Param(300.0, 250.0, 350.0, "equatorial terrain IR seen by an oriented panel")
ABSORBED_SOLAR_EQ_WM2 = Param(70.0, 25.0, 160.0, "absorbed solar on an oriented sunlit radiator (alpha*S*f)")

# --- Heat-integration cost (the thing you must build to capture the benefit) ---
INTEGRATION_MASS_T = Param(1.0, 0.4, 2.5, "heat exchanger + transport loop + dust mitigation, t")

# --- Reference ISRU plant ---
ANNUAL_O2_KG = 50_000.0  # 50 t/yr PSR water pilot

# --- Enabling-probability chain (ILLUSTRATIVE, subjective priors; tune freely) ---
# These are deliberately wide and are NOT predictions; they exist so the expected-value
# view can be computed. The headline result is the break-even P* (below), which does not
# depend on them.
P_SURFACE_COMPUTE = Param(0.40, 0.10, 0.80, "meaningful lunar-surface compute exists (illustrative)")
P_COLOCATION = Param(0.50, 0.20, 0.85, "compute sited at/near the PSR water op | it exists")
P_WATER_ROUTE = Param(0.55, 0.25, 0.85, "PSR water mining pursued (vs regolith-only)")
P_INTEGRATION_WORKS = Param(0.75, 0.50, 0.95, "heat transport/integration engineered | co-located")


def net_rejection_wm2(t_rad: float, t_env: float, emissivity: float, absorbed_solar_wm2: float) -> float:
    """Net heat a radiator panel rejects per m^2: IR emission minus environmental IR
    minus absorbed solar. Can be <= 0 if the environment is too hot / sunlit to reject at
    this radiator temperature (then the panel cannot reject there without active cooling)."""
    return emissivity * SIGMA * (t_rad**4 - t_env**4) - absorbed_solar_wm2


def radiator_area_m2(power_kw: float, t_rad: float, t_env: float,
                     emissivity: float, absorbed_solar_wm2: float = 0.0) -> float:
    """Radiator area to reject `power_kw` under an explicit energy balance."""
    q = net_rejection_wm2(t_rad, t_env, emissivity, absorbed_solar_wm2)
    if q <= 0:
        return float("inf")  # cannot reject at this temperature in this environment
    return (power_kw * 1000.0) / q


@dataclass
class BenefitResult:
    # The cascade decision (build heat-integration hardware to reuse compute heat in ISRU):
    cascade_benefit_t: float            # ISRU reactor mass saved by the low-grade heat offset
    integration_cost_t: float           # mass of the heat-integration hardware
    cascade_break_even_prob_nominal: float   # P* = cost/benefit at nominal
    cascade_break_even_prob_median: float    # P* propagated (median of cost/benefit)
    p_integration_given_colocation: float    # conditional prob the integration works | co-located
    prob_cascade_worthwhile_if_colocated: float  # P( P_integration > P* ) propagating both
    # The separate SITING benefit (put compute in a PSR for its cold sink), scale-dependent.
    # Per-MW radiator mass saved. Reported over FEASIBLE samples only (median + IQR), with
    # the infeasibility fraction as a separate headline statistic; mean/p95 are NOT reported
    # because they are dominated by the area-cap, not physics.
    radiator_saved_t_per_mw_nominal: float
    radiator_saved_t_per_mw_median_feasible: float
    radiator_saved_t_per_mw_p25_feasible: float
    radiator_saved_t_per_mw_p75_feasible: float
    frac_equatorial_infeasible: float   # fraction of sampled conditions where a sunlit
                                        # radiator at T_rad cannot reject (cap binds / q<=0)
    # The speculative UNCONDITIONAL view (full enabling chain, illustrative priors):
    expected_joint_probability: float
    expected_cascade_net_t: float       # E[chain] * cascade_benefit - cost


def _nominal(p: Param) -> float:
    return p.nominal


_A_EQ_CAP_MULT = 10.0  # cap the equatorial radiator area at this multiple of the PSR area


def _radiator_saved_t_per_mw(eps, t_rad, t_env_eq, solar_eq, t_env_psr, areal_mass):
    """Radiator mass saved (t) per MW by PSR siting, and whether the sunlit panel is feasible.

    Returns (saved_t_per_mw, feasible). As a sunlit panel nears its rejection limit its
    area diverges hyperbolically (1/q), so we cap a_eq at a fixed multiple of the PSR area
    for ALL cases (not only the q<=0 branch); without this the saving is dominated by a
    near-singular denominator and the upper percentiles become numerical artifacts. When the
    cap binds (or the panel cannot reject at all) the case is flagged infeasible, and such
    cases should be summarized by the feasibility fraction, not folded into a point estimate.
    """
    a_eq = radiator_area_m2(1000.0, t_rad, t_env_eq, eps, solar_eq)
    a_psr = radiator_area_m2(1000.0, t_rad, t_env_psr, eps, 0.0)
    cap = a_psr * _A_EQ_CAP_MULT
    feasible = a_eq <= cap  # finite and below the cap
    a_eq = min(a_eq, cap)
    return max(0.0, a_eq - a_psr) * areal_mass / 1000.0, feasible


def estimate(n: int = 20000, seed: int = 12345) -> BenefitResult:
    """Decompose the benefit and compute the cascade break-even probability.

    Two distinct benefits, deliberately NOT summed:
    1. Cascade (reuse compute waste heat in ISRU) -> ISRU reactor mass saved. This is the
       'should we build the heat-integration hardware' decision; its break-even is what we
       report.
    2. Siting (put compute in a PSR) -> radiator mass saved by the cold sink. This is a
       separate decision and scales with compute size; reported informationally. It is NOT
       a cascade benefit because a PSR already offers a cheap radiative sink.
    """
    rng = np.random.default_rng(seed)

    # 1. Cascade benefit: ISRU reactor mass saved (nominal), plus a propagated break-even.
    def _benefit_t(draw):
        offset = offsettable_kwh_per_kg_o2("water_mining", draw(T_REJECT_K), draw)
        return offset * ANNUAL_O2_KG / HOURS_PER_YEAR * draw(FSP_SPECIFIC_MASS) / 1000.0

    cascade_benefit = _benefit_t(Draw(None))
    cost = _nominal(INTEGRATION_MASS_T)
    break_even_nominal = cost / cascade_benefit if cascade_benefit > 0 else float("inf")
    p_int = _nominal(P_INTEGRATION_WORKS)

    # Propagate the break-even: P* = cost/benefit is a ratio of uncertain quantities and is
    # right-skewed, so the nominal point understates it. We report the median P* and the
    # probability the cascade is worthwhile once co-located, P(P_integration > P*).
    be_samples = np.empty(n)
    worthwhile = np.empty(n, dtype=bool)
    for i in range(n):
        d = Draw(rng)
        b = _benefit_t(d)
        c = INTEGRATION_MASS_T.sample(rng)
        pstar = c / b if b > 0 else float("inf")
        be_samples[i] = pstar
        worthwhile[i] = P_INTEGRATION_WORKS.sample(rng) > pstar

    # 2. Siting benefit: radiator mass saved per MW; feasible-only robust stats.
    rad_nominal, _ = _radiator_saved_t_per_mw(
        _nominal(RADIATOR_EMISSIVITY), _nominal(T_REJECT_K), _nominal(T_ENV_EQ_K),
        _nominal(ABSORBED_SOLAR_EQ_WM2), _nominal(T_ENV_PSR_K), _nominal(RADIATOR_AREAL_MASS),
    )
    rad_feasible = []
    infeasible = 0
    for i in range(n):
        saved, feas = _radiator_saved_t_per_mw(
            RADIATOR_EMISSIVITY.sample(rng), T_REJECT_K.sample(rng), T_ENV_EQ_K.sample(rng),
            ABSORBED_SOLAR_EQ_WM2.sample(rng), T_ENV_PSR_K.sample(rng), RADIATOR_AREAL_MASS.sample(rng),
        )
        if feas:
            rad_feasible.append(saved)
        else:
            infeasible += 1
    rad_feasible = np.array(rad_feasible) if rad_feasible else np.array([rad_nominal])

    # 3. Unconditional speculative view: full enabling chain (illustrative priors).
    joint = np.ones(n)
    for p in (P_SURFACE_COMPUTE, P_COLOCATION, P_WATER_ROUTE, P_INTEGRATION_WORKS):
        joint *= rng.triangular(p.low, p.nominal, p.high, n)
    expected_joint = float(joint.mean())

    return BenefitResult(
        cascade_benefit_t=cascade_benefit,
        integration_cost_t=cost,
        cascade_break_even_prob_nominal=break_even_nominal,
        cascade_break_even_prob_median=float(np.median(be_samples)),
        p_integration_given_colocation=p_int,
        prob_cascade_worthwhile_if_colocated=float(worthwhile.mean()),
        radiator_saved_t_per_mw_nominal=rad_nominal,
        radiator_saved_t_per_mw_median_feasible=float(np.percentile(rad_feasible, 50)),
        radiator_saved_t_per_mw_p25_feasible=float(np.percentile(rad_feasible, 25)),
        radiator_saved_t_per_mw_p75_feasible=float(np.percentile(rad_feasible, 75)),
        frac_equatorial_infeasible=infeasible / n,
        expected_joint_probability=expected_joint,
        expected_cascade_net_t=expected_joint * cascade_benefit - cost,
    )
