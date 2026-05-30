"""lpem: common-basis energy model for lunar propellant production.

Places every major oxygen / propellant extraction route on one electrical-equivalent
kWh-per-kg basis under a single explicit system boundary, with propagated
uncertainty. See the design spec and paper/PAPER.md.
"""

from .model import Draw, MCResult, evaluate, evaluate_all
from .routes import ROUTES, RouteResult

__all__ = ["evaluate", "evaluate_all", "MCResult", "Draw", "ROUTES", "RouteResult"]
__version__ = "0.1.0"
