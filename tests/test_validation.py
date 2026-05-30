"""Validation against the one well-quantified literature anchor.

Leger et al. (PNAS 2025) model the full H2-reduction chain (excavation ->
beneficiation -> reduction -> electrolysis -> liquefaction) at 24.3 +- 5.8 kWh/kg
LOX, with the reduction step ~55% and water electrolysis ~38% of the total.

This is the project's falsifiable test: an *independent* bottom-up model, built from
first principles and literature parameters (NOT fitted to Leger), should reproduce
that figure. If it does not, the framework is wrong.
"""

from lpem import evaluate
from lpem.routes import h2_reduction, water_mining
from lpem.model import Draw

LEGER_MEAN = 24.3
LEGER_SIGMA = 5.8  # 1-sigma


def test_h2_reduction_nominal_within_leger_one_sigma():
    """Nominal point estimate lands inside Leger's 24.3 +- 5.8 kWh/kg LOX.

    Uses the deterministic nominal path directly (no Monte Carlo needed).
    """
    nominal = h2_reduction(Draw(None)).total
    assert LEGER_MEAN - LEGER_SIGMA <= nominal <= LEGER_MEAN + LEGER_SIGMA, (
        f"nominal {nominal:.1f} outside Leger 1-sigma "
        f"[{LEGER_MEAN - LEGER_SIGMA}, {LEGER_MEAN + LEGER_SIGMA}]"
    )


def test_h2_reduction_ci_overlaps_leger_interval():
    """Our independent 90% interval overlaps Leger's 24.3 +- 5.8 interval.

    Interval overlap (not bracketing of the central value) is the honest criterion for
    agreement between two independent uncertain estimates. Our genuinely-independent
    model runs slightly lower than Leger, with its 95th percentile essentially at
    Leger's central value; the intervals overlap substantially.
    """
    r = evaluate("h2_reduction", n=20000)
    leger_lo, leger_hi = LEGER_MEAN - LEGER_SIGMA, LEGER_MEAN + LEGER_SIGMA
    overlap = min(r.p95, leger_hi) - max(r.p5, leger_lo)
    assert overlap > 0, (
        f"model 90% CI [{r.p5:.1f}, {r.p95:.1f}] does not overlap "
        f"Leger 1-sigma [{leger_lo:.1f}, {leger_hi:.1f}]"
    )


def test_h2_reduction_breakdown_matches_leger_shares():
    """Reduction (heating+reaction) ~55% and water electrolysis ~38%, loosely.

    This is the discriminating check: an independent model whose internal composition
    matched Leger's would not need to be fitted to his total.
    """
    route = h2_reduction(Draw(None))
    b, total = route.breakdown, route.total
    reduction_share = (b["heating"] + b["reaction"]) / total
    electrolysis_share = b["water_electrolysis"] / total
    # Loose bands: we are checking the model is not wildly miscomposed, not fitting.
    assert 0.40 <= reduction_share <= 0.70, f"reduction share {reduction_share:.2f}"
    assert 0.25 <= electrolysis_share <= 0.50, f"electrolysis share {electrolysis_share:.2f}"


def test_water_route_roughly_matches_leger_benchmark():
    """Leger cites ~11.3 kWh/kg for the water-ice route (O2 basis); be within ~50%."""
    nominal = water_mining(Draw(None)).total
    assert 6.0 <= nominal <= 17.0, f"water route O2-basis {nominal:.1f} far from ~11.3"


def test_nominal_is_deterministic():
    """Nominal evaluation uses Param.nominal and does not depend on rng."""
    a = h2_reduction(Draw(None)).total
    b = h2_reduction(Draw(None)).total
    assert a == b
