"""Command-line entry point: print the cross-route comparison table.

    python -m lpem                # comparison table to stdout
    python -m lpem --figure out.png   # also write a bar+whisker figure (needs matplotlib)
    python -m lpem --markdown     # emit the table as Markdown (used to refresh the paper)
"""

from __future__ import annotations

import argparse

from .arch import size_all
from .model import evaluate_all


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
    args = ap.parse_args(argv)

    results = evaluate_all(n=args.n, seed=args.seed)
    print(_format_table(results, markdown=args.markdown))
    if args.figure:
        _write_figure(results, args.figure)
    if args.plant_tonnes:
        sizings = size_all(args.plant_tonnes * 1000.0, n=args.n, seed=args.seed)
        print()
        print(_format_plant_table(sizings, args.plant_tonnes, markdown=args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
