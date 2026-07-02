"""Tests for the low-grade compute-waste-heat offset model."""

import math

import pytest

import lpem.waste_heat as wh
from lpem import params as P
from lpem.params import Param
from lpem.waste_heat import (
    heat_balance,
    offset_summary,
    offsettable_kwh_per_kg_o2,
    supportable_caveat_lines,
)


def test_water_route_fully_offsettable_above_sublimation():
    # A reject temperature above the ~273 K sublimation target serves the whole
    # thermal-mining term; the water route has the largest offsettable fraction.
    s = offset_summary(t_reject_k=350.0)
    water = s["water_mining"]
    assert water.offsettable_kwh_per_kg_o2 > 1.5  # ~2 kWh/kg O2
    assert water.fraction_of_total > max(
        s[k].fraction_of_total for k in ("h2_reduction", "carbothermal", "mre", "molten_salt")
    )


def test_regolith_routes_barely_offsettable():
    # High-grade reduction/electrolysis heat cannot be served by ~350 K waste heat;
    # only the cold preheat slice is, a small fraction of each route.
    s = offset_summary(t_reject_k=350.0)
    for k in ("carbothermal", "mre", "molten_salt"):
        assert s[k].fraction_of_total < 0.05


def test_offsettable_monotonic_in_reject_temperature():
    lo = offsettable_kwh_per_kg_o2("h2_reduction", 300.0)
    hi = offsettable_kwh_per_kg_o2("h2_reduction", 400.0)
    assert hi > lo  # a hotter source serves a larger slice


def test_water_route_zero_offset_below_feed_temperature():
    # A reject temperature at/below the PSR floor cannot drive anything.
    assert offsettable_kwh_per_kg_o2("water_mining", 40.0) == 0.0


def test_heat_balance_small_compute_covers_pilot_water_plant():
    # ~12 kW of compute waste heat should cover a 50 t/yr water plant's low-grade demand.
    hb = heat_balance("water_mining", compute_kw=12.0, annual_o2_kg=50_000.0)
    assert hb.covered_fraction == pytest.approx(1.0, abs=0.15)
    assert hb.reactor_mass_saved_t > 0
    # demand is modest: a few kW for a 50 t/yr plant.
    assert hb.low_grade_demand_kw < 20.0


def test_heat_balance_supportable_o2_scales_with_compute():
    a = heat_balance("water_mining", 10.0, 50_000.0)
    b = heat_balance("water_mining", 20.0, 50_000.0)
    assert b.o2_supportable_kg_yr == pytest.approx(2 * a.o2_supportable_kg_yr, rel=1e-6)


def test_heat_balance_zero_offset_is_infinite_support():
    # A route with no offsettable demand (reject below feed temp) supports unbounded O2.
    hb = heat_balance("water_mining", 10.0, 50_000.0, t_reject_k=40.0)
    assert math.isinf(hb.o2_supportable_kg_yr)


# --- Delivery physics: approach delta-T, effectiveness, latent-credit threshold ---

def test_offset_decreases_with_approach_delta_t(monkeypatch):
    # A larger approach delta-T lowers the usable source temperature, so the served
    # sensible slice (and the offset) shrinks.
    monkeypatch.setattr(wh, "DT_APPROACH", Param(5.0, 5.0, 5.0))
    small_approach = offsettable_kwh_per_kg_o2("h2_reduction", 350.0)
    monkeypatch.setattr(wh, "DT_APPROACH", Param(40.0, 40.0, 40.0))
    large_approach = offsettable_kwh_per_kg_o2("h2_reduction", 350.0)
    assert large_approach < small_approach


def test_effectiveness_scales_offset_linearly(monkeypatch):
    # With the served slice fixed (t_src stays above the sublimation target), halving the
    # exchanger effectiveness halves the delivered offset exactly.
    monkeypatch.setattr(wh, "HX_EFFECTIVENESS", Param(0.90, 0.90, 0.90))
    hi = offsettable_kwh_per_kg_o2("water_mining", 350.0)
    monkeypatch.setattr(wh, "HX_EFFECTIVENESS", Param(0.45, 0.45, 0.45))
    lo = offsettable_kwh_per_kg_o2("water_mining", 350.0)
    assert lo == pytest.approx(0.5 * hi, rel=1e-9)


def test_sublimation_credit_is_a_discrete_step_at_the_pinched_threshold(monkeypatch):
    # The latent sublimation credit requires t_reject - DT_APPROACH >= T_sub. Straddling
    # that threshold by a hair produces a discrete jump (the sensible part barely moves),
    # equal to the sublimation enthalpy times effectiveness: a genuine latent step.
    monkeypatch.setattr(wh, "DT_APPROACH", Param(15.0, 15.0, 15.0))
    t_sub = P.T_SUBLIMATION.nominal  # 273 K
    just_clears = offsettable_kwh_per_kg_o2("water_mining", t_sub + 15.0 + 0.001)   # t_src just above
    just_misses = offsettable_kwh_per_kg_o2("water_mining", t_sub + 15.0 - 0.001)   # t_src just below
    assert just_clears - just_misses > 0.8  # ~ sublimation enthalpy (~0.98) * effectiveness (0.85)


def test_sublimation_credit_present_at_nominal_reject_temperatures():
    # At the nominal 330 K reject (and the paper's 350 K), t_reject - DT_APPROACH still
    # clears the 273 K sublimation target, so the water route keeps its latent credit.
    for t_reject in (330.0, 350.0):
        assert offsettable_kwh_per_kg_o2("water_mining", t_reject) > 1.5


def test_heat_balance_exposes_conduction_caveat_and_contact_area():
    # The supportable-throughput figure must travel with its energy-balance-upper-bound
    # caveat and the illustrative (large) bed-contact area that conduction implies.
    hb = heat_balance("water_mining", 12.0, 50_000.0, t_reject_k=350.0)
    assert hb.contact_area_m2 > 100.0  # order 10^3 m^2: conduction, not energy, binds
    lines = supportable_caveat_lines(hb)
    assert any("conduction" in ln.lower() for ln in lines)
    assert any("upper bound" in ln.lower() for ln in lines)
