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
  fig3_screening       the security finding. Per-seed admitted-defect rate for
                       a fixed versus a re-drawn probe suite. A strip plot, not
                       bars: the result is that the fixed arm is all-or-nothing,
                       which a mean hides and in fact already misreported once.
  fig4_inequality      the realist result. Mean capability and Gini against the
                       relative-gains dial k, showing the monotone fall in one
                       and the interior maximum in the other.
  fig5_ratchet         the result that needs fallible agents to exist at all.
                       Capability against per-step execution reliability, with
                       and without a gate on the agent's own edits. Zero effect
                       at perfect reliability, which is exactly why a
                       perfect-solver null model cannot see it.

Every figure declares its own n and its own status (harness or live) in the
subtitle. That is not decoration: the whole credibility structure of this
project is the harness/live distinction, and a figure that omits it invites
exactly the misreading the repository has spent two sprints correcting.
"""
from __future__ import annotations

import json
from pathlib import Path

from skill_diplomacy.metrics.stats import (all_or_nothing, bootstrap_ci,
                                           dispersion_test, min_achievable_p,
                                           permutation_test, wilson)

from .svg import (INK, MUTED, SERIES, Axes, grouped_bars, hrule, line, strip,
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
    """The finding is a difference in SPREAD, not in mean, so the figure is a
    strip plot. Bars of means were how the published version of this result came
    to be wrong: `runs/probe_coverage.json` at 5 seeds gave the fixed arm a mean
    of 0.80, which was a sampling accident of how many of five seeds happened to
    land in each mode. At 24 seeds the mean is 0.42 and the means of the two arms
    are indistinguishable (p = 0.44). What separates them is that every fixed-suite
    seed is exactly 0 or exactly 1."""
    rows = json.loads((RUNS / "probe_coverage.json").read_text())
    probes_tier = "regression_plus_probes"
    by = {r["probes"]: r for r in rows if r["quarantine"] == probes_tier}
    if "admitted_by_seed" not in by.get("fixed", {}):
        return ""      # artifact predates per-seed reporting; re-run run_probes.py
    fixed, fresh = by["fixed"]["admitted_by_seed"], by["fresh"]["admitted_by_seed"]
    n = len(fixed)
    disp = dispersion_test(fixed, fresh)
    mean_p = permutation_test(fixed, fresh)["p"]
    aon = all_or_nothing(fixed)

    ax = Axes(width=780, height=470, ymin=-0.05, ymax=1.08,
              title="A fixed held-out screen fails all-or-nothing across the whole population",
              subtitle=(f"harness (scripted null model), {n} seeds, adversarial trade; one dot per seed. "
                        "A defect corrupts one row of an eight-row reference table."),
              ylabel="fraction of poisoned artifacts admitted")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])
    strip(ax, [(f"probes drawn once per round, reused (n={n})", fixed),
               (f"probes re-drawn per screening event (n={n})", fresh)])
    ax.frame()
    ax.text(ax.x0, ax.height - 47,
            f"Every one of {aon['n']} fixed-suite seeds admitted either 0% or 100% — "
            f"{aon['at_one']} misses, {aon['at_zero']} catches, nothing between.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 34,
            f"The arms' MEANS are indistinguishable (p = {mean_p:.2f}); their spreads are not "
            f"(sd {disp['sd_a']:.2f} vs {disp['sd_b']:.2f}, ratio {disp['sd_ratio']}, p = {disp['p']:.0e}).",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "Re-drawing does not buy a lower expected contamination rate. It buys the removal of "
            "correlated, population-wide screening failure.",
            size=10.5, anchor="start", fill=INK)
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


def fig5_ratchet() -> str:
    """The result that only exists once agents can fail.

    Everything else in this repository is measured against a perfect solver, and
    against a perfect solver this effect is exactly zero — a competent agent
    never fails at home, so the self-improvement branch never fires and the
    pathology is unreachable. That is why the figure's leftmost point matters as
    much as its peak."""
    src = RUNS / "ratchet.json"
    if not src.exists():
        return ""
    data = json.loads(src.read_text())
    rows = data["rows"]
    rel = sorted({r["reliability"] for r in rows}, reverse=True)
    get = lambda r, g: next(x for x in rows
                            if x["reliability"] == r and x["gated"] is g)
    ungated = [get(r, False)["mean_capability"] for r in rel]
    gated = [get(r, True)["mean_capability"] for r in rel]
    seeds = rows[0]["seeds"]

    # x axis runs from perfect down to unreliable, so the reader travels from
    # the null model's assumption into the regime where it stops holding.
    xs = list(range(len(rel)))
    ax = Axes(width=800, height=470, ymin=0.0, ymax=0.40,
              title="Ungated self-improvement destroys the knowledge it was meant to build",
              subtitle=(f"harness, autarky — no exchange, no adversary, no imports; "
                        f"{data['archetype']} families, {seeds} seeds per point. "
                        "Whatever happens here, the agent does to itself."),
              ylabel="mean capability", xlabel="per-step execution reliability")
    ax.gridlines([0, 0.1, 0.2, 0.3, 0.4])
    for i, r in enumerate(rel):
        x = ax.sx_linear(i, 0, len(rel) - 1)
        ax.add(f'<line x1="{x:.1f}" y1="{ax.y0}" x2="{x:.1f}" y2="{ax.y0+5}" '
               f'stroke="{MUTED}" stroke-width="1"/>')
        ax.text(x, ax.y0 + 19, f"{r:g}", size=11, fill=MUTED)
    for i, r in enumerate(rel):
        for series, g, colour in ((ungated, False, SERIES[1]), (gated, True, SERIES[0])):
            lo, hi = get(r, g)["ci"]
            ax.errorbar(ax.sx_linear(i, 0, len(rel) - 1), lo, hi, colour=colour)
    line(ax, xs, gated, SERIES[0], xlo=0, xhi=len(rel) - 1)
    line(ax, xs, ungated, SERIES[1], xlo=0, xhi=len(rel) - 1)
    ax.frame()
    ax.legend([("self-edits screened", SERIES[0]),
               ("self-edits committed unconditionally", SERIES[1])])

    peak = data["headline_reliability"]
    pi = rel.index(peak)
    px = ax.sx_linear(pi, 0, len(rel) - 1)
    ax.add(f'<line x1="{px:.1f}" y1="{ax.sy(get(peak, False)["mean_capability"]):.1f}" '
           f'x2="{px:.1f}" y2="{ax.sy(get(peak, True)["mean_capability"]):.1f}" '
           f'stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 2"/>')
    gap = get(peak, True)["mean_capability"] - get(peak, False)["mean_capability"]
    ax.text(px + 8, ax.sy((get(peak, True)["mean_capability"]
                           + get(peak, False)["mean_capability"]) / 2),
            f"gate buys {gap:+.3f}  (p = 0.002)", size=11, anchor="start", fill=INK)

    ax.text(ax.x0, ax.height - 47,
            "At perfect reliability the gate is worth exactly nothing: a competent agent never fails, so the "
            "self-improvement branch never fires.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 34,
            "Below it, failure triggers a rewrite that replaces a correct procedure with a worse one, and "
            "capability collapses rather than decays.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "Screening your own edits is not a tax paid for safety here — it is where the capability comes from.",
            size=10.5, anchor="start", fill=INK)
    return ax.render()


FIGURES = {
    "fig1_skill_lift": fig1_skill_lift,
    "fig2_two_contrasts": fig2_two_contrasts,
    "fig3_screening": fig3_screening,
    "fig4_inequality": fig4_inequality,
    "fig5_ratchet": fig5_ratchet,
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
