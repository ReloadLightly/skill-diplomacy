"""Per-state budget accounting — the b_t ceilings of the spec (survey §8 / FD B4).

Budgets are the independent variable's currency: institutions are compared at
IDENTICAL per-state budgets, and quarantine costs are charged to the importer,
which is what turns 'governance has a price' into a measured curve.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    pass


@dataclass
class BudgetMeter:
    max_tokens: int
    max_rollouts: int
    tokens_in: int = 0
    tokens_out: int = 0
    rollouts: int = 0
    # governance sub-accounts: tokens/rollouts consumed by screening.
    # Sprint 2 splits these, because v1 priced IMPORT screening only while
    # self-authored edits were committed unconditionally — an asymmetry in
    # exactly the governance story the paper is about. `quarantine_tokens`
    # remains the total so existing folds keep their meaning.
    quarantine_tokens: int = 0
    quarantine_rollouts: int = 0
    import_screen_tokens: int = 0
    self_screen_tokens: int = 0
    ledger: list = field(default_factory=list)

    @property
    def spent_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    @property
    def exhausted(self) -> bool:
        return self.spent_tokens >= self.max_tokens or self.rollouts >= self.max_rollouts

    def charge(self, tokens_in: int = 0, tokens_out: int = 0, rollouts: int = 0,
               kind: str = "task") -> None:
        """Charge spend. Raises BudgetExceeded if the ceiling was already hit
        BEFORE this charge (the charge that crosses the line is still recorded,
        matching 'the attempt that exhausts you still happened')."""
        if self.exhausted:
            raise BudgetExceeded(
                f"budget exhausted: {self.spent_tokens}/{self.max_tokens} tokens, "
                f"{self.rollouts}/{self.max_rollouts} rollouts")
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.rollouts += rollouts
        if kind in ("quarantine", "quarantine_self"):
            self.quarantine_tokens += tokens_in + tokens_out
            self.quarantine_rollouts += rollouts
            if kind == "quarantine":
                self.import_screen_tokens += tokens_in + tokens_out
            else:
                self.self_screen_tokens += tokens_in + tokens_out
        self.ledger.append({"kind": kind, "tokens_in": tokens_in,
                            "tokens_out": tokens_out, "rollouts": rollouts})

    def snapshot(self) -> dict:
        spent = self.spent_tokens
        return {
            "spent_tokens": spent, "rollouts": self.rollouts,
            "quarantine_tokens": self.quarantine_tokens,
            "quarantine_rollouts": self.quarantine_rollouts,
            "import_screen_tokens": self.import_screen_tokens,
            "self_screen_tokens": self.self_screen_tokens,
            "governance_overhead": (self.quarantine_tokens / spent) if spent else 0.0,
            # the two-term decomposition: who is being policed, and at what cost
            "import_screen_overhead": (self.import_screen_tokens / spent) if spent else 0.0,
            "self_screen_overhead": (self.self_screen_tokens / spent) if spent else 0.0,
        }
