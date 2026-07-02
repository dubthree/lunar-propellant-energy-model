"""Tests for the bidirectional-benefit / break-even-probability analysis."""

import pytest

from lpem.benefit import (
    ABSORBED_SOLAR_EQ_WM2,
    F_SKY,
    RADIATOR_EMISSIVITY,
    SIGMA,
    T_ENV_EQ_K,
    T_REJECT_K,
    estimate,
    net_rejection_wm2,
    radiator_area_m2,
)


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


def test_net_rejection_increases_with_sky_view():
    # Monotonicity in F_sky: more cold-sky view factor means less absorbed environmental IR,
    # hence more net rejection at fixed radiator/terrain temperatures and solar load.
    low = net_rejection_wm2(330.0, 300.0, 0.85, 55.0, f_sky=0.2)
    mid = net_rejection_wm2(330.0, 300.0, 0.85, 55.0, f_sky=0.5)
    high = net_rejection_wm2(330.0, 300.0, 0.85, 55.0, f_sky=0.65)
    assert low < mid < high


def test_sunlit_panel_rejects_at_nominal_vertical_geometry():
    # With a competent vertical two-sided orientation (F_sky ~ 0.5) an OSR-class 330 K panel
    # over 300 K terrain rejects net-positive heat: the old "cannot reject" case is an
    # artifact of the horizontal-plate (zero sky view) assumption.
    q = net_rejection_wm2(
        T_REJECT_K.nominal, T_ENV_EQ_K.nominal, RADIATOR_EMISSIVITY.nominal,
        ABSORBED_SOLAR_EQ_WM2.nominal, f_sky=F_SKY.nominal,
    )
    assert q > 0


def test_horizontal_plate_recovered_at_zero_sky_view():
    # F_sky=0 must reproduce the old unity-view-to-terrain energy balance exactly, and the
    # default (no f_sky argument) must be that same horizontal-plate limit.
    t_rad, t_env, eps, solar = 330.0, 300.0, 0.85, 55.0
    old = eps * SIGMA * (t_rad**4 - t_env**4) - solar
    assert net_rejection_wm2(t_rad, t_env, eps, solar, f_sky=0.0) == pytest.approx(old, rel=1e-12)
    assert net_rejection_wm2(t_rad, t_env, eps, solar) == pytest.approx(old, rel=1e-12)


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


def test_both_feasibility_fractions_reported():
    # The two failure modes are reported SEPARATELY (the old code lumped them as one
    # 'infeasible' flag, mis-worded in the paper as "cannot reject at all"). With a
    # competently oriented vertical panel the true "cannot reject" (q<=0) fraction is
    # essentially zero; the old ~30% figure was the horizontal-plate artifact.
    r = estimate(n=8000)
    assert 0.0 <= r.frac_equatorial_cannot_reject < 0.05
    assert 0.0 <= r.frac_equatorial_area_capped < 0.5
    # backward-compat alias is exactly the sum of the two split fractions
    assert r.frac_equatorial_infeasible == pytest.approx(
        r.frac_equatorial_cannot_reject + r.frac_equatorial_area_capped, rel=1e-9
    )


def test_unconditional_chain_below_break_even():
    # Honest result: the full speculative enabling chain (illustrative priors) sits below
    # the break-even, so as a standalone bet the cascade is negative expected value.
    r = estimate(n=20000)
    assert r.expected_joint_probability < r.cascade_break_even_prob_nominal
    assert r.expected_cascade_net_t < 0
