"""Physical constants and thermodynamic reference data.

Every value carries a sourced comment. Nothing here is fitted; these are
first-principles constants or standard reference data. Route- and stage-specific
parameters (with uncertainty) live in `params.py`, not here.
"""

# --- Universal constants ---
FARADAY = 96485.332  # C/mol, Faraday constant (CODATA)
MJ_PER_KWH = 3.6     # 1 kWh = 3.6 MJ
J_PER_KWH = 3.6e6
KJ_PER_KWH = 3600.0

# --- Molar masses (kg/mol) ---
M_O2 = 0.0319988
M_H2 = 0.00201588
M_H2O = 0.0180153

# --- Water stoichiometry ---
# Per kg of O2 produced, the mass of water that must be split, and the H2 co-product.
# 1 mol H2O -> 1 mol H2 + 1/2 mol O2.  Per mol O2 you split 2 mol H2O and get 2 mol H2.
WATER_PER_KG_O2 = (2 * M_H2O) / M_O2   # kg H2O per kg O2  (~1.1260)
H2_PER_KG_O2 = (2 * M_H2) / M_O2       # kg H2 per kg O2   (~0.1260)

# --- Electrolysis energy ---
# Higher heating value of hydrogen, derived from its standard molar enthalpy of
# combustion (liquid-water product, 285.8 kJ/mol; NIST) and M_H2, rather than a
# rounded literature MJ/kg. HHV is the right basis for liquid-water-fed electrolysis
# (the enthalpy of liquid water -> H2 + O2).
ENTHALPY_COMBUSTION_H2_KJ_PER_MOL = 285.8  # NIST, HHV basis
HHV_H2_KWH_PER_KG = ENTHALPY_COMBUSTION_H2_KJ_PER_MOL / (M_H2 * 1000.0) / MJ_PER_KWH  # ~39.4

# --- Electrons transferred per O2 molecule in oxide/water electrolysis ---
# 2 O^2-  ->  O2 + 4 e-
ELECTRONS_PER_O2 = 4

# --- Sublimation enthalpy of water ice (kJ/kg) ---
# Latent heat of sublimation ~2.83 MJ/kg near 273 K (CRC); used for thermal mining.
SUBLIMATION_H2O_KJ_PER_KG = 2830.0
