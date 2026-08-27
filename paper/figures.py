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
                       Capability against per-step execution reliability with the
                       self-improvement loop off and running, under two edit
                       operators. The damage is the operator, not the loop: the
                       same loop that costs everything when it overwrites costs
                       nothing measurable when it appends.

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

from .svg import (GRID, INK, MUTED, SERIES, Axes, grouped_bars, hrule, line,
                  strip, xticks_linear)

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
    """The damage is the edit operator, not the loop and not the missing gate.

    Two curves per panel against per-step execution reliability: capability with
    self-improvement disabled, and with it running unscreened. Left panel, the
    loop replaces the doctrine wholesale; right panel, it appends. Same failures,
    same budget, same absence of screening — the only difference is whether the
    prior doctrine survives the edit."""
    src = RUNS / "ratchet.json"
    if not src.exists():
        return ""
    data = json.loads(src.read_text())
    rows = data["rows"]
    if not rows or "arm" not in rows[0]:
        return ""
    modes = [m for m in data.get("modes", []) if any(r["mode"] == m for r in rows)]
    if len(modes) < 2:
        return ""
    rel = sorted({r["reliability"] for r in rows}, reverse=True)
    get = lambda r, tag, m: next(x for x in rows if x["reliability"] == r
                                 and x["arm"] == tag and x["mode"] == m)
    seeds = rows[0]["seeds"]

    ax = Axes(width=860, height=500, ymin=0.0, ymax=0.40,
              title="A self-improvement loop that overwrites destroys what it was given",
              subtitle=(f"harness, autarky — no exchange, no adversary, no imports; "
                        f"{data['archetype']} families, {seeds} seeds per point. "
                        "Whatever happens here, the agent does to itself."),
              ylabel="mean capability", xlabel="per-step execution reliability")
    ax.gridlines([0, 0.1, 0.2, 0.3, 0.4])
    mid = (ax.x0 + ax.x1) / 2
    ax.add(f'<line x1="{mid:.1f}" y1="{ax.y1}" x2="{mid:.1f}" y2="{ax.y0}" '
           f'stroke="{GRID}" stroke-width="1"/>')
    panels = ((modes[0], ax.x0 + 26, mid - 30,
               "replace — the reply is written over the doctrine"),
              (modes[1], mid + 36, ax.x1 - 22,
               "append — the prior doctrine survives the edit"))
    for mode, px0, px1, label in panels:
        ax.text((px0 + px1) / 2, ax.y1 - 8, label, size=11.5, weight="600")
        for i, r in enumerate(rel):
            x = px0 + (px1 - px0) * i / max(1, len(rel) - 1)
            ax.add(f'<line x1="{x:.1f}" y1="{ax.y0}" x2="{x:.1f}" y2="{ax.y0+5}" '
                   f'stroke="{MUTED}" stroke-width="1"/>')
            ax.text(x, ax.y0 + 19, f"{r:g}", size=10, fill=MUTED)
        for si, (tag, colour) in enumerate((("off", SERIES[0]), ("ungated", SERIES[1]))):
            ys = [get(r, tag, mode)["mean_capability"] for r in rel]
            pts = [(px0 + (px1 - px0) * i / max(1, len(rel) - 1), ax.sy(y))
                   for i, y in enumerate(ys)]
            d = " ".join(("M" if i == 0 else "L") + f"{a:.1f},{b:.1f}"
                         for i, (a, b) in enumerate(pts))
            ax.add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2.2"/>')
            for i, (a, b) in enumerate(pts):
                lo, hi = get(rel[i], tag, mode)["ci"]
                ax.errorbar(a, lo, hi, colour=colour, cap=3.5, width=1.2)
                ax.add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{colour}"/>')
    ax.frame()
    ax.legend([("self-improvement disabled", SERIES[0]),
               ("self-improvement running, unscreened", SERIES[1])])
    ax.text(ax.x0, ax.height - 47,
            "Left: at 97% reliability the loop costs 0.287 — every point of capability the agent was endowed with "
            "(p = 0.0002).",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 34,
            "Right: the same loop, the same failures, the same absence of a gate costs 0.037 and is not significant "
            "(p = 0.11).",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "A gate that rejects the edit recovers the left panel exactly — by being element-wise identical to "
            "not running the loop at all.",
            size=10.5, anchor="start", fill=INK)
    return ax.render()


