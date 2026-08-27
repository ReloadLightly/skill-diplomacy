"""The paper's figures, regenerated from committed artifacts.

    python -m paper.figures            # -> paper/fig/*.svg

The draft in LETTER.md carries no figures at all. These are the four that do
the argument's work, in the order the argument makes them:

  fig1_skill_lift      the instrument. Per-family floor and with-skill rate with
                       Wilson intervals, which is where the reader sees that the
                       diagnostic is currently applied at an n too small to
                       resolve its own three regimes.
  fig2_two_contrasts   the result. The same institutional comparison over
                       saturated and over load-bearing families, with bootstrap
                       intervals and the exact-permutation p-floor annotated, so
                       the design limit is on the figure rather than in a
                       footnote a reviewer has to find.
  fig3_screening       the security finding. Admitted-defect rate against
                       governance overhead for each quarantine tier, fixed
                       versus re-drawn probes — the "held out matters less than
                       re-drawn" result.
  fig4_inequality      the realist result. Mean capability and Gini against the
                       relative-gains dial k, showing the monotone fall in one
                       and the interior maximum in the other.

Every figure declares its own n and its own status (harness or live) in the
subtitle. That is not decoration: the whole credibility structure of this
project is the harness/live distinction, and a figure that omits it invites
exactly the misreading the repository has spent two sprints correcting.
"""
from __future__ import annotations

import json
from pathlib import Path

from skill_diplomacy.metrics.stats import (bootstrap_ci, min_achievable_p,
                                           permutation_test, wilson)

from .svg import (INK, MUTED, SERIES, Axes, grouped_bars, hrule, line,
                  xticks_linear)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = Path(__file__).resolve().parent / "fig"

# Instances per family behind runs/skill_lift_live.json. Not recorded in the
# artifact itself, which is its own small provenance failure; calibrate.py's
# default is 6 and LETTER.md states 6.
LIFT_N = 6


def _caps(pattern: str) -> list[float]:
    return [json.loads(p.read_text())["mean_capability"]
            for p in sorted(RUNS.glob(pattern))]


# ---------------------------------------------------------------------------

def fig1_skill_lift() -> str:
    rows = json.loads((RUNS / "skill_lift_live.json").read_text())
    cats = [r["family"] for r in rows]
    floors = [r["no_skill"] for r in rows]
    withs = [r["with_skill"] for r in rows]
    err_f = [wilson(round(v * LIFT_N), LIFT_N) for v in floors]
    err_w = [wilson(round(v * LIFT_N), LIFT_N) for v in withs]

    ax = Axes(width=780, height=430, ymin=0.0, ymax=1.0,
              title="Skill lift is measured at an n that cannot resolve its own verdicts",
              subtitle=(f"live, Claude Haiku 4.5, n={LIFT_N} instances per family; "
                        "bars are Wilson 95% intervals"),
              ylabel="P(solve)", xlabel="task family")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])
    hrule(ax, 0.8, "saturation threshold used by calibrate.py (floor ≥ 0.80)")
    grouped_bars(ax, cats,
                 [("empty library (floor)", floors), ("reference skill installed", withs)],
                 errors=[err_f, err_w],
                 annotations=[f"lift {r['lift']:+.2f}" for r in rows])
    ax.frame()
    # The point of the figure, said once, on the figure.
    ax.text(ax.x0, ax.height - 34,
            "Every interval spans ≥0.39. unit_chain's 6/6 floor is consistent with a true rate of 0.61,",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "and modmath's −0.17 lift is not distinguishable from zero.",
            size=10.5, anchor="start", fill=MUTED)
    return ax.render()


def fig2_two_contrasts() -> str:
    sat_a, sat_f = _caps("h1/autarky_s*.json"), _caps("h1/free_trade_s*.json")
    lex_a, lex_f = _caps("lex/autarky_none_s*.json"), _caps("lex/free_trade_none_s*.json")
    pairs = [("saturated families\n(unit_chain, calendar, modmath)", sat_a, sat_f),
             ("load-bearing families\n(lexicon x3)", lex_a, lex_f)]

    ax = Axes(width=780, height=450, ymin=0.0, ymax=1.15,
              title="The institutional effect appears only where the skill carries information",
              subtitle="live, Claude Haiku 4.5, 3 seeds per arm; bars are seeded percentile bootstrap 95% intervals",
              ylabel="mean capability")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])

    cats, aut, fre, e_a, e_f, notes = [], [], [], [], [], []
    for label, a, f in pairs:
        ba, bf = bootstrap_ci(a), bootstrap_ci(f)
        perm = permutation_test(a, f)
        cats.append(label.replace("\n", " "))
        aut.append(ba["mean"]); fre.append(bf["mean"])
        e_a.append((ba["ci_low"], ba["ci_high"])); e_f.append((bf["ci_low"], bf["ci_high"]))
        notes.append(f"Δ = {bf['mean']-ba['mean']:+.3f}   p = {perm['p']:.2f} (exact)")

    grouped_bars(ax, cats, [("autarky", aut), ("free trade", fre)],
                 errors=[e_a, e_f], annotations=notes)
    ax.frame()
    floor = min_achievable_p(3, 3)
    ax.text(ax.x0, ax.height - 34,
            f"With 3 seeds per arm an exact permutation test cannot return p below {floor:.2f} "
            f"(C(6,3) = 20 arrangements),",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "so the right-hand contrast is at the design's floor despite separating perfectly. "
            "Five seeds per arm would reach 0.008.",
            size=10.5, anchor="start", fill=MUTED)
    return ax.render()


