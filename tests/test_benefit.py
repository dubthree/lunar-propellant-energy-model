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


def test_break_even_is_cost_over_benefit():
    r = estimate(n=2000)
    assert r.cascade_break_even_prob == pytest.approx(
        r.integration_cost_t / r.cascade_benefit_t, rel=1e-9
    )
    assert 0.0 < r.cascade_break_even_prob < 1.0


def test_cascade_worthwhile_if_colocated():
    # Conditional on co-location, P(integration works) should exceed the break-even,
    # so the cascade is positive-EV once you are already co-located.
    r = estimate(n=2000)
    assert r.cascade_worthwhile_if_colocated is True
    assert r.p_integration_given_colocation > r.cascade_break_even_prob


def test_radiator_saving_band_ordered_and_positive():
    # The per-MW radiator saving is a positive, ordered Monte-Carlo band.
    r = estimate(n=4000)
    assert 0 < r.radiator_saved_t_per_mw_p5 <= r.radiator_saved_t_per_mw_p95
    assert r.radiator_saved_t_per_mw_nominal > 0


def test_unconditional_chain_below_break_even():
    # Honest result: the full speculative enabling chain (illustrative priors) sits below
    # the break-even, so as a standalone bet the cascade is negative expected value.
    r = estimate(n=20000)
    assert r.expected_joint_probability < r.cascade_break_even_prob
    assert r.expected_cascade_net_t < 0
