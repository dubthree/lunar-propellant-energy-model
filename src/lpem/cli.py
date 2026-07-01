"""Command-line entry point: print the cross-route comparison table.

    python -m lpem                # comparison table to stdout
    python -m lpem --figure out.png   # also write a bar+whisker figure (needs matplotlib)
    python -m lpem --markdown     # emit the table as Markdown (used to refresh the paper)
"""

from __future__ import annotations

import argparse

from .arch import size_all
from .model import compare, evaluate_all
from .routes import ROUTES
from .sensitivity import tornado
from .sobol import sobol
from .waste_heat import heat_balance, offset_summary
from .benefit import estimate as estimate_benefit


def _format_table(results: dict, markdown: bool = False) -> str:
    header = [
        "Route", "Yields", "kWh/kg O2 (nom)", "90% CI (O2)", "kWh/kg propellant (nom)"
    ]
    rows = []
    # Stable, energy-ascending order on the per-kg-O2 nominal.
    for key, r in sorted(results.items(), key=lambda kv: kv[1].nominal):
        rows.append([
            r.name,
            r.yields,
            f"{r.nominal:.1f}",
            f"{r.p5:.1f}-{r.p95:.1f}",
            f"{r.per_propellant_nominal:.1f}",
        ])

    if markdown:
        out = ["| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(out)

    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*row) for row in rows]
    return "\n".join(lines)


def _format_plant_table(sizings: dict, annual_o2_t: float, markdown: bool = False) -> str:
    header = ["Route", "Yields", "Power kWe (nom)", "90% CI kWe",
              "Power-sys mass t (nom)", "100-kWe units"]
    rows = []
    for key, s in sorted(sizings.items(), key=lambda kv: kv[1].power_kwe_nominal):
        rows.append([
            s.route, s.yields,
            f"{s.power_kwe_nominal:,.0f}",
            f"{s.power_kwe_p5:,.0f}-{s.power_kwe_p95:,.0f}",
            f"{s.mass_t_nominal:,.1f}",
            f"{s.n_fsp_units_nominal:,.1f}",
        ])
    title = f"Power plant sizing for {annual_o2_t:g} t O2/yr"
    if markdown:
        out = [f"**{title}**", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(out)
    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [title, fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*row) for row in rows]
    return "\n".join(lines)


def _format_dominance(c, markdown: bool = False) -> str:
    title = f"Paired-Monte-Carlo dominance ({c.n} trials): P(route is cheapest / worst)"
    order = sorted(c.keys, key=lambda k: -c.p_cheapest[k])
    rows = [[c.names[k], f"{c.p_cheapest[k]:.2f}", f"{c.p_worst[k]:.2f}"] for k in order]
    header = ["Route", "P(cheapest)", "P(worst)"]
    if markdown:
        out = [f"**{title}**", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(out)
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [title, fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*r) for r in rows]
    return "\n".join(lines)


def _param_names() -> dict:
    """Map each Param object (by id) to its module-level variable name."""
    from . import params as P

    from .params import Param

    return {id(v): n for n, v in vars(P).items() if isinstance(v, Param)}


