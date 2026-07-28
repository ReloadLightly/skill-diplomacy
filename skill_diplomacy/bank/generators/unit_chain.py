"""Unit-conversion chains over INVENTED units.

Invented units (1 flib = 7 blem, ...) guarantee the model cannot answer from
memorized real-world conversions — it must compose the chain given in the
prompt. Integer factors and integer quantities make ground truth an exact
integer product. Difficulty dial: chain depth.
"""
from __future__ import annotations

import random

from ..base import Generator, TaskInstance

_UNIT_NAMES = ["flib", "blem", "quon", "drap", "snib", "torv",
               "melk", "zarn", "pyx", "grol", "vint", "hesk"]


class UnitChainGenerator(Generator):
    family = "unit_chain"

    def __init__(self, depth: tuple[int, int] = (2, 4)):
        self.depth = depth

    def generate(self, rng: random.Random) -> TaskInstance:
        k = rng.randint(*self.depth)
        units = rng.sample(_UNIT_NAMES, k + 1)
        factors = [rng.randint(2, 12) for _ in range(k)]
        qty = rng.randint(2, 30)
        rules = [f"1 {units[i]} = {factors[i]} {units[i + 1]}" for i in range(k)]
        answer = qty
        for f in factors:
            answer *= f
        prompt = (
            "Conversion rules:\n" + "\n".join(f"- {r}" for r in rules) +
            f"\n\nHow many {units[-1]} are in {qty} {units[0]}?\n"
            "Show your reasoning, then give the final line as `ANSWER: <integer>`."
        )
        tid = f"unit_chain-{rng.getrandbits(32):08x}"
        return TaskInstance(tid, self.family, prompt, str(answer),
                            {"qty": qty, "factors": factors, "units": units})
