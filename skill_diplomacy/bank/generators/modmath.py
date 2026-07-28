"""Modular arithmetic: a^b mod m. Ground truth via pow(a, b, m).
Difficulty dial: exponent size. Requires actual computation (or a written
tool — the intended skill), not recall."""
from __future__ import annotations

import random

from ..base import Generator, TaskInstance


class ModMathGenerator(Generator):
    family = "modmath"

    def __init__(self, exp_range: tuple[int, int] = (20, 400)):
        self.exp_range = exp_range

    def generate(self, rng: random.Random) -> TaskInstance:
        a = rng.randint(3, 60)
        b = rng.randint(*self.exp_range)
        m = rng.choice([97, 101, 103, 251, 509, 1009, 4093])
        answer = pow(a, b, m)
        prompt = (f"Compute {a}^{b} mod {m}.\n"
                  "Show your reasoning, then give the final line as `ANSWER: <integer>`.")
        tid = f"modmath-{rng.getrandbits(32):08x}"
        return TaskInstance(tid, self.family, prompt, str(answer), {"a": a, "b": b, "m": m})
