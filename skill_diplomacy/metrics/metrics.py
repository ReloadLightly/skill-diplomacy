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
             "poisoned": e.get("poisoned", False)}
            for e in events if e["type"] == "adoption_decision"]


def poison_spread(events: list[dict]) -> dict:
    edges = adoption_edges(events)
    poisoned_adopted = [e for e in edges if e["poisoned"] and e["accepted"]]
    poisoned_offered = [e for e in edges if e["poisoned"]]
    return {"offered": len(poisoned_offered), "adopted": len(poisoned_adopted),
            "adoption_rate": (len(poisoned_adopted) / len(poisoned_offered)
                              if poisoned_offered else 0.0)}
