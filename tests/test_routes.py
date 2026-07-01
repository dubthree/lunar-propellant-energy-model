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


def test_water_route_is_robustly_cheapest():
    # Once continuous reactor heat loss is charged to the high-temperature routes, the
    # low-temperature PSR water route (sublimation at ~273 K) avoids that penalty and is
    # the most likely cheapest route by a wide margin (paired Monte Carlo).
    c = compare(n=8000)
    assert c.p_cheapest["water_mining"] == max(c.p_cheapest.values())
    assert c.p_cheapest["water_mining"] > 0.7
    # it beats every high-temperature route in the large majority of trials.
    for k in ("carbothermal", "mre", "molten_salt", "h2_reduction"):
        assert c.beats("water_mining", k) > 0.8


def test_high_temperature_routes_are_the_intensive_ones():
    # The worst route is always one of the four high-temperature routes; the water route is
    # essentially never the worst. With the reactor standing loss now charged symmetrically to
    # H2 reduction too, H2 (highest nominal) and MRE are the two most likely worst; the robust
    # claim is that water is never the worst.
    c = compare(n=8000)
    assert c.p_worst["water_mining"] < 0.02
    worst_route = max(c.p_worst, key=c.p_worst.get)
    assert worst_route in ("h2_reduction", "mre")


def test_water_total_rises_when_capture_efficiency_falls():
    # Charging the water route a vapor-capture efficiency: poorer capture (0.50) forces more
    # sublimation and regolith throughput per kg O2 than good capture (0.95), so the total rises.
    from lpem import params as P
    from lpem.sensitivity import tornado
    row = {r.param: r for r in tornado("water_mining")}[P.CAPTURE_EFFICIENCY]
    assert row.low_total > row.high_total  # low capture efficiency => higher energy


def test_solar_thermal_lowers_hot_routes_but_not_water():
    # Report-only sensitivity: with high-grade heat supplied by solar concentrators, every hot
    # route drops (heat costs zero electrical); the PSR water route sits in shadow and is unchanged.
    base = evaluate_all(n=200)
    solar = evaluate_all(n=200, solar_thermal=True)
    assert solar["water_mining"].nominal == pytest.approx(base["water_mining"].nominal)
    for k in ("h2_reduction", "carbothermal", "mre", "molten_salt"):
        assert solar[k].nominal < base[k].nominal
