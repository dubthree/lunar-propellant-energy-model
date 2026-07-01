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


def test_water_route_dominated_by_standing_loss_and_lh2():
    # With the PSR environmental standing loss now charged to the water route, its wide
    # log-range shares the top of the variance decomposition with LH2 liquefaction: the two
    # largest total-effect inputs are the PSR standing loss and LH2 liquefaction.
    idx = sobol("water_mining", n=2048)  # sorted by total effect
    top2 = " ".join(x.input_label for x in idx[:2])
    assert "sublimation-zone" in top2  # PSR environmental standing loss
    assert "LH2" in top2               # LH2 liquefaction
    assert idx[0].total_effect > 0.3


def test_mre_dominated_by_reactor_loss_or_voltage_latent():
    top2 = " ".join(x.input_label for x in sobol("mre", n=2048)[:2])
    assert "reactor heat loss" in top2 or "latent:severity_mre" in top2


def test_h2_reduction_dominated_by_reactor_standing_loss():
    # Once the reactor standing loss is charged, its wide log-range dominates H2's variance.
    # It is a large ADDITIVE term, so the route becomes close to additive: total-effect
    # indices sum to ~1 and the per-input interaction terms are within estimator noise (this
    # retires the earlier, under-sampled claim of ~30% interaction variance on this route).
    idx = sobol("h2_reduction", n=4096)  # sorted by total effect
    assert "reactor heat loss" in idx[0].input_label
    assert idx[0].total_effect > 0.5
    sum_sti = sum(x.total_effect for x in idx)
    assert 0.85 <= sum_sti <= 1.15


def test_route_inputs_uses_latent_only_for_electrochemical_routes():
    assert any("severity" in str(k) for k in route_inputs("mre"))
    assert not any("severity" in str(k) for k in route_inputs("h2_reduction"))
