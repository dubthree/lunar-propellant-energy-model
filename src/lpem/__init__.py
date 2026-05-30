"""lpem: common-basis energy model for lunar propellant production.

Places every major oxygen / propellant extraction route on one electrical-equivalent
kWh-per-kg basis under a single explicit system boundary, with propagated
uncertainty. See the design spec and paper/PAPER.md.
"""

from .model import Comparison, Draw, MCResult, compare, evaluate, evaluate_all
from .routes import ROUTES, RouteResult
from .waste_heat import heat_balance, offset_summary, offsettable_kwh_per_kg_o2

__all__ = [
    "evaluate", "evaluate_all", "compare", "Comparison",
    "MCResult", "Draw", "ROUTES", "RouteResult",
    "offset_summary", "offsettable_kwh_per_kg_o2", "heat_balance",
]
__version__ = "0.4.0"
