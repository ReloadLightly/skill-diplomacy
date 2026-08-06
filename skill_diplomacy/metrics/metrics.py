"""Metrics — every one of these is a pure fold over the event log (spec §4).

pass^k follows the handoff brief's suggestion: the probability that ALL k of k
sampled trials succeed — the consistency-sensitive counterpart of pass@k.
Unbiased estimator per task: C(s, k) / C(n, k) with s successes of n trials."""
from __future__ import annotations

from collections import defaultdict
from math import comb


# -- improvement trajectories (survey §8 protocol) --------------------------

def pass_rate_trajectory(events: list[dict], state: str, window: int = 10) -> list[tuple[int, float]]:
    """(cumulative_budget_tokens, rolling pass-rate) after each attempt."""
    attempts = [e for e in events if e["type"] == "attempt" and e["state"] == state
                and e.get("phase", "eval") == "eval"]
    out, results = [], []
    for e in attempts:
        results.append(1 if e["success"] else 0)
        rate = sum(results[-window:]) / min(len(results), window)
        out.append((e["budget_spent_tokens"], rate))
    return out


def pass_k(trial_outcomes: dict[str, list[bool]], k: int) -> float:
    """Mean over tasks of C(s,k)/C(n,k). Tasks with n<k are skipped."""
    vals = []
    for outcomes in trial_outcomes.values():
        n, s = len(outcomes), sum(outcomes)
        if n >= k:
            vals.append(comb(s, k) / comb(n, k) if s >= k else 0.0)
    return sum(vals) / len(vals) if vals else 0.0


def trials_by_task(events: list[dict], state: str) -> dict[str, list[bool]]:
    d: dict[str, list[bool]] = defaultdict(list)
    for e in events:
        if (e["type"] == "attempt" and e["state"] == state
                and e.get("phase", "eval") == "eval"):
            d[e["task_id"]].append(bool(e["success"]))
    return dict(d)


# -- inequality (relative gains / realist critique) -------------------------

def gini(values: list[float]) -> float:
    if not values or all(v == 0 for v in values):
        return 0.0
    xs = sorted(values)
    n = len(xs)
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


# -- the trade network ------------------------------------------------------

def adoption_edges(events: list[dict]) -> list[dict]:
    return [{"importer": e["state"], "exporter": e["exporter"],
             "skill": e["skill"], "accepted": e["accepted"],
             "poisoned": e.get("poisoned", False),
             "first_hand": e.get("first_hand", e.get("poisoned", False)),
             "content_hash": e.get("content_hash")}
            for e in events if e["type"] == "adoption_decision"]


def poison_spread(events: list[dict]) -> dict:
    """RQ3. `first_hand` = adopted directly from a designated poisoner;
    `transitive` = adopted from an honest intermediary that had itself been
    infected. The second number is the one the research question is actually
    about, and in v1 it was structurally always zero (defect 3.1)."""
    edges = adoption_edges(events)
    offered = [e for e in edges if e["poisoned"]]
    adopted = [e for e in offered if e["accepted"]]
    first_hand = [e for e in adopted if e["first_hand"]]
    transitive = [e for e in adopted if not e["first_hand"]]
    unique_offered = {e["content_hash"] for e in offered if e["content_hash"]}
    return {"offered": len(offered), "adopted": len(adopted),
            "first_hand_adopted": len(first_hand),
            "transitive_adopted": len(transitive),
            "unique_offered": len(unique_offered),
            "adoption_rate": (len(adopted) / len(offered)) if offered else 0.0}


def export_refusals(events: list[dict]) -> dict:
    """Sprint 2. How often the export POLICY (not the institution's visibility
    mask) blocked an exchange, and why. Zero under `open`, by construction."""
    evs = [e for e in events if e["type"] == "export_decision"]
    granted = [e for e in evs if e["granted"]]
    reasons: dict[str, int] = defaultdict(int)
    for e in evs:
        if not e["granted"]:
            reasons[e.get("reason", "?")] += 1
    return {"requests": len(evs), "granted": len(granted),
            "refused": len(evs) - len(granted),
            "refusal_rate": ((len(evs) - len(granted)) / len(evs)) if evs else 0.0,
            "reasons": dict(reasons)}


# -- diversity / monoculture (RQ2) ------------------------------------------

def mean_pairwise_similarity(libraries: list) -> float:
    """Mean Jaccard over all unordered pairs of skill libraries.

    RQ2 had no output at all in v1: `jaccard`/`shingles` existed and were unit
    tested but nothing reported them. Monoculture is the result MAP-Elites'
    entire rationale in ACTIR rests on, so it gets a headline number."""
    from ..skills.format import jaccard
    if len(libraries) < 2:
        return 0.0
    vals = [jaccard(libraries[i], libraries[j])
            for i in range(len(libraries)) for j in range(i + 1, len(libraries))]
    return sum(vals) / len(vals)


def distinct_bodies(libraries: list) -> int:
    """Number of distinct skill CONTENTS across the whole population. Falls as
    one doctrine out-competes the rest — the direct monoculture signal."""
    seen = set()
    for lib in libraries:
        for name in lib.skill_names():
            seen.add(lib.content_hash(name))
    return len(seen)
