"""One-at-a-time (tornado) sensitivity analysis.

For a given route, hold every parameter at its nominal except one, which is pinned
to its `low` then its `high`. The resulting swing in the route's total kWh/kg O2
isolates how much each input drives the output uncertainty. Ranking the parameters
by swing gives the classic tornado ordering, which underpins the paper's robustness
claims: it shows which few inputs a reviewer should challenge first.

Implementation note: a `_Resolver` mimics the `Draw` interface (`__call__(param)`,
a `.rng` attribute, and `.latent(name)`) so the route composition in `lpem.routes`
is reused verbatim, never duplicated. Keeping `rng = None` means routes follow their
deterministic nominal path; the resolver simply substitutes one pinned value.
"""

from __future__ import annotations

from dataclasses import dataclass

from .params import Param
from .routes import ROUTES


class _Resolver:
    """A nominal-everything resolver with the `Draw` call interface.

    Returns `param.nominal` for every `Param`, except a single optionally-pinned
    `Param`, for which it returns a chosen value. `rng` is `None` so routes take
    their deterministic nominal path (including `coupled_voltage_efficiency`, which
    then resolves its voltage/efficiency params through this resolver). Every
    distinct `Param` seen is recorded in `seen`, so we can discover exactly which
    parameters a route actually uses.
    """

    rng = None

    def __init__(self, pinned: Param | None = None, value: float | None = None) -> None:
        self._pinned = pinned
        self._value = value
        self.seen: list[Param] = []

    def __call__(self, param: Param) -> float:
        if param not in self.seen:
            self.seen.append(param)
        if self._pinned is not None and param is self._pinned:
            return self._value
        return param.nominal

    def latent(self, name: str) -> float:
        # Nominal path: matches Draw.latent's rng-free behaviour.
        return 0.5


@dataclass
class ParamSensitivity:
    """One row of a tornado chart for a single parameter."""

    param: Param
    cite: str
    low_total: float    # route total kWh/kg O2 with this param pinned low
    high_total: float   # route total kWh/kg O2 with this param pinned high
    nominal_total: float
    swing: float        # |high_total - low_total|


def _params_used(route_key: str) -> list[Param]:
    """The distinct Params a route actually resolves, in first-seen order."""
    fn = ROUTES[route_key]
    r = _Resolver()
    fn(r)
    return r.seen


def tornado(route_key: str) -> list[ParamSensitivity]:
    """Tornado sensitivity for a route, sorted by swing descending.

    For each parameter the route uses, recompute the route total with that parameter
    set to its `low` and to its `high` while all others stay nominal.
    """
    if route_key not in ROUTES:
        raise KeyError(route_key)
    fn = ROUTES[route_key]
    nominal_total = fn(_Resolver()).total

    rows: list[ParamSensitivity] = []
    for p in _params_used(route_key):
        low_total = fn(_Resolver(p, p.low)).total
        high_total = fn(_Resolver(p, p.high)).total
        rows.append(
            ParamSensitivity(
                param=p,
                cite=p.cite,
                low_total=low_total,
                high_total=high_total,
                nominal_total=nominal_total,
                swing=abs(high_total - low_total),
            )
        )

    rows.sort(key=lambda r: r.swing, reverse=True)
    return rows


def dominant_drivers(route_key: str, top: int = 3) -> list[ParamSensitivity]:
    """The `top` parameters with the largest swing for a route."""
    return tornado(route_key)[:top]
