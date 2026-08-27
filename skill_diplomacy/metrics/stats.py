"""Uncertainty — the layer this repository reported results without.

Every number in README.md and LETTER.md is a point estimate. Two of them carry
a hand-computed standard deviation in prose; none carries an interval, none
carries a test, and nothing anywhere states how large an effect the design was
capable of detecting. That is the gap a methods reviewer opens on first, and it
is not closed by running more seeds alone — it is closed by reporting what the
seeds can and cannot support.

Three quantities, and one diagnostic that matters more than either.

**Proportions.** Skill lift is measured over six instances per family
(`runs/skill_lift_live.json`). A six-trial proportion is a very wide thing. The
normal approximation is not usable at that n — it produces intervals that leave
the unit interval — so `wilson` is used throughout, which is well-behaved at
small n and at proportions near 0 and 1, exactly where this bank sits.

**Differences.** The headline live contrast is a difference of arm means over
three seeds each. With n that small the only defensible test is exact and
non-parametric: enumerate every way the observed values could have been split
between the arms and ask how often chance does this well.

**Detectability.** And here is the diagnostic that should be read before any
p-value: with three seeds per arm there are C(6,3)=20 distinct assignments, so
the smallest two-sided p an exact permutation test can EVER return is 2/20 =
0.10 — regardless of how large the effect is. A three-seed design cannot reach
p<0.05 two-sided even if the separation is perfect. `min_achievable_p` computes
this, `compare` reports it beside the p-value, and a design that cannot clear
its own threshold is a design fact to state, not a result to report.
"""
from __future__ import annotations

import random
from itertools import combinations
from math import comb, sqrt
from statistics import NormalDist, mean, pstdev

__all__ = ["wilson", "proportion", "bootstrap_ci", "permutation_test",
           "min_achievable_p", "compare", "fmt"]


# -- proportions -------------------------------------------------------------

def wilson(successes: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the normal ("Wald") approximation because the quantities this
    repository measures are small-n proportions pinned near 0 or 1 — a lexicon
    floor of 0/6, a saturated family at 6/6 — where Wald returns a zero-width
    interval and asserts certainty the data cannot support."""
    if n <= 0:
        return (0.0, 1.0)
    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(successes: int, n: int, conf: float = 0.95) -> dict:
    lo, hi = wilson(successes, n, conf)
    return {"successes": successes, "n": n,
            "estimate": (successes / n) if n else 0.0,
            "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            "ci_width": round(hi - lo, 4), "conf": conf}


# -- means -------------------------------------------------------------------

def bootstrap_ci(values: list[float], conf: float = 0.95, reps: int = 10_000,
                 seed: int = 0) -> dict:
    """Percentile bootstrap over the mean. Seeded, so it is as reproducible as
    everything else here.

    At n=3 the bootstrap resamples from three points and can only ever return
    one of a handful of distinct means; the interval is honest about the
    design's coarseness rather than smoothing it away, which is the point."""
    vals = list(values)
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "sd": 0.0}
    if n == 1:
        return {"n": 1, "mean": vals[0], "ci_low": vals[0], "ci_high": vals[0],
                "sd": 0.0, "note": "n=1: no interval is estimable"}
    rng = random.Random(seed)
    means = sorted(mean(rng.choices(vals, k=n)) for _ in range(reps))
    lo = means[int((1 - conf) / 2 * reps)]
    hi = means[min(reps - 1, int((1 + conf) / 2 * reps))]
    return {"n": n, "mean": round(mean(vals), 4),
            "sd": round(pstdev(vals), 4),
            "ci_low": round(lo, 4), "ci_high": round(hi, 4), "conf": conf}


# -- differences -------------------------------------------------------------

def min_achievable_p(n_a: int, n_b: int, two_sided: bool = True) -> float:
    """The smallest p an exact permutation test can return for these group
    sizes — the floor imposed by the DESIGN, before any data exist.

    Read this before the p-value. Three seeds per arm gives C(6,3)=20
    arrangements and a two-sided floor of 0.10: such a design cannot produce a
    conventionally significant result however cleanly the arms separate. That is
    a statement about how many seeds to run, and it costs nothing to check."""
    total = comb(n_a + n_b, n_a)
    if total == 0:
        return 1.0
    return min(1.0, (2.0 if two_sided else 1.0) / total)


