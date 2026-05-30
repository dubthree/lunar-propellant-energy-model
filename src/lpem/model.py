"""Evaluation engine: nominal point estimate + Monte-Carlo uncertainty propagation.

A `Draw` resolves each `Param` to a scalar. With no rng it returns the nominal (a
deterministic point estimate); with an rng it returns a triangular sample. Draws are
memoized per evaluation so a parameter shared across stages takes one consistent
value within a single Monte-Carlo trial.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .params import Param
from .routes import ROUTES, RouteResult


class Draw:
    """Resolves Params to scalars; memoized within one evaluation/trial."""

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self.rng = rng
        # Key on the Param object itself (frozen dataclass => hashable). This keeps a
        # parameter referenced twice in one trial consistent, and is robust to derived
        # Params (unlike keying on id(), which breaks for locally-constructed objects).
        self._cache: dict[Param, float] = {}

    def __call__(self, param: Param) -> float:
        if param not in self._cache:
            self._cache[param] = param.nominal if self.rng is None else param.sample(self.rng)
        return self._cache[param]


@dataclass
class MCResult:
    name: str
    yields: str
    nominal: float                 # kWh/kg O2, point estimate at nominal (modal) params
    p5: float
    p50: float                     # MC median; the honest central estimate
    p95: float
    mean: float
    breakdown_nominal: dict        # stage -> kWh/kg O2 at nominal
    h2_coproduct: float            # kg H2 per kg O2
    per_propellant_nominal: float  # kWh/kg propellant (LOX [+LH2]) at nominal
    per_propellant_p5: float
    per_propellant_p95: float
    samples: np.ndarray | None = field(repr=False, default=None)

    @property
    def ci90_halfwidth(self) -> float:
        """Half-width of the 90% Monte-Carlo interval: (p95 - p5) / 2 (NOT a sigma)."""
        return (self.p95 - self.p5) / 2.0


def evaluate(route_key: str, n: int = 20000, seed: int = 12345) -> MCResult:
    """Evaluate one route: nominal point estimate plus an n-trial Monte-Carlo band."""
    fn = ROUTES[route_key]

    nominal: RouteResult = fn(Draw(None))

    rng = np.random.default_rng(seed)
    totals = np.empty(n)
    per_prop = np.empty(n)
    for i in range(n):
        r = fn(Draw(rng))
        totals[i] = r.total
        per_prop[i] = r.total_per_kg_propellant

    return MCResult(
        name=nominal.name,
        yields=nominal.yields,
        nominal=nominal.total,
        p5=float(np.percentile(totals, 5)),
        p50=float(np.percentile(totals, 50)),
        p95=float(np.percentile(totals, 95)),
        mean=float(totals.mean()),
        breakdown_nominal=dict(nominal.breakdown),
        h2_coproduct=nominal.h2_coproduct,
        per_propellant_nominal=nominal.total_per_kg_propellant,
        per_propellant_p5=float(np.percentile(per_prop, 5)),
        per_propellant_p95=float(np.percentile(per_prop, 95)),
        samples=totals,
    )


def evaluate_all(n: int = 20000, seed: int = 12345) -> dict[str, MCResult]:
    return {key: evaluate(key, n=n, seed=seed) for key in ROUTES}


@dataclass
class Comparison:
    """Paired-Monte-Carlo comparison across all routes."""

    keys: list                       # route keys, in declared order
    names: dict                      # key -> display name
    totals: dict                     # key -> np.ndarray of per-trial kWh/kg O2
    dominance: dict                  # a -> {b -> P(route a strictly cheaper than b)}
    p_cheapest: dict                 # key -> P(route is the single cheapest)
    p_worst: dict                    # key -> P(route is the single most expensive)
    n: int

    def beats(self, a: str, b: str) -> float:
        return self.dominance[a][b]


def compare(n: int = 20000, seed: int = 12345) -> Comparison:
    """Paired Monte Carlo: ONE shared Draw per trial across all routes.

    This is the statistically correct way to rank the routes. Because a single Draw is
    shared by every route within a trial, parameters that are physically common (regolith
    cp, heat recuperation, electrolysis efficiency, liquefaction, cleanup, compression,
    electric-to-thermal) take the SAME sampled value for all routes in that trial; only
    route-specific parameters differ. Comparing independent per-route runs (as `evaluate`
    does) would let one route get a lucky recuperation draw while another gets an unlucky
    one, smearing the ranking. Here the ranking is evaluated trial-by-trial, so we can
    report P(route A cheaper than route B) rather than eyeballing overlapping error bars.
    """
    keys = list(ROUTES)
    rng = np.random.default_rng(seed)
    totals = {k: np.empty(n) for k in keys}
    for i in range(n):
        draw = Draw(rng)  # shared across all routes this trial -> common params consistent
        for k in keys:
            totals[k][i] = ROUTES[k](draw).total

    dominance = {
        a: {b: float(np.mean(totals[a] < totals[b])) for b in keys if b != a} for a in keys
    }
    stacked = np.vstack([totals[k] for k in keys])  # (R, n)
    cheapest = stacked.argmin(axis=0)
    worst = stacked.argmax(axis=0)
    p_cheapest = {k: float(np.mean(cheapest == j)) for j, k in enumerate(keys)}
    p_worst = {k: float(np.mean(worst == j)) for j, k in enumerate(keys)}

    names = {k: ROUTES[k](Draw(None)).name for k in keys}
    return Comparison(keys, names, totals, dominance, p_cheapest, p_worst, n)
