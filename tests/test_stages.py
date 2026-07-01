"""Unit checks on stage functions: dimensional sanity, monotonicity, edge cases."""

import math

import pytest

from lpem import constants as C
from lpem import stages as S


def test_water_stoichiometry_self_consistent():
    # Per kg O2: water mass = O2 + H2 masses split out of it. Self-consistent to the
    # ~6-sig-fig precision of the independently-quoted standard molar masses.
    assert math.isclose(C.WATER_PER_KG_O2, 1.0 + C.H2_PER_KG_O2, rel_tol=1e-5)
    # Known values to ~3 sig figs.
    assert math.isclose(C.WATER_PER_KG_O2, 1.1260, abs_tol=1e-3)
    assert math.isclose(C.H2_PER_KG_O2, 0.1260, abs_tol=1e-3)


def test_feed_per_kg_o2_inverse_of_yield():
    assert S.feed_per_kg_o2(0.02) == pytest.approx(50.0)
    with pytest.raises(ValueError):
        S.feed_per_kg_o2(0.0)


def test_heating_scales_linearly_with_mass_and_dT():
    base = S.heating_kwh(10, 1.0, 1000, 0.0, 1.0)
    assert S.heating_kwh(20, 1.0, 1000, 0.0, 1.0) == pytest.approx(2 * base)
    assert S.heating_kwh(10, 1.0, 2000, 0.0, 1.0) == pytest.approx(2 * base)


def test_heating_recuperation_reduces_energy():
    no_recup = S.heating_kwh(10, 1.0, 1000, 0.0, 1.0)
    half = S.heating_kwh(10, 1.0, 1000, 0.5, 1.0)
    assert half == pytest.approx(0.5 * no_recup)


def test_heating_known_value():
    # 1 kg, cp=3600 kJ/kg/K, dT=1 K, no recup, unity conversion -> exactly 1 kWh.
    assert S.heating_kwh(1.0, 3600.0, 1.0, 0.0, 1.0) == pytest.approx(1.0)


def test_heating_rejects_bad_inputs():
    with pytest.raises(ValueError):
        S.heating_kwh(1, 1, 1, 1.0, 1.0)  # recup must be < 1
    with pytest.raises(ValueError):
        S.heating_kwh(1, 1, 1, 0.0, 0.0)  # thermal_to_electric must be > 0


def test_water_electrolysis_known_value():
    # At 100% efficiency: H2_PER_KG_O2 * HHV.
    expected = C.H2_PER_KG_O2 * C.HHV_H2_KWH_PER_KG
    assert S.water_electrolysis_kwh(1.0) == pytest.approx(expected)
    # ~4.96 kWh/kg O2 theoretical floor.
    assert S.water_electrolysis_kwh(1.0) == pytest.approx(4.96, abs=0.1)
    # Lower efficiency costs more energy.
    assert S.water_electrolysis_kwh(0.5) > S.water_electrolysis_kwh(1.0)


def test_faradaic_known_value():
    # 4 e-/O2 at 2.5 V over 1/M_O2 mol/kg -> ~8.38 kWh/kg O2 at 100% current eff.
    val = S.faradaic_kwh(2.5, 1.0)
    assert val == pytest.approx(8.38, abs=0.1)
    # Faradaic energy is linear in cell voltage.
    assert S.faradaic_kwh(5.0, 1.0) == pytest.approx(2 * val)


def test_thermal_mining_richer_ice_costs_less_per_kg_o2():
    # signature: (ice_grade, cp_regolith, cp_ice, dT, recup, e2t, capture_efficiency)
    lean = S.thermal_mining_kwh(0.04, 1.0, 1.75, 200, 0.2, 0.9, 0.75)
    rich = S.thermal_mining_kwh(0.10, 1.0, 1.75, 200, 0.2, 0.9, 0.75)
    assert rich < lean  # less host regolith to heat per kg water


def test_thermal_mining_lower_capture_costs_more():
    # Poorer vapor capture means sublimating (and heating regolith for) more water per kg O2.
    good = S.thermal_mining_kwh(0.056, 0.45, 1.75, 200, 0.2, 0.9, 0.95)
    poor = S.thermal_mining_kwh(0.056, 0.45, 1.75, 200, 0.2, 0.9, 0.50)
    assert poor > good


def test_water_throughput_scales_with_capture_and_grade():
    # Sublimated water = delivered / capture efficiency.
    assert S.water_sublimated_per_kg_o2(0.5) == pytest.approx(2 * S.water_sublimated_per_kg_o2(1.0))
    # Regolith processed per kg O2 rises as grade falls and as capture efficiency falls.
    assert S.water_regolith_per_kg_o2(0.02, 0.75) > S.water_regolith_per_kg_o2(0.10, 0.75)
    assert S.water_regolith_per_kg_o2(0.056, 0.50) > S.water_regolith_per_kg_o2(0.056, 0.95)
    with pytest.raises(ValueError):
        S.water_sublimated_per_kg_o2(0.0)


def test_liquefaction_linear():
    assert S.liquefaction_kwh(2.0, 0.5) == pytest.approx(1.0)
