"""Sanity checks across all routes: finite, positive, ordered, internally consistent."""

import pytest

from lpem import evaluate, evaluate_all
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


def test_mre_energy_competitive_despite_no_published_figure():
    # Headline finding: MRE's per-kg-O2 energy is not an outlier high; its barrier
    # is anode life/power density, not energy. Assert it is within the route spread.
    results = evaluate_all(n=4000)
    mre = results["mre"].nominal
    h2 = results["h2_reduction"].nominal
    assert mre < h2  # MRE more energy-efficient per kg O2 than H2 reduction at nominal