def permutation_test(a: list[float], b: list[float], two_sided: bool = True,
                     max_exact: int = 100_000, reps: int = 20_000,
                     seed: int = 0) -> dict:
    """Exact permutation test on the difference of means, Monte Carlo above
    `max_exact` arrangements.

    Non-parametric and assumption-free, which is what n=3 per arm requires: a
    t-test here would be asserting normality on the basis of three points."""
    a, b = list(a), list(b)
    n_a, n_b = len(a), len(b)
    if n_a == 0 or n_b == 0:
        return {"observed": 0.0, "p": 1.0, "n_a": n_a, "n_b": n_b,
                "method": "undefined", "note": "an empty arm"}
    pool = a + b
    observed = mean(a) - mean(b)
    total = comb(n_a + n_b, n_a)

    def extreme(d: float) -> bool:
        return abs(d) >= abs(observed) - 1e-12 if two_sided else d >= observed - 1e-12

    if total <= max_exact:
        hits = 0
        idx = range(len(pool))
        for pick in combinations(idx, n_a):
            sa = [pool[i] for i in pick]
            rest = set(pick)
            sb = [pool[i] for i in idx if i not in rest]
            if extreme(mean(sa) - mean(sb)):
                hits += 1
        p, method, n_perm = hits / total, "exact", total
    else:
        rng = random.Random(seed)
        hits = 0
        for _ in range(reps):
            shuffled = pool[:]
            rng.shuffle(shuffled)
            if extreme(mean(shuffled[:n_a]) - mean(shuffled[n_a:])):
                hits += 1
        # +1 smoothing: a Monte Carlo p of exactly 0 is not evidence of p=0
        p, method, n_perm = (hits + 1) / (reps + 1), "monte_carlo", reps
    return {"observed": round(observed, 4), "p": round(p, 4), "method": method,
            "n_a": n_a, "n_b": n_b, "arrangements": n_perm,
            "two_sided": two_sided}


def compare(a: list[float], b: list[float], label_a: str = "a",
            label_b: str = "b", conf: float = 0.95, seed: int = 0) -> dict:
    """The full report for one arm-versus-arm contrast.

    Deliberately returns `min_p` and `design_can_reach_significance` alongside
    the p-value, so a result cannot be quoted without the design fact that
    bounds it. `interpretable` additionally flags the case this repository
    already walked into once: an effect smaller than the noise it sits in, which
    is what the +0.074 live gap against a 0.111 seed-to-seed spread was."""
    ba, bb = bootstrap_ci(a, conf, seed=seed), bootstrap_ci(b, conf, seed=seed)
    diff = ba["mean"] - bb["mean"]
    perm = permutation_test(a, b, seed=seed)
    floor = min_achievable_p(len(a), len(b))
    pooled_sd = pstdev(list(a) + list(b)) if len(a) + len(b) > 1 else 0.0
    return {
        label_a: ba,
        label_b: bb,
        "difference": round(diff, 4),
        "pooled_sd": round(pooled_sd, 4),
        "effect_vs_noise": (round(abs(diff) / pooled_sd, 2) if pooled_sd else None),
        "p": perm["p"],
        "p_method": perm["method"],
        "min_p": round(floor, 4),
        "design_can_reach_significance": floor <= 0.05,
        "interpretable": bool(pooled_sd == 0 or abs(diff) > pooled_sd),
        "seeds_per_arm": (len(a), len(b)),
    }


def fmt(d: dict) -> str:
    """`0.333 [0.333, 0.333] (n=3)` — the form a table cell should carry."""
    return (f"{d['mean']:.3f} [{d['ci_low']:.3f}, {d['ci_high']:.3f}] "
            f"(n={d['n']})")
