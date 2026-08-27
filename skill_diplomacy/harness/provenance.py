"""Run provenance — what a third party needs to know to believe a number.

Every result summary this repository committed described the *configuration* of
a trial (institution, quarantine, seed, endowment) and nothing about the
conditions it ran under. For the deterministic arms that is nearly sufficient:
the code plus the seed reproduces the number, and the code is in git. For the
live arms it is not sufficient at all. `runs/h1/*.json` and `runs/lex/*.json`
record no model identifier, no date, no temperature, no prompt version, and no
commit — so "autarky 0.889, free trade 0.963 on a live model" cannot be
re-derived, audited, or even attributed to a model tier by anyone reading the
repository, including its authors six months on.

Model aliases make this sharper rather than softer. `claude-haiku-4-5` is a
moving pointer; a run in August and a run in November can carry the same string
and be different weights. So we record both what was *asked for* and, where the
client can tell us, what actually *served* the call.

This module is deliberately dependency-free and failure-tolerant: provenance
that raises would be worse than provenance that is partial, so every probe
degrades to a recorded reason rather than an exception.
"""
from __future__ import annotations

import datetime as dt
import platform
import subprocess
from pathlib import Path

# Bump when a change alters what a model is shown or how a response is scored,
# i.e. when live numbers from before and after are no longer comparable.
HARNESS_VERSION = "0.4"

_REPO = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(("git", "-C", str(_REPO)) + args,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def git_state() -> dict:
    """Commit the run was produced at, and whether the tree was dirty.

    A dirty tree is not a disqualification, but an unrecorded dirty tree is:
    it means the committed code and the code that produced the number are not
    known to be the same, and no reader can tell."""
    sha = _git("rev-parse", "HEAD")
    if sha is None:
        return {"commit": None, "dirty": None, "note": "not a git checkout"}
    status = _git("status", "--porcelain")
    return {"commit": sha,
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(status) if status is not None else None}


def describe_model(model) -> dict:
    """What served this run. Clients expose `describe()`; anything that does not
    still gets its class name, which at minimum separates a scripted arm from a
    live one — the distinction every claim in the README turns on."""
    desc = getattr(model, "describe", None)
    if callable(desc):
        try:
            return dict(desc())
        except Exception as e:
            return {"client": type(model).__name__, "describe_error": str(e)}
    return {"client": type(model).__name__}


def run_provenance(model, config: dict | None = None) -> dict:
    """The block stamped into every trial summary.

    `live` is derived from the client rather than declared, because the
    harness/live distinction is the load-bearing status label on every result in
    the README and it should not depend on a human remembering to set a flag."""
    m = describe_model(model)
    return {
        "harness_version": HARNESS_VERSION,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git": git_state(),
        "python": platform.python_version(),
        "model": m,
        "live": bool(m.get("live", type(model).__name__ != "ScriptedModel")),
        "config": dict(config or {}),
    }
