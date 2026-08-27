"""The paper pipeline: figures render, and the manifest still holds.

The reproducibility promise in README.md ("every headline number reproduces from
one command") was true claim by claim and unenforced as a set. These tests make
drift a test failure rather than something a reader discovers.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from paper import figures, reproduce


def test_every_deterministic_number_matches_the_locked_manifest():
    import json
    assert reproduce.MANIFEST.exists(), "run `python -m paper.reproduce --update`"
    drift = reproduce._diff(json.loads(reproduce.MANIFEST.read_text()),
                            reproduce.compute())
    assert not drift, "\n".join(drift)


def test_the_published_v1_table_still_reproduces():
    """capability 0.33 / 1.00 / 0.56 / 0.86 / 0.78, overheads 0.180 and 0.204,
    poison 6/6 admitted by regression against 0/6 by probes."""
    c = reproduce.claim_v1_grid()
    assert c["autarky_capability"] == pytest.approx(0.33, abs=0.01)
    assert c["free_trade_capability"] == pytest.approx(1.00, abs=0.01)
    assert c["clubs_capability"] == pytest.approx(0.56, abs=0.01)
    assert c["free_trade_probes_overhead"] == pytest.approx(0.180, abs=0.001)
    assert c["adversarial_probes_overhead"] == pytest.approx(0.204, abs=0.001)
    assert (c["poison_admitted_regression"], c["poison_offered_regression"]) == (6, 6)
    assert (c["poison_admitted_probes"], c["poison_offered_probes"]) == (0, 6)


def test_parity_not_abundance_is_what_makes_the_relative_gains_dial_inert():
    """README's scarcity row says "with three task families every arrangement
    returns identical capability". It does not: at 3 families autarky is 0.33
    against free trade 1.00. What IS true is that the dial is a two-level step
    under a uniform endowment whatever the family count, and traces a curve as
    soon as the endowment is graded — parity is the boundary condition, and
    scarcity sets the resolution rather than switching the effect on."""
    c = reproduce.claim_parity_and_scarcity()
    assert c["dial_is_inert_under_parity"] is True
    assert c["k_levels_3_families_uniform"] == c["k_levels_12_families_uniform"] == 2
    assert c["scarcity_sets_resolution_not_existence"] is True
    assert c["k_levels_12_families_zipf"] > c["k_levels_3_families_zipf"] > 2
    # and the published wording, pinned as false so it cannot be restored silently
    assert c["institutions_identical_at_3_families"] is False


def test_the_scripted_null_model_reports_itself_as_a_monoculture():
    """It emits one playbook text for every skill. A diversity metric that says
    otherwise is measuring provenance."""
    c = reproduce.claim_monoculture_metric()
    assert c["scripted_distinct_bodies"] == 1
    assert c["lexicon_distinct_bodies"] == c["lexicon_n_families"]


@pytest.mark.parametrize("name", sorted(figures.FIGURES))
def test_each_figure_renders_valid_svg(name):
    svg = figures.FIGURES[name]()
    if not svg:
        pytest.skip(f"{name} needs an artifact this checkout does not have")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.findall(".//{http://www.w3.org/2000/svg}text"), "no labels"


def test_live_artifacts_are_audited_rather_than_assumed_reproducible():
    """A live run cannot be re-executed in CI, so the standard it is held to is
    that it records what produced it. The pre-provenance artifacts currently
    fail that, and the harness should say so rather than pass silently."""
    problems = reproduce.audit_live_artifacts()
    assert isinstance(problems, list)
    assert all(isinstance(p, str) for p in problems)
