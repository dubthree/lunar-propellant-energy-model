"""Tests for the architecture extension (power + landed mass sizing)."""

import pytest

from lpem.arch import HOURS_PER_YEAR, size_all, size_plant


def test_power_scales_linearly_with_output():
    a = size_plant("h2_reduction", 1_000, n=1000)
    b = size_plant("h2_reduction", 2_000, n=1000)
    assert b.power_kwe_nominal == pytest.approx(2 * a.power_kwe_nominal, rel=1e-9)


def test_power_matches_hand_calc():
    # power[kW] = energy[kWh/kg] * annual[kg] / (hours * availability)
    from lpem.arch import AVAILABILITY
    from lpem.model import Draw
    from lpem.routes import ROUTES
    e = ROUTES["h2_reduction"](Draw(None)).total
    annual = 50_000.0
    expected = e * annual / (HOURS_PER_YEAR * AVAILABILITY.nominal)
    s = size_plant("h2_reduction", annual, n=500)
    assert s.power_kwe_nominal == pytest.approx(expected, rel=1e-9)


def test_higher_energy_route_needs_more_power_and_mass():
    sizings = size_all(50_000, n=2000)
    h2 = sizings["h2_reduction"]
    carbo = sizings["carbothermal"]
    # H2 reduction is far more energy-intensive than carbothermal -> more power, mass.
    assert h2.power_kwe_nominal > carbo.power_kwe_nominal
    assert h2.mass_t_nominal > carbo.mass_t_nominal


def test_fsp_unit_count_consistent():
    s = size_plant("water_mining", 100_000, n=500)
    assert s.n_fsp_units_nominal == pytest.approx(s.power_kwe_nominal / 100.0, rel=1e-9)


def test_percentiles_ordered_and_positive():
    # Note: the nominal point estimate uses parameter *modes* (favorable availability,
    # mode specific-mass), while the MC mean is pulled up by right-skewed priors
    # (FSP specific mass 120/150/300). So nominal legitimately sits low, not centered;
    # we assert ordering and positivity, not that nominal lies between p5 and p95.
    for s in size_all(50_000, n=3000).values():
        assert 0 < s.power_kwe_p5 <= s.power_kwe_p95
        assert 0 < s.mass_t_p5 <= s.mass_t_p95
        assert s.power_kwe_nominal > 0 and s.mass_t_nominal > 0
        assert s.power_kwe_nominal <= s.power_kwe_p95  # nominal uses favorable params


def test_rejects_nonpositive_output():
    with pytest.raises(ValueError):
        size_plant("mre", 0)
