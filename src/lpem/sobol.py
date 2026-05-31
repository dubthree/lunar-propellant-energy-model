"""Global, variance-based sensitivity analysis (Sobol indices).

Where the one-at-a-time tornado in `sensitivity.py` reports local range-swings with all
other parameters pinned, this decomposes the *total Monte-Carlo variance* of a route's
kWh/kg O2 into contributions from each independent input. It reports two indices per input:

- First-order S_i: the fraction of output variance explained by that input alone, averaged
  over all settings of the others ("how much variance would fixing only this remove?").
- Total-effect S_Ti: the fraction of variance involving that input including all its
  interactions ("how much variance is left if everything except this is fixed?").

S_Ti - S_i is the interaction strength. First-order indices sum to <= 1; total-effect
indices sum to >= 1 (the excess is interaction). Estimators: Saltelli (2010) for S_i,
Jansen (1999) for S_Ti, evaluated on Saltelli sample matrices. numpy only.

Inputs are the genuinely INDEPENDENT random quantities a route draws. For the electrolysis
routes, cell voltage and current efficiency are not independent (they share an
operating-severity latent), so that latent is the single input dimension here, not V and CE
separately. This is what makes the variance decomposition correct rather than double-counting
correlated inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .params import Param
from .routes import ROUTES


class _Resolver:
    """Maps a route's draws to fixed values from a unit-hypercube point (or records them)."""

    def __init__(self, rng_flag=True):
        # rng must be non-None so coupled_voltage_efficiency takes its coupled (latent) path.
        self.rng = object() if rng_flag else None
        self._u: dict = {}          # key -> u in [0,1]; key is a Param or a latent-name str
        self.order: list = []       # discovery order of keys
        self._cache: dict = {}
        self.recording = False

    def __call__(self, param: Param) -> float:
        if param not in self._cache:
            if self.recording and param not in self._u:
                self.order.append(param)
            u = self._u.get(param, 0.5)
            self._cache[param] = param.ppf(u)
        return self._cache[param]

    def latent(self, name: str) -> float:
        if self.recording and name not in self._u:
            self.order.append(name)
        return self._u.get(name, 0.5)


def route_inputs(route_key: str) -> list:
    """Discover the ordered list of independent inputs (Params and latent names) a route uses."""
    r = _Resolver()
    r.recording = True
    ROUTES[route_key](r)
    return r.order


def _evaluate(route_key: str, u_row: np.ndarray, inputs: list) -> float:
    r = _Resolver()
    r._u = {key: float(u_row[j]) for j, key in enumerate(inputs)}
    return ROUTES[route_key](r).total


@dataclass
class SobolIndex:
    input_label: str
    first_order: float    # S_i
    total_effect: float   # S_Ti


def _label(key) -> str:
    return key.cite if isinstance(key, Param) else f"latent:{key}"


def sobol(route_key: str, n: int = 4096, seed: int = 12345) -> list[SobolIndex]:
    """Sobol first-order and total-effect indices for a route, sorted by total effect.

    Cost is n*(k+2) route evaluations for k inputs (cheap; the route is pure arithmetic).
    """
    inputs = route_inputs(route_key)
    k = len(inputs)
    rng = np.random.default_rng(seed)
    A = rng.random((n, k))
    B = rng.random((n, k))

    def run(mat):
        return np.array([_evaluate(route_key, mat[i], inputs) for i in range(n)])

    f_A = run(A)
    f_B = run(B)
    var = np.var(np.concatenate([f_A, f_B]))
    if var <= 0:
        return [SobolIndex(_label(key), 0.0, 0.0) for key in inputs]

    out = []
    for j, key in enumerate(inputs):
        AB = A.copy()
        AB[:, j] = B[:, j]
        f_AB = run(AB)
        # Saltelli 2010 first-order; Jansen 1999 total-effect.
        s_i = float(np.mean(f_B * (f_AB - f_A)) / var)
        s_ti = float(np.mean((f_A - f_AB) ** 2) / (2.0 * var))
        out.append(SobolIndex(_label(key), s_i, s_ti))

    out.sort(key=lambda s: -s.total_effect)
    return out
