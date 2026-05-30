"""Sanity checks across all routes: finite, positive, ordered, internally consistent."""

import pytest

from lpem import compare, evaluate, evaluate_all
from lpem.routes import ROUTES


def test_all_routes_evaluate_finite_and_positive():
    results = evaluate_all(n=3000)
    assert set(results) == set(ROUTES)
    for key, r in results.items():
        assert r.nominal > 0, key
        assert all(v >= 0 for v in r.breakdown_nominal.values()), key
        # breakdown sums to the reported total
        assert pytest.approx(r.nominal) == sum(r.breakdown_nominal.values())


def test_percentiles_ordered():
    # The meaningful invariant is p5 <= p50 <= p95 and positive samples. The nominal
    # (modal point estimate) need not equal p50: right-skewed priors (e.g. O2 yield)
    # pull the MC median away from the mode, by design.
    for r in evaluate_all(n=5000).values():
        assert r.p5 <= r.p50 <= r.p95, f"{r.name}: percentile order violated"
        assert r.p5 > 0, f"{r.name}: p5 non-positive"


def test_only_water_route_coproduces_hydrogen():
    results = evaluate_all(n=1000)
    assert results["water_mining"].h2_coproduct > 0
    assert results["water_mining"].yields == "LOX+LH2"
    for key in ("h2_reduction", "carbothermal", "mre", "molten_salt"):
        assert results[key].h2_coproduct == 0.0
        assert results[key].yields == "LOX"


def test_lox_only_routes_equal_per_o2_and_per_propellant():
    # With no H2 co-product, per-kg-O2 and per-kg-propellant figures coincide.
    lox = evaluate("carbothermal", n=1000)
    assert lox.per_propellant_nominal == pytest.approx(lox.nominal)


def test_water_route_per_propellant_lower_than_per_o2():
    # Co-producing usable H2 lowers the per-kg-propellant figure vs per-kg-O2.
    w = evaluate_all(n=1000)["water_mining"]
    assert w.per_propellant_nominal < w.nominal


def test_dominance_probabilities_are_valid():
    c = compare(n=8000)
    # P(cheapest) and P(worst) are probability simplexes over the routes.
    assert pytest.approx(sum(c.p_cheapest.values()), abs=1e-9) == 1.0
    assert pytest.approx(sum(c.p_worst.values()), abs=1e-9) == 1.0
    # dominance is antisymmetric up to ties: P(a<b) + P(b<a) <= 1.
    for a in c.keys:
        for b in c.keys:
            if a != b:
                assert c.beats(a, b) + c.beats(b, a) <= 1.0 + 1e-9


def test_carbothermal_is_robustly_cheapest():
    # With all routes on a common electrical basis and realistic electrochemistry,
    # carbothermal is the most likely cheapest route (paired Monte Carlo).
    c = compare(n=8000)
    assert c.p_cheapest["carbothermal"] == max(c.p_cheapest.values())
    assert c.p_cheapest["carbothermal"] > 0.5
    # it beats H2 reduction always and MRE most of the time (MRE's lower tail, from its
    # wide cell-voltage uncertainty, occasionally dips below carbothermal).
    assert c.beats("carbothermal", "h2_reduction") > 0.95
    assert c.beats("carbothermal", "mre") > 0.80


def test_mre_and_h2_reduction_are_the_two_most_intensive():
    # Honest revised finding (v0.2): once MRE uses a realistic full-cell voltage, it is
    # among the MOST energy-intensive routes, not competitive. The two worst routes are
    # MRE and H2 reduction; carbothermal/molten-salt/water are essentially never worst.
    c = compare(n=8000)
    assert c.p_worst["mre"] + c.p_worst["h2_reduction"] > 0.95
    for k in ("carbothermal", "molten_salt", "water_mining"):
        assert c.p_worst[k] < 0.05
