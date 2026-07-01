"""Stage energy functions.

Each function is pure: explicit inputs, no hidden state, returns electrical-
equivalent energy in **kWh per kg of O2 produced** (the common functional unit),
except `liquefaction_kwh` which is called per liquefied species. Composing these
under a shared system boundary is the contribution of this package.

All sampled scalars are passed in as plain floats (the Monte-Carlo engine in
`model.py` draws them from the `Param` table); these functions never sample, so
they are deterministic and trivially testable.
"""

from __future__ import annotations

from . import constants as C


def feed_per_kg_o2(o2_yield_wt: float) -> float:
    """kg of solid feed processed per kg O2, from the O2 weight-fraction yield."""
    if o2_yield_wt <= 0:
        raise ValueError("o2_yield_wt must be > 0")
    return 1.0 / o2_yield_wt


def excavation_kwh(feed_kg_per_kg_o2: float, exc_kwh_per_kg: float) -> float:
    """Electrical energy to excavate/move the feed for one kg O2."""
    return feed_kg_per_kg_o2 * exc_kwh_per_kg


def heating_kwh(
    feed_kg_per_kg_o2: float,
    cp_kj_per_kg_k: float,
    dT: float,
    recup: float,
    electric_to_thermal_eff: float,
    fusion_kj_per_kg: float = 0.0,
    melt_fraction: float = 0.0,
) -> float:
    """Electrical-equivalent energy to heat (and optionally melt) the feed.

    thermal = m * (cp*dT + fusion*melt_fraction), reduced by heat recuperation, then
    converted to the electrical input that must be supplied via the electric-to-thermal
    efficiency: electrical = thermal / electric_to_thermal_eff.
    """
    if not (0.0 <= recup < 1.0):
        raise ValueError("recup must be in [0, 1)")
    if not (0.0 < electric_to_thermal_eff <= 1.0):
        raise ValueError("electric_to_thermal_eff must be in (0, 1]")
    thermal_kj = feed_kg_per_kg_o2 * (cp_kj_per_kg_k * dT + fusion_kj_per_kg * melt_fraction)
    thermal_kj *= (1.0 - recup)
    electrical_kj = thermal_kj / electric_to_thermal_eff
    return electrical_kj / C.KJ_PER_KWH


def reaction_enthalpy_kwh(value_kwh_per_kg_o2: float) -> float:
    """Net chemical reaction enthalpy beyond sensible heating (already kWh/kg O2)."""
    return value_kwh_per_kg_o2


def water_electrolysis_kwh(efficiency: float) -> float:
    """Electrical energy to electrolyze the water needed for one kg O2.

    Per kg O2, H2_PER_KG_O2 kg of hydrogen is produced; energy = HHV(H2)/efficiency.
    """
    if not (0.0 < efficiency <= 1.0):
        raise ValueError("efficiency must be in (0, 1]")
    return C.H2_PER_KG_O2 * C.HHV_H2_KWH_PER_KG / efficiency


def coupled_voltage_efficiency(draw, v_param, ce_param, latent_name):
    """Anti-correlated draw of (cell voltage, current efficiency) for an electrolysis cell.

    Physically these are not independent: pushing higher current density raises the
    operating voltage (more overpotential + iR) AND lowers Faradaic efficiency. A single
    shared "operating severity" latent s maps high severity -> high voltage AND low
    efficiency, removing the unphysical (low-V, low-eff) and (high-V, high-eff) corners
    that independent sampling would visit. The latent is mapped through each parameter's
    triangular inverse-CDF (`ppf`), so the coupled draws still honor each parameter's MODE
    and distribution shape (a linear map would discard the mode and bias the mean toward
    the range midpoint). The latent name is route/cell specific so distinct cells (e.g. a
    1900 K oxide melt vs a 1200 K chloride salt) are NOT spuriously correlated in the
    paired Monte Carlo. The nominal (rng-free) path returns each param's nominal unchanged.
    """
    if draw.rng is None:
        return draw(v_param), draw(ce_param)
    s = draw.latent(latent_name)
    return v_param.ppf(s), ce_param.ppf(1.0 - s)  # severity up -> V up, efficiency down


