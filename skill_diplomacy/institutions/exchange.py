"""Export policies — what makes an institution more than a visibility mask.

Sprint 2's central addition. In v1 an "institution" answered only *who can see
whom*; states adopted whatever they were permitted to adopt and never made a
decision. That reduces the IR framing to decoration: clubs are a subgraph,
autarky is the empty graph, and nothing an agent believes affects the outcome.

Here the exporter gets a *choice*. Visibility (the institution) says what is
possible; the export policy says what a state is willing to do. The interesting
regime is the one realists care about: a skill you already possess costs you
nothing to give and raises your rival's capability, so under strict
relative-gains reasoning you should never export — unless you expect to receive
something in return. That expectation is what the policies below formalize.

    open            always export (v1 behaviour; the cooperative baseline)
    reciprocal      export iff the requester holds >= 1 skill I lack
    relative_gains  export iff the requester holds >= s skills I lack, where s
                    is the relative-gains sensitivity dial. s=0 collapses to
                    `open`, s=1 to `reciprocal`, s>=2 is strict realism.
    defector        never export; adopt freely (the free-rider)

The dial matters because it turns a categorical claim ("realists say states
avoid cooperation under anarchy") into a *curve*: exchange volume, mean
capability and capability Gini as functions of s. That curve is a finding; the
v1 visibility masks were not.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExchangeContext:
    """Everything a policy is allowed to know at decision time.

    Deliberately narrow: a state may inspect the public skill INDEX of others
    (names + descriptions, which is what `render_index` publishes) and its own
    memory of past exchanges. It may not read a rival's bodies or capability."""
    libraries: dict = field(default_factory=dict)      # state -> set[str] skill names
    granted: dict = field(default_factory=dict)        # (exporter, importer) -> n exports granted

    def skills_of(self, state: str) -> set:
        return set(self.libraries.get(state, set()))

    def has_granted(self, exporter: str, importer: str) -> int:
        return self.granted.get((exporter, importer), 0)

    def record_grant(self, exporter: str, importer: str) -> None:
        self.granted[(exporter, importer)] = self.granted.get((exporter, importer), 0) + 1


@dataclass
class ExportPolicy:
    name: str = "open"

    def will_export(self, *, exporter: str, importer: str, skill: str,
                    ctx: ExchangeContext) -> tuple[bool, str]:
        """Return (decision, reason). Reason is logged so refusals are auditable."""
        return True, "open"


@dataclass
class RelativeGains(ExportPolicy):
    """Grieco's sensitivity-to-relative-gains coefficient, made operational.

    Handing over a doctrine costs the exporter nothing in absolute terms and
    raises the importer's capability by one unit. A state that cares about gaps
    will only pay that price if the counterparty still holds enough that it
    lacks to make the relationship worth keeping open. So:

        prospective_return = |their skills I lack|      what I might still get
        cost_to_me         = 1                          the unit I hand over
        export  iff  prospective_return >= k * cost_to_me

    `sensitivity` is k. k=0 reproduces `open`; k=1 is plain reciprocity; larger
    k is progressively stricter realism. The dial is only meaningful when the
    family space is large: with three families prospective_return is 0 or 1 and
    every k >= 2 collapses to autarky. With the variant bank (bank/variants.py,
    3*n_variants families) it ranges over 0..F-1 and k traces a curve.

    `mode="balance"` scores the *net* position instead —

        balance = |their skills I lack| - |my skills they lack|

    — which reads better as "am I the net donor?" but measured badly here: once
    endowments are asymmetric the balance distribution is bimodal (a great power
    facing a small state sits at -14, an equal pair at 0), so every threshold
    between those clusters gives the same partition and the dial is a step
    again. Kept because it is the honest thing to compare against, and because
    the two modes disagreeing is itself reportable."""
    name: str = "relative_gains"
    sensitivity: int = 0
    mode: str = "return"          # return (Grieco k) | balance (net donor test)
    reciprocity_credit: int = 1   # value of one past grant received, in skills

    def score(self, mine: set, theirs: set, credits: int = 0) -> int:
        """What the exchange is worth to the exporter, in units of skills.

        Prospective return plus a *quantity* of reciprocity credit, not a
        boolean override. The first version of this policy treated any prior
        grant as an unconditional licence to export, which turned out to swamp
        the dial completely: one exchange between a pair opened the channel
        permanently, so k stopped mattering anywhere in the middle of its range
        and the sweep flattened into a plateau. Reciprocity has to be priced on
        the same scale as capability for the two to trade off."""
        base = (len(theirs - mine) - len(mine - theirs) if self.mode == "balance"
                else len(theirs - mine))
        return base + self.reciprocity_credit * credits

    def will_export(self, *, exporter, importer, skill, ctx) -> tuple[bool, str]:
        mine = ctx.skills_of(exporter)
        theirs = ctx.skills_of(importer)
        credits = ctx.has_granted(importer, exporter)   # what they gave me
        s = self.score(mine, theirs, credits)
        ok = s >= self.sensitivity
        return ok, f"{self.mode}+{credits}c={s}{'>=' if ok else '<'}k={self.sensitivity}"


@dataclass
class Defector(ExportPolicy):
    """Adopts freely, exports never. Present to test whether an institution can
    survive free-riding, which is the question a reviewer will ask first."""
    name: str = "defector"

    def will_export(self, *, exporter, importer, skill, ctx) -> tuple[bool, str]:
        return False, "defector"


def make_policy(kind: str, sensitivity: int = 0, mode: str = "return") -> ExportPolicy:
    if kind == "open":
        return ExportPolicy()
    if kind == "reciprocal":
        return RelativeGains(sensitivity=1)
    if kind == "relative_gains":
        return RelativeGains(sensitivity=sensitivity, mode=mode)
    if kind == "defector":
        return Defector()
    raise ValueError(f"unknown export policy: {kind}")
