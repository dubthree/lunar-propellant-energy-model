"""Architecture extension: from energy-per-kg to power plant size and landed mass.

This is the next step in the sequence after the energy model. It imports the energy
model (`routes`/`model`) and adds the two terms that lunar-ISRU gap assessments flag
as the architecture drivers: the **continuous electrical power** a route needs for a
target production rate, and the **landed mass of the power system** that implies (the
dominant ISRU infrastructure mass). It does NOT model capital cost, mobility, or
demand: those remain out of scope.

Cross-check (reported, not fitted): CLPA (Kornuta 2019) sizes a ~450 t/yr water
propellant plant at ~2.0 MWe. Production-only energy here lands below that because the
CLPA figure includes mining mobility, thermal management, comms, and margin outside
this boundary; see PAPER.md limitations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .model import Draw
from .params import Param
from .routes import ROUTES

HOURS_PER_YEAR = 8766.0
FSP_UNIT_KWE = 100.0  # NASA FY2030 fission-surface-power unit target

# Plant operational availability (fraction of the year actually producing).
AVAILABILITY = Param(0.90, 0.75, 0.95, "plant availability; FSP gives continuous power")
# Power-system specific mass (kg per kWe), nuclear FSP incl. conversion + radiators.
# NASA's 40 kWe concept TARGETED ~150 kg/kWe but concept studies reportedly EXCEEDED it,
# so 150 is an optimistic-unmet target; the nominal is set to a more defensible ~225,
# with 150 as the low end. The landed-mass swing is most sensitive to this one number.
# Source: NASA 40 kWe Fission Surface Power concept; Kilopower/FSP.
# NOTE: this models an ALL-FISSION architecture (continuous power, no night-storage
# mass). A solar+storage architecture would be dominated by regenerative-fuel-cell /
# battery mass for the ~14-day night, which this does NOT include (see PAPER limitations).
FSP_SPECIFIC_MASS = Param(225.0, 150.0, 350.0, "NASA FSP; 150 kg/kWe target reportedly exceeded")


@dataclass
class PlantSizing:
    route: str
    yields: str
    annual_o2_kg: float
    power_kwe_nominal: float
    power_kwe_p5: float
    power_kwe_p95: float
    mass_t_nominal: float          # power-system landed mass, tonnes
    mass_t_p5: float
    mass_t_p95: float
    n_fsp_units_nominal: float     # 100-kWe units required
    samples_power: np.ndarray = field(repr=False, default=None)


def size_plant(route_key: str, annual_o2_kg: float, n: int = 20000, seed: int = 12345) -> PlantSizing:
    """Size the power plant for a route at a target annual O2 output, with uncertainty."""
    if annual_o2_kg <= 0:
        raise ValueError("annual_o2_kg must be > 0")
    fn = ROUTES[route_key]

    def _power_kwe(energy_per_kg: float, availability: float) -> float:
        return energy_per_kg * annual_o2_kg / (HOURS_PER_YEAR * availability)

    nominal_route = fn(Draw(None))
    e_nom = nominal_route.total
    power_nom = _power_kwe(e_nom, AVAILABILITY.nominal)
    mass_nom = power_nom * FSP_SPECIFIC_MASS.nominal  # kg

    rng = np.random.default_rng(seed)
    powers = np.empty(n)
    masses = np.empty(n)
    for i in range(n):
        d = Draw(rng)
        e = fn(d).total
        avail = AVAILABILITY.sample(rng)
        sm = FSP_SPECIFIC_MASS.sample(rng)
        p = _power_kwe(e, avail)
        powers[i] = p
        masses[i] = p * sm

    return PlantSizing(
        route=nominal_route.name,
        yields=nominal_route.yields,
        annual_o2_kg=annual_o2_kg,
        power_kwe_nominal=power_nom,
        power_kwe_p5=float(np.percentile(powers, 5)),
        power_kwe_p95=float(np.percentile(powers, 95)),
        mass_t_nominal=mass_nom / 1000.0,
        mass_t_p5=float(np.percentile(masses, 5)) / 1000.0,
        mass_t_p95=float(np.percentile(masses, 95)) / 1000.0,
        n_fsp_units_nominal=power_nom / FSP_UNIT_KWE,
        samples_power=powers,
    )


def size_all(annual_o2_kg: float, n: int = 20000, seed: int = 12345) -> dict[str, PlantSizing]:
    return {key: size_plant(key, annual_o2_kg, n=n, seed=seed) for key in ROUTES}