def fig6_governance_coverage() -> str:
    """Governance under a binding budget is paid in COVERAGE, not competence.

    The published version of this experiment reported "capability 0.627" for the
    unscreened arm at a 160k budget. That number was the product of two
    different things: attempts a state could not pay for were scored as wrong
    answers and left in the denominator. Separated, the unscreened arm answers
    100% of what it attempts and can afford 63% of them — it did not get worse
    at the task, it ran out of money. The screened arm affords nothing at all."""
    src = RUNS / "v2_budget.json"
    if not src.exists():
        return ""
    rows = json.loads(src.read_text())
    budgets = sorted({r["budget"] for r in rows})
    get = lambda b, q: next((r for r in rows
                             if r["budget"] == b and r["quarantine"] == q), None)
    if any(get(b, "none") is None or "attempt_coverage" not in get(b, "none")
           for b in budgets):
        return ""      # artifact predates coverage reporting

    xs = list(range(len(budgets)))
    ax = Axes(width=820, height=470, ymin=0.0, ymax=1.1,
              title="Under a binding budget, screening costs coverage — not competence",
              subtitle=("harness, free trade, 15 states x 30 families, zipf endowment. "
                        "Solid: accuracy on attempts that ran. Dashed: share of "
                        "scheduled attempts the state could afford."),
              ylabel="rate", xlabel="token budget")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])
    for i, b in enumerate(budgets):
        x = ax.sx_linear(i, 0, len(budgets) - 1)
        ax.add(f'<line x1="{x:.1f}" y1="{ax.y0}" x2="{x:.1f}" y2="{ax.y0+5}" '
               f'stroke="{MUTED}" stroke-width="1"/>')
        ax.text(x, ax.y0 + 19, f"{b//1000}k", size=11, fill=MUTED)

    for si, (q, label) in enumerate((("none", "no screening"),
                                     ("regression_plus_probes", "probes"))):
        colour = SERIES[si]
        cap = [get(b, q)["mean_capability"] for b in budgets]
        cov = [get(b, q)["attempt_coverage"] for b in budgets]
        line(ax, xs, cap, colour, xlo=0, xhi=len(budgets) - 1)
        pts = [(ax.sx_linear(x, 0, len(budgets) - 1), ax.sy(y)) for x, y in zip(xs, cov)]
        d = " ".join(("M" if i == 0 else "L") + f"{px:.1f},{py:.1f}"
                     for i, (px, py) in enumerate(pts))
        ax.add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2" '
               f'stroke-dasharray="6 4"/>')
    ax.frame()
    ax.legend([("accuracy / coverage, unscreened", SERIES[0]),
               ("accuracy / coverage, probes", SERIES[1])])
    ax.text(ax.x0, ax.height - 34,
            "At 160k the unscreened arm answers everything it attempts and affords 63% of them; "
            "the screened arm affords none.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "Reported as one number these read as \u201ccapability 0.627\u201d \u2014 a state that could not pay to try, "
            "recorded as one that could not solve.",
            size=10.5, anchor="start", fill=INK)
    return ax.render()


