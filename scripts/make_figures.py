"""Publication-quality figures for the lunar-propellant-energy-model manuscript.

Run from the repo root:

    PYTHONPATH=src python3 scripts/make_figures.py

Writes three PNGs (dpi 150) into results/:
  fig-routes.png      five routes on a common energy basis vs Leger 2025
  fig-waste-heat.png  low-grade compute-waste-heat offset per route
  fig-radiator.png    radiator mass saved by PSR siting vs compute scale
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import lpem

RESULTS = Path(__file__).resolve().parent.parent / "results"
DPI = 150

# Leger 2025 H2-reduction reference: 24.3 +- 5.8 kWh/kg O2.
LEGER_CENTER = 24.3
LEGER_SIGMA = 5.8

T_REJECT_K = 350.0


def fig_routes() -> Path:
    """Horizontal bar chart: nominal kWh/kg O2 with 90% Monte-Carlo interval bars."""
    results = lpem.evaluate_all()
    items = sorted(results.items(), key=lambda kv: kv[1].nominal)
    names = [r.name for _, r in items]
    nom = np.array([r.nominal for _, r in items])
    lo = nom - np.array([r.p5 for _, r in items])
    hi = np.array([r.p95 for _, r in items]) - nom

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(names))
    ax.barh(y, nom, xerr=[lo, hi], color="#3b6", ecolor="#333", capsize=4, alpha=0.85)
    ax.axvspan(
        LEGER_CENTER - LEGER_SIGMA,
        LEGER_CENTER + LEGER_SIGMA,
        color="#88f",
        alpha=0.15,
        label="Leger 2025 H$_2$-reduction $\\pm 1\\sigma$",
    )
    ax.axvline(LEGER_CENTER, color="#44a", ls="--", lw=1, label="Leger 2025 central (24.3)")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Electrical-equivalent energy (kWh per kg O$_2$)")
    ax.set_title(
        "Lunar propellant routes on a common energy basis\n"
        "(nominal + 90% Monte-Carlo interval)"
    )
    ax.legend(loc="lower right", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = RESULTS / "fig-routes.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out


def fig_waste_heat() -> Path:
    """Bar chart: low-grade offsettable energy per route at T_reject = 350 K."""
    summ = lpem.offset_summary(t_reject_k=T_REJECT_K)
    # Descending by offsettable energy so the dominant PSR water route reads first.
    order = sorted(summ.values(), key=lambda r: -r.offsettable_kwh_per_kg_o2)
    names = [_route_label(r.route) for r in order]
    offset = np.array([r.offsettable_kwh_per_kg_o2 for r in order])
    colors = ["#3b6" if r.route == "water_mining" else "#bbb" for r in order]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(names))
    bars = ax.bar(x, offset, color=colors, alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Offsettable low-grade energy (kWh per kg O$_2$)")
    ax.set_title(
        f"Compute waste-heat offset by route (T$_{{reject}}$ = {T_REJECT_K:.0f} K)\n"
        "PSR water route dominates; regolith routes are negligible"
    )
    for rect, val in zip(bars, offset):
        ax.annotate(
            f"{val:.2f}",
            xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = RESULTS / "fig-waste-heat.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out


def _route_label(key: str) -> str:
    """Display label for a route key, sourced from its evaluated name."""
    return lpem.evaluate(key, n=1).name


def fig_radiator() -> tuple[Path, float]:
    """Radiator mass saved (t) by PSR siting vs sunlit equator across compute scale.

    Uses the benefit module's nominal parameters, including the vertical two-sided panel
    sky view factor F_sky (a competently oriented deployable panel, not a horizontal plate
    lying on warm terrain). The F_sky=0 horizontal-plate limit is what over-stated the
    earlier slope (~51 t/MW); the vertical geometry gives a much smaller, honest saving.
    """
    b = lpem.benefit
    eps = b.RADIATOR_EMISSIVITY.nominal
    t_rad = b.T_REJECT_K.nominal
    t_env_psr = b.T_ENV_PSR_K.nominal
    t_env_eq = b.T_ENV_EQ_K.nominal
    solar_eq = b.ABSORBED_SOLAR_EQ_WM2.nominal
    areal_mass = b.RADIATOR_AREAL_MASS.nominal  # kg/m^2
    f_sky = b.F_SKY.nominal

    mw = np.linspace(0.01, 2.0, 200)
    saved_t = np.empty_like(mw)
    for i, scale in enumerate(mw):
        power_kw = scale * 1000.0
        a_eq = b.radiator_area_m2(power_kw, t_rad, t_env_eq, eps, solar_eq, f_sky)
        a_psr = b.radiator_area_m2(power_kw, t_rad, t_env_psr, eps, 0.0, f_sky)
        saved_t[i] = max(0.0, a_eq - a_psr) * areal_mass / 1000.0

    slope = saved_t[-1] / mw[-1]  # t per MW (linear through origin)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(mw, saved_t, color="#3b6", lw=2)
    ax.set_xlabel("Compute scale (MW)")
    ax.set_ylabel("Radiator mass saved by PSR siting (t)")
    ax.set_title(
        "Radiator mass saved by PSR siting vs sunlit equator\n"
        f"roughly linear at ~{slope:.0f} t/MW"
    )
    ax.annotate(
        f"~{slope:.0f} t/MW",
        xy=(mw[-1], saved_t[-1]),
        xytext=(-12, -18),
        textcoords="offset points",
        ha="right",
        fontsize=9,
    )
    ax.set_xlim(0, 2.0)
    ax.set_ylim(0, None)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = RESULTS / "fig-radiator.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out, slope


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    p1 = fig_routes()
    p2 = fig_waste_heat()
    p3, slope = fig_radiator()
    print(f"wrote {p1}")
    print(f"wrote {p2}")
    print(f"wrote {p3}  (radiator slope ~{slope:.1f} t/MW)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
