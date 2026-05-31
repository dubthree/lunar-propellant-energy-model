"""Tests for the Sobol variance-based sensitivity analysis."""

from lpem.sobol import route_inputs, sobol


def test_first_order_sum_bounded_and_total_at_least_one():
    # Sobol invariants: sum of first-order indices <= ~1, sum of total-effect >= ~1
    # (the excess over 1 is interaction). Allow estimator noise.
    idx = sobol("h2_reduction", n=2048)
    sum_si = sum(x.first_order for x in idx)
    sum_sti = sum(x.total_effect for x in idx)
    assert sum_si <= 1.10
    assert sum_sti >= 0.90


def test_total_effect_at_least_first_order():
    # For each input, total effect should be >= first order up to estimator noise.
    for x in sobol("mre", n=2048):
        assert x.total_effect >= x.first_order - 0.05


def test_water_route_dominated_by_lh2_liquefaction():
    idx = sobol("water_mining", n=2048)  # sorted by total effect
    assert "LH2" in idx[0].input_label
    assert idx[0].total_effect > 0.5


def test_mre_dominated_by_reactor_loss_or_voltage_latent():
    top2 = " ".join(x.input_label for x in sobol("mre", n=2048)[:2])
    assert "reactor heat loss" in top2 or "latent:severity_mre" in top2


def test_h2_reduction_has_meaningful_interaction_variance():
    # The heating term is multiplicative (feed x cp x dT), so first-order indices sum
    # well below 1 while total-effects sum to ~1: interactions are real here.
    idx = sobol("h2_reduction", n=4096)
    sum_si = sum(x.first_order for x in idx)
    sum_sti = sum(x.total_effect for x in idx)
    assert sum_sti - sum_si > 0.1  # at least 10% of variance from interactions


def test_route_inputs_uses_latent_only_for_electrochemical_routes():
    assert any("severity" in str(k) for k in route_inputs("mre"))
    assert not any("severity" in str(k) for k in route_inputs("h2_reduction"))
