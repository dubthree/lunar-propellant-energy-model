"""Tests for the low-grade compute-waste-heat offset model."""

import math

import pytest

from lpem.waste_heat import heat_balance, offset_summary, offsettable_kwh_per_kg_o2


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
