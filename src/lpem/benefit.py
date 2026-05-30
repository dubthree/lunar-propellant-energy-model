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
from .params import Param
from .waste_heat import offsettable_kwh_per_kg_o2

SIGMA = 5.670374e-8  # Stefan-Boltzmann, W/m^2/K^4

# --- Compute / radiator parameters ---
COMPUTE_KW = Param(12.0, 5.0, 50.0, "co-located surface compute load (kW); reference case")
T_REJECT_K = Param(330.0, 315.0, 360.0, "compute coolant/radiator reject temperature")
T_SINK_PSR_K = Param(70.0, 40.0, 110.0, "PSR effective radiative sink (cold, no solar)")
T_SINK_EQ_K = Param(300.0, 270.0, 330.0, "sunlit-site effective sink (warm terrain + solar backload)")
RADIATOR_EMISSIVITY = Param(0.90, 0.80, 0.95, "radiator emissivity")
RADIATOR_AREAL_MASS = Param(7.0, 4.0, 12.0, "deployable radiator areal mass, kg/m^2")

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


def radiator_area_m2(power_kw: float, t_reject: float, t_sink: float, emissivity: float) -> float:
    """Radiator area to reject `power_kw` at `t_reject` to a sink at `t_sink`."""
    denom = emissivity * SIGMA * (t_reject**4 - t_sink**4)
    return (power_kw * 1000.0) / denom


@dataclass
class BenefitResult:
    # The cascade decision (build heat-integration hardware to reuse compute heat in ISRU):
    cascade_benefit_t: float            # ISRU reactor mass saved by the low-grade heat offset
    integration_cost_t: float           # mass of the heat-integration hardware
    cascade_break_even_prob: float      # P* = cost / benefit; enabling chain must beat this
    p_integration_given_colocation: float  # conditional prob the integration works | co-located
    cascade_worthwhile_if_colocated: bool   # is the cascade +EV once co-location is assumed?
    # The separate SITING benefit (put compute in a PSR for its cold sink), scale-dependent:
    radiator_saved_t_at_ref: float      # at the reference compute load
    radiator_saved_t_per_mw: float      # scaling: ~t of radiator saved per MW of compute
    # The speculative UNCONDITIONAL view (full enabling chain, illustrative priors):
    expected_joint_probability: float
    expected_cascade_net_t: float       # E[chain] * cascade_benefit - cost


def _nominal(p: Param) -> float:
    return p.nominal


def _radiator_saved_t(power_kw: float) -> float:
    eps = _nominal(RADIATOR_EMISSIVITY)
    tr = _nominal(T_REJECT_K)
    a_eq = radiator_area_m2(power_kw, tr, _nominal(T_SINK_EQ_K), eps)
    a_psr = radiator_area_m2(power_kw, tr, _nominal(T_SINK_PSR_K), eps)
    return max(0.0, a_eq - a_psr) * _nominal(RADIATOR_AREAL_MASS) / 1000.0


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
    # 1. Cascade benefit: ISRU reactor mass saved.
    offset_per_kg = offsettable_kwh_per_kg_o2("water_mining", _nominal(T_REJECT_K))
    isru_kwe_saved = offset_per_kg * ANNUAL_O2_KG / HOURS_PER_YEAR
    cascade_benefit = isru_kwe_saved * _nominal(FSP_SPECIFIC_MASS) / 1000.0
    cost = _nominal(INTEGRATION_MASS_T)
    break_even = cost / cascade_benefit if cascade_benefit > 0 else float("inf")
    p_int = _nominal(P_INTEGRATION_WORKS)

    # 2. Siting benefit: radiator mass saved (reference + per-MW scaling).
    rad_ref = _radiator_saved_t(_nominal(COMPUTE_KW))
    rad_per_mw = _radiator_saved_t(1000.0)

    # 3. Unconditional speculative view: full enabling chain (illustrative priors).
    rng = np.random.default_rng(seed)
    joint = np.ones(n)
    for p in (P_SURFACE_COMPUTE, P_COLOCATION, P_WATER_ROUTE, P_INTEGRATION_WORKS):
        joint *= rng.triangular(p.low, p.nominal, p.high, n)
    expected_joint = float(joint.mean())

    return BenefitResult(
        cascade_benefit_t=cascade_benefit,
        integration_cost_t=cost,
        cascade_break_even_prob=break_even,
        p_integration_given_colocation=p_int,
        cascade_worthwhile_if_colocated=p_int > break_even,
        radiator_saved_t_at_ref=rad_ref,
        radiator_saved_t_per_mw=rad_per_mw,
        expected_joint_probability=expected_joint,
        expected_cascade_net_t=expected_joint * cascade_benefit - cost,
    )