def faradaic_kwh(v_cell: float, current_efficiency: float) -> float:
    """Faradaic electrolysis energy to evolve one kg O2 from oxide/salt melt.

    charge per kg O2 = (mol O2/kg) * electrons_per_O2 * Faraday; energy = q*V; then
    divide by current efficiency (current lost to side reactions).
    """
    if not (0.0 < current_efficiency <= 1.0):
        raise ValueError("current_efficiency must be in (0, 1]")
    mol_o2_per_kg = 1.0 / C.M_O2
    charge_c = mol_o2_per_kg * C.ELECTRONS_PER_O2 * C.FARADAY  # coulombs per kg O2
    energy_j = charge_c * v_cell
    return energy_j / C.J_PER_KWH / current_efficiency


def liquefaction_kwh(mass_kg: float, specific_kwh_per_kg: float) -> float:
    """Liquefaction energy for `mass_kg` of a species (call per species)."""
    return mass_kg * specific_kwh_per_kg


def water_sublimated_per_kg_o2(capture_efficiency: float) -> float:
    """kg of water that must be SUBLIMATED per kg O2, given imperfect vapor capture.

    Delivering C.WATER_PER_KG_O2 kg of captured water requires sublimating 1/eta as much,
    because tent/cold-trap capture over fissured PSR terrain in vacuum is leaky. The mining
    heat, ice sensible heat, and regolith throughput all scale with this (not the delivered
    mass).
    """
    if not (0.0 < capture_efficiency <= 1.0):
        raise ValueError("capture_efficiency must be in (0, 1]")
    return C.WATER_PER_KG_O2 / capture_efficiency


def water_regolith_per_kg_o2(ice_grade_wt: float, capture_efficiency: float) -> float:
    """kg of dry host regolith processed per kg O2 (shared by mining heat and excavation)."""
    regolith_per_kg_water = (1.0 - ice_grade_wt) / ice_grade_wt  # kg dry regolith per kg water
    return regolith_per_kg_water * water_sublimated_per_kg_o2(capture_efficiency)


def thermal_mining_kwh(
    ice_grade_wt: float,
    cp_regolith_kj_per_kg_k: float,
    cp_ice_kj_per_kg_k: float,
    dT: float,
    recup: float,
    electric_to_thermal_eff: float,
    capture_efficiency: float,
) -> float:
    """Electrical-equivalent energy to thermally mine the water for one kg O2.

    Three heat loads: (1) host-regolith sensible heat (recuperable), (2) ice sensible heat
    from feed to the sublimation point (NOT recuperated, leaves as vapor), and (3) the
    sublimation enthalpy (NOT recuperated). All three scale with the SUBLIMATED water mass
    (delivered/eta) via `capture_efficiency`. Returns kWh per kg O2.
    """
    if not (0.0 <= recup < 1.0):
        raise ValueError("recup must be in [0, 1)")
    if not (0.0 < electric_to_thermal_eff <= 1.0):
        raise ValueError("electric_to_thermal_eff must be in (0, 1]")
    water_sublimated = water_sublimated_per_kg_o2(capture_efficiency)
    regolith_per_kg_o2 = water_regolith_per_kg_o2(ice_grade_wt, capture_efficiency)
    # Recuperation applies only to the host-regolith sensible heat (it stays in the pit).
    # The ice sensible heat and the sublimation enthalpy are NOT recuperated: the water
    # vapor IS the product and carries that energy out of the system boundary.
    regolith_sensible_kj = regolith_per_kg_o2 * cp_regolith_kj_per_kg_k * dT * (1.0 - recup)
    ice_sensible_kj = water_sublimated * cp_ice_kj_per_kg_k * dT
    sublimation_kj = water_sublimated * C.SUBLIMATION_H2O_KJ_PER_KG
    electrical_kj = (regolith_sensible_kj + ice_sensible_kj + sublimation_kj) / electric_to_thermal_eff
    return electrical_kj / C.KJ_PER_KWH