def _format_sensitivity(route_key: str, markdown: bool = False) -> str:
    rows = tornado(route_key)
    names = _param_names()
    title = (
        f"One-at-a-time (tornado) sensitivity for '{route_key}': "
        f"each param low/high, all others nominal (kWh/kg O2)"
    )
    header = ["Parameter", "Cite", "Low total", "High total", "Swing"]
    table = []
    for r in rows:
        table.append([
            names.get(id(r.param), "?"),
            r.cite,
            f"{r.low_total:.2f}",
            f"{r.high_total:.2f}",
            f"{r.swing:.2f}",
        ])
    if markdown:
        out = [f"**{title}**", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in table]
        return "\n".join(out)
    widths = [max(len(header[i]), *(len(row[i]) for row in table)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [title, fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*row) for row in table]
    return "\n".join(lines)


def _format_sobol(route_key: str, n: int, markdown: bool = False) -> str:
    rows = sobol(route_key, n=n)
    title = (
        f"Sobol variance-based sensitivity for '{route_key}' ({n} base samples): "
        f"first-order S_i and total-effect S_Ti (fraction of output variance)"
    )
    header = ["Input", "S_i", "S_Ti", "interaction (S_Ti - S_i)"]
    table = [[r.input_label, f"{r.first_order:.2f}", f"{r.total_effect:.2f}",
              f"{r.total_effect - r.first_order:.2f}"] for r in rows]
    if markdown:
        out = [f"**{title}**", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in table]
        return "\n".join(out)
    widths = [max(len(header[i]), *(len(row[i]) for row in table)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [title, fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*row) for row in table]
    return "\n".join(lines)


def _format_solar_thermal(n: int, seed: int, markdown: bool = False) -> str:
    """Baseline vs solar-thermal electrical totals side by side (report-only sensitivity)."""
    base = evaluate_all(n=n, seed=seed)
    solar = evaluate_all(n=n, seed=seed, solar_thermal=True)
    title = (
        "Solar-thermal sensitivity: high-grade heat (sensible + fusion + reaction + standing "
        "loss) supplied by solar concentrators instead of resistive electric heat"
    )
    caption = (
        "Applies ONLY at a sunlit site and ignores concentrator mass. The PSR water route "
        "sits in permanent shadow and cannot use solar-thermal, so it stays at baseline."
    )
    header = ["Route", "Yields", "Baseline kWh/kg O2", "Solar-thermal kWh/kg O2", "Delta"]
    rows = []
    for key, r in sorted(base.items(), key=lambda kv: kv[1].nominal):
        s = solar[key]
        rows.append([
            r.name, r.yields,
            f"{r.nominal:.1f} ({r.p5:.1f}-{r.p95:.1f})",
            f"{s.nominal:.1f} ({s.p5:.1f}-{s.p95:.1f})",
            f"-{r.nominal - s.nominal:.1f}",
        ])
    if markdown:
        out = [f"**{title}**", "", f"_{caption}_", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] * len(header)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(out)
    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    lines = [title, fmt.format(*header), fmt.format(*("-" * w for w in widths))]
    lines += [fmt.format(*row) for row in rows]
    lines += ["", caption]
    return "\n".join(lines)


def _format_waste_heat(t_reject: float, compute_kw: float, o2_t: float) -> str:
    summ = offset_summary(t_reject_k=t_reject)
    order = sorted(summ.values(), key=lambda r: -r.fraction_of_total)
    lines = [f"Compute waste-heat offset at T_reject = {t_reject:.0f} K (low-grade only):",
             f"  {'Route':30s} {'offset kWh/kg O2':>16s}  {'% of total':>10s}"]
    for r in order:
        lines.append(f"  {r.route:30s} {r.offsettable_kwh_per_kg_o2:16.2f}  {100*r.fraction_of_total:9.1f}%")
    hb = heat_balance("water_mining", compute_kw, o2_t * 1000.0, t_reject_k=t_reject)
    lines.append("")
    lines.append(f"  Heat balance: a {compute_kw:g} kW compute load vs a {o2_t:g} t/yr PSR water plant")
    lines.append(f"    low-grade demand {hb.low_grade_demand_kw:.1f} kW; covered {100*hb.covered_fraction:.0f}%; "
                 f"reactor mass saved {hb.reactor_mass_saved_t:.1f} t")
    lines.append(f"    that compute load alone could supply low-grade heat for "
                 f"{hb.o2_supportable_kg_yr/1000:.0f} t O2/yr")
    return "\n".join(lines)


def _format_benefit() -> str:
    r = estimate_benefit()
    return "\n".join([
        "Compute/ISRU cascade benefit and break-even probability:",
        f"  Cascade (reuse heat in ISRU): saves {r.cascade_benefit_t:.2f} t reactor, "
        f"costs {r.integration_cost_t:.2f} t hardware",
        f"    break-even enabling probability P*: nominal {r.cascade_break_even_prob_nominal:.0%}, "
        f"propagated median {r.cascade_break_even_prob_median:.0%}; "
        f"P(worthwhile | co-located) = {r.prob_cascade_worthwhile_if_colocated:.0%}",
        f"  Siting (PSR cold sink for compute): radiator saved per MW (feasible cases) "
        f"median {r.radiator_saved_t_per_mw_median_feasible:.0f} t, IQR "
        f"{r.radiator_saved_t_per_mw_p25_feasible:.0f}-{r.radiator_saved_t_per_mw_p75_feasible:.0f}; "
        f"a sunlit 330 K panel cannot reject in {r.frac_equatorial_infeasible:.0%} of sampled "
        "conditions -- the larger prize and the real driver of co-location",
        f"  Standalone speculative view: full enabling chain ~{r.expected_joint_probability:.0%} "
        f"(illustrative) < P*, so E[cascade net] = {r.expected_cascade_net_t:.2f} t "
        "(not worth it unless co-location already happens for other reasons)",
    ])


def _write_figure(results: dict, path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    items = sorted(results.items(), key=lambda kv: kv[1].nominal)
    names = [r.name for _, r in items]
    nom = np.array([r.nominal for _, r in items])
    lo = np.array([r.nominal - r.p5 for _, r in items])
    hi = np.array([r.p95 - r.nominal for _, r in items])

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(names))
    ax.barh(y, nom, xerr=[lo, hi], color="#3b6", ecolor="#333", capsize=4, alpha=0.85)
    ax.axvspan(24.3 - 5.8, 24.3 + 5.8, color="#88f", alpha=0.15,
               label="Leger 2025 H2-reduction 1$\\sigma$")
    ax.axvline(24.3, color="#44a", ls="--", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Electrical-equivalent energy (kWh per kg O$_2$)")
    ax.set_title("Lunar propellant routes on a common energy basis\n(nominal + 90% Monte-Carlo interval)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    print(f"wrote figure: {path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lunar propellant common-energy model")
    ap.add_argument("-n", type=int, default=20000, help="Monte-Carlo trials")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--markdown", action="store_true", help="emit table as Markdown")
    ap.add_argument("--figure", metavar="PATH", help="write a figure to PATH (needs matplotlib)")
    ap.add_argument("--plant-tonnes", type=float, metavar="T",
                    help="also size the power plant for T tonnes O2/yr per route")
    ap.add_argument("--dominance", action="store_true",
                    help="also print paired-Monte-Carlo dominance probabilities")
    ap.add_argument("--waste-heat", action="store_true",
                    help="also print the low-grade compute-waste-heat offset per route")
    ap.add_argument("--reject-k", type=float, default=350.0,
                    help="compute waste-heat reject temperature (K) for --waste-heat")
    ap.add_argument("--benefit", action="store_true",
                    help="also print the cascade benefit + break-even probability analysis")
    ap.add_argument("--solar-thermal", action="store_true",
                    help="also print baseline vs solar-thermal totals (sunlit-site sensitivity)")
    ap.add_argument("--sensitivity", metavar="ROUTE", choices=list(ROUTES),
                    help="print the one-at-a-time (tornado) sensitivity table for ROUTE")
    ap.add_argument("--sobol", metavar="ROUTE", choices=list(ROUTES),
                    help="print Sobol variance-based sensitivity (first-order + total-effect) for ROUTE")
    ap.add_argument("--sobol-n", type=int, default=4096, help="base sample size for --sobol")
    args = ap.parse_args(argv)

    if args.sensitivity:
        print(_format_sensitivity(args.sensitivity, markdown=args.markdown))
        return 0
    if args.sobol:
        print(_format_sobol(args.sobol, n=args.sobol_n, markdown=args.markdown))
        return 0

    results = evaluate_all(n=args.n, seed=args.seed)
    print(_format_table(results, markdown=args.markdown))
    if args.dominance:
        print()
        print(_format_dominance(compare(n=args.n, seed=args.seed), markdown=args.markdown))
    if args.figure:
        _write_figure(results, args.figure)
    if args.plant_tonnes:
        sizings = size_all(args.plant_tonnes * 1000.0, n=args.n, seed=args.seed)
        print()
        print(_format_plant_table(sizings, args.plant_tonnes, markdown=args.markdown))
    if args.waste_heat:
        print()
        print(_format_waste_heat(args.reject_k, compute_kw=12.0, o2_t=50.0))
    if args.benefit:
        print()
        print(_format_benefit())
    if args.solar_thermal:
        print()
        print(_format_solar_thermal(n=args.n, seed=args.seed, markdown=args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