def fig7_sufficiency() -> str:
    """The acceptance rule dominates the screening depth.

    Both panels are admission rate against probe depth, one curve per defect
    symptom rate d. Left: the proportional rule the tier shipped with (accept if
    60% of probes pass). Right: strict (any failure rejects). Same defects, same
    depths, same cost. Under the strict rule the curves fall and track (1-d)^k;
    under the proportional rule the quiet defects rise toward certainty, because
    adding probes concentrates the observed failure fraction on d and a d below
    the rule's tolerance stops producing the chance rejections a shallow screen
    got for free."""
    src = RUNS / "sufficiency.json"
    if not src.exists():
        return ""
    data = json.loads(src.read_text())
    rows = data["rows"]
    if not rows or "threshold" not in rows[0]:
        return ""
    ks = data["probe_grid"]
    ds = sorted({r["detectability"] for r in rows})
    shown = [ds[0], ds[2], ds[4]] if len(ds) >= 5 else ds

    ax = Axes(width=860, height=500, ymin=0.0, ymax=1.08,
              title="A screening rule stated as a pass rate has a blind band",
              subtitle=("harness, adversarial trade, re-drawn probes, 4 seeds. Same defects, "
                        "same depths, same cost — only the acceptance rule differs."),
              ylabel="fraction of poisoned artifacts admitted",
              xlabel="probes drawn per screening event")
    ax.gridlines([0, 0.25, 0.5, 0.75, 1.0])

    # two panels side by side inside one axes
    mid = (ax.x0 + ax.x1) / 2
    ax.add(f'<line x1="{mid:.1f}" y1="{ax.y1}" x2="{mid:.1f}" y2="{ax.y0}" '
           f'stroke="{GRID}" stroke-width="1"/>')
    panels = ((0.6, ax.x0 + 24, mid - 30, "proportional — 60% of probes must pass"),
              (1.0, mid + 34, ax.x1 - 20, "strict — any probe failure rejects"))
    for threshold, px0, px1, label in panels:
        ax.text((px0 + px1) / 2, ax.y1 - 8, label, size=11.5, weight="600")
        for i, k in enumerate(ks):
            x = px0 + (px1 - px0) * i / max(1, len(ks) - 1)
            ax.add(f'<line x1="{x:.1f}" y1="{ax.y0}" x2="{x:.1f}" y2="{ax.y0+5}" '
                   f'stroke="{MUTED}" stroke-width="1"/>')
            ax.text(x, ax.y0 + 19, str(k), size=11, fill=MUTED)
        for si, d in enumerate(shown):
            colour = SERIES[si % len(SERIES)]
            ys = []
            for k in ks:
                r = next((x for x in rows if x["detectability"] == d
                          and x["probes"] == k and x["threshold"] == threshold), None)
                ys.append(r["admitted_rate"] if r else 0.0)
            pts = [(px0 + (px1 - px0) * i / max(1, len(ks) - 1), ax.sy(y))
                   for i, y in enumerate(ys)]
            dpath = " ".join(("M" if i == 0 else "L") + f"{a:.1f},{b:.1f}"
                             for i, (a, b) in enumerate(pts))
            ax.add(f'<path d="{dpath}" fill="none" stroke="{colour}" stroke-width="2.2"/>')
            for a, b in pts:
                ax.add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{colour}"/>')
            # the analytic prediction, for comparison
            tp = [(px0 + (px1 - px0) * i / max(1, len(ks) - 1), ax.sy((1 - d) ** k))
                  for i, k in enumerate(ks)]
            tpath = " ".join(("M" if i == 0 else "L") + f"{a:.1f},{b:.1f}"
                             for i, (a, b) in enumerate(tp))
            ax.add(f'<path d="{tpath}" fill="none" stroke="{colour}" stroke-width="1.2" '
                   f'stroke-dasharray="3 3" opacity="0.6"/>')
    ax.frame()
    ax.legend([(f"defect symptom rate d = {d:.2f}", SERIES[i % len(SERIES)])
               for i, d in enumerate(shown)])
    ax.text(ax.x0, ax.height - 47,
            "Dashed: the analytic prediction (1-d)^k, which assumes a single failure is disqualifying.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 34,
            "Right panel tracks it across the range. Left panel inverts below the rule's tolerance: "
            "at d = 0.18, sixteen probes admit 100%.",
            size=10.5, anchor="start", fill=MUTED)
    ax.text(ax.x0, ax.height - 21,
            "Depth is not a dial on protection unless the rule is strict. Under a pass-rate rule it is a dial on variance.",
            size=10.5, anchor="start", fill=INK)
    return ax.render()


FIGURES = {
    "fig1_skill_lift": fig1_skill_lift,
    "fig2_two_contrasts": fig2_two_contrasts,
    "fig3_screening": fig3_screening,
    "fig4_inequality": fig4_inequality,
    "fig5_ratchet": fig5_ratchet,
    "fig6_governance_coverage": fig6_governance_coverage,
    "fig7_sufficiency": fig7_sufficiency,
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
