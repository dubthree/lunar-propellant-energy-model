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
    """Resolves Params to scalars; memoized within one evaluation/trial.

    Two report-only flags change how routes compose (they never alter parameter draws):
    - `exclude_standing_loss`: zero every continuous standing-loss term, giving each route's
      loss-free configuration (used to validate H2 reduction against Leger 2025).
    - `solar_thermal`: charge zero electrical energy for high-grade heat terms, as if a solar
      concentrator supplied them (sunlit-site sensitivity; the PSR water route never sets it).
    Both default False, so the headline tables are unaffected.
    """

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        exclude_standing_loss: bool = False,
        solar_thermal: bool = False,
    ) -> None:
        self.rng = rng
        self.exclude_standing_loss = exclude_standing_loss
        self.solar_thermal = solar_thermal
        # Key on the Param object itself (frozen dataclass => hashable). This keeps a
        # parameter referenced twice in one trial consistent, and is robust to derived
        # Params (unlike keying on id(), which breaks for locally-constructed objects).
        # Shared latents (for correlated params) are keyed by a ("__latent__", name) tuple.
        self._cache: dict = {}

    def __call__(self, param: Param) -> float:
        if param not in self._cache:
            self._cache[param] = param.nominal if self.rng is None else param.sample(self.rng)
        return self._cache[param]

    def latent(self, name: str) -> float:
        """A shared standard-uniform latent in [0,1], memoized per trial by name.

        Used to induce physical correlation between parameters that are not independent
        (e.g. electrolysis cell voltage and current efficiency both move with operating
        current density). Returns 0.5 on the nominal (rng-free) path so callers can keep
        nominal behaviour exact.
        """
        key = ("__latent__", name)
        if key not in self._cache:
            self._cache[key] = 0.5 if self.rng is None else float(self.rng.random())
        return self._cache[key]


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


def evaluate(
    route_key: str,
    n: int = 20000,
    seed: int = 12345,
    exclude_standing_loss: bool = False,
    solar_thermal: bool = False,
) -> MCResult:
    """Evaluate one route: nominal point estimate plus an n-trial Monte-Carlo band."""
    fn = ROUTES[route_key]

    def mk(rng):
        return Draw(rng, exclude_standing_loss=exclude_standing_loss, solar_thermal=solar_thermal)

    nominal: RouteResult = fn(mk(None))

    rng = np.random.default_rng(seed)
    totals = np.empty(n)
    per_prop = np.empty(n)
    for i in range(n):
        r = fn(mk(rng))
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


def evaluate_all(
    n: int = 20000,
    seed: int = 12345,
    exclude_standing_loss: bool = False,
    solar_thermal: bool = False,
) -> dict[str, MCResult]:
    return {
        key: evaluate(
            key, n=n, seed=seed,
            exclude_standing_loss=exclude_standing_loss, solar_thermal=solar_thermal,
        )
        for key in ROUTES
    }


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


def compare(
    n: int = 20000,
    seed: int = 12345,
    exclude_standing_loss: bool = False,
    solar_thermal: bool = False,
) -> Comparison:
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
        # shared across all routes this trial -> common params consistent
        draw = Draw(rng, exclude_standing_loss=exclude_standing_loss, solar_thermal=solar_thermal)
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
