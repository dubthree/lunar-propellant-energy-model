"""Tests for the bidirectional-benefit / break-even-probability analysis."""

import pytest

from lpem.benefit import estimate, radiator_area_m2


def test_radiator_area_smaller_for_colder_sink():
    # A colder environment with no solar (PSR) needs less radiator area than a warm,
    # sunlit one for the same load.
    warm = radiator_area_m2(12.0, 330.0, 300.0, 0.85, 70.0)
    cold = radiator_area_m2(12.0, 330.0, 70.0, 0.85, 0.0)
    assert cold < warm
    assert warm > 0 and cold > 0


def test_radiator_cannot_reject_when_environment_too_hot():
    import math
    # Emission cannot overcome environmental IR + absorbed solar -> infinite area.
    assert math.isinf(radiator_area_m2(12.0, 300.0, 320.0, 0.85, 200.0))


def test_break_even_nominal_is_cost_over_benefit():
    r = estimate(n=2000)
    assert r.cascade_break_even_prob_nominal == pytest.approx(
        r.integration_cost_t / r.cascade_benefit_t, rel=1e-9
    )
    assert 0.0 < r.cascade_break_even_prob_nominal < 1.0


def test_propagated_break_even_exceeds_nominal():
    # P* = cost/benefit is right-skewed, so the propagated median exceeds the nominal
    # point estimate; the nominal under-reports the break-even.
    r = estimate(n=20000)
    assert r.cascade_break_even_prob_median >= r.cascade_break_even_prob_nominal
    assert 0.0 < r.prob_cascade_worthwhile_if_colocated <= 1.0


def test_radiator_feasible_band_ordered_and_positive():
    r = estimate(n=4000)
    assert 0 < r.radiator_saved_t_per_mw_p25_feasible <= r.radiator_saved_t_per_mw_p75_feasible
    assert r.radiator_saved_t_per_mw_median_feasible > 0
    assert 0.0 <= r.frac_equatorial_infeasible < 0.5  # a meaningful fraction, not all


def test_unconditional_chain_below_break_even():
    # Honest result: the full speculative enabling chain (illustrative priors) sits below
    # the break-even, so as a standalone bet the cascade is negative expected value.
    r = estimate(n=20000)
    assert r.expected_joint_probability < r.cascade_break_even_prob_nominal
    assert r.expected_cascade_net_t < 0
