"""lpem: common-basis energy model for lunar propellant production.

Places every major oxygen / propellant extraction route on one electrical-equivalent
kWh-per-kg basis under a single explicit system boundary, with propagated
uncertainty. See the design spec and paper/PAPER.md.
"""

from .model import Comparison, Draw, MCResult, compare, evaluate, evaluate_all
from .routes import ROUTES, RouteResult
from .sensitivity import ParamSensitivity, dominant_drivers, tornado
from .waste_heat import heat_balance, offset_summary, offsettable_kwh_per_kg_o2
from .benefit import estimate as estimate_benefit

__all__ = [
    "evaluate", "evaluate_all", "compare", "Comparison",
    "MCResult", "Draw", "ROUTES", "RouteResult",
    "tornado", "dominant_drivers", "ParamSensitivity",
    "offset_summary", "offsettable_kwh_per_kg_o2", "heat_balance",
    "estimate_benefit",
]
__version__ = "0.7.0"
