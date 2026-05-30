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