def fig3_screening() -> str:
    rows = json.loads((RUNS / "probe_coverage.json").read_text())
    ax = Axes(width=780, height=440, ymin=0.0, ymax=1.05,
              title="Whether a screen is re-drawn matters more than whether it is held out",
              subtitle=("harness (scripted null model), 5 seeds; a defect corrupting one row "
                        "of an eight-row reference table"),
              ylabel="fraction of poisoned artifacts admitted",
              xlabel="governance overhead (share of budget spent screening)")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])
    hrule(ax, 1.0, "no screening at all", colour="#b91c1c")

    xlo, xhi = 0.0, 0.75
    xticks_linear(ax, [0.0, 0.15, 0.3, 0.45, 0.6, 0.75], xlo, xhi)
    for si, mode in enumerate(("fixed", "fresh")):
        pts = [r for r in rows if r["probes"] == mode]
        order = {"none": 0, "regression": 1, "regression_plus_probes": 2}
        pts.sort(key=lambda r: order[r["quarantine"]])
        line(ax, [r["governance_overhead"] for r in pts],
             [r["admitted_rate"] for r in pts], SERIES[si],
             label=f"{mode} probes", xlo=xlo, xhi=xhi)
        for r in pts:
            x = ax.sx_linear(r["governance_overhead"], xlo, xhi)
            y = ax.sy(r["admitted_rate"])
            short = {"none": "none", "regression": "regression",
                     "regression_plus_probes": "+ probes"}[r["quarantine"]]
            ax.text(x, y - 11, short, size=10, fill=MUTED)
    ax.frame()
    ax.legend([("probes drawn once per round, reused", SERIES[0]),
               ("probes re-drawn per screening event", SERIES[1])])
    ax.text(ax.x0, ax.height - 34,
            "Home-shard regression pays 23% of the budget and admits 100%: expensive and perfectly blind.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "A fixed held-out suite has one hole and every importer falls into it at once (80% admitted); "
            "re-drawing cuts that to 29%.",
            size=10.5, anchor="start", fill=MUTED)
    return ax.render()


def fig4_inequality() -> str:
    src = RUNS / "v2_k.json"
    if not src.exists():
        return ""
    rows = json.loads(src.read_text())
    ks = [r["k"] for r in rows]
    caps = [r["mean_capability"] for r in rows]
    ginis = [r["capability_gini"] for r in rows]

    ax = Axes(width=780, height=450, ymin=0.0, ymax=max(0.75, max(ginis + caps) * 1.15),
              title="Capability falls monotonically in k; inequality peaks in the interior",
              subtitle=(f"harness (scripted null model); k is the relative-gains sensitivity of "
                        f"the export policy, swept over {len(ks)} values"),
              ylabel="capability / Gini", xlabel="relative-gains sensitivity k")
    ax.gridlines([0, 0.2, 0.4, 0.6])
    xticks_linear(ax, ks[::max(1, len(ks) // 8)], min(ks), max(ks),
                  fmt=lambda v: str(int(v)))
    line(ax, ks, caps, SERIES[0], xlo=min(ks), xhi=max(ks))
    line(ax, ks, ginis, SERIES[1], xlo=min(ks), xhi=max(ks))
    peak = max(range(len(ginis)), key=lambda i: ginis[i])
    px, py = ax.sx_linear(ks[peak], min(ks), max(ks)), ax.sy(ginis[peak])
    ax.add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6.5" fill="none" '
           f'stroke="{INK}" stroke-width="1.4"/>')
    ax.text(px, py - 14, f"interior maximum: Gini {ginis[peak]:.2f} at k={ks[peak]:g}",
            size=10.5, fill=INK)
    ax.frame()
    ax.legend([("mean capability", SERIES[0]), ("capability Gini", SERIES[1])])
    ax.text(ax.x0, ax.height - 21,
            "Strict refusal produces not a hierarchy but a flat, uniformly poor population — "
            "the rich stop trading too.",
            size=10.5, anchor="start", fill=MUTED)
    return ax.render()


FIGURES = {
    "fig1_skill_lift": fig1_skill_lift,
    "fig2_two_contrasts": fig2_two_contrasts,
    "fig3_screening": fig3_screening,
    "fig4_inequality": fig4_inequality,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in FIGURES.items():
        try:
            svg = fn()
        except FileNotFoundError as e:
            print(f"  {name:<20} SKIPPED — missing artifact: {e.filename}")
            continue
        if not svg:
            print(f"  {name:<20} SKIPPED — run `python run_v2.py --sweep k` first")
            continue
        path = OUT / f"{name}.svg"
        path.write_text(svg)
        print(f"  {name:<20} -> {path.relative_to(ROOT)}  ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
