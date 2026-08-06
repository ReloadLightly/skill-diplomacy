"""Calendar arithmetic. Ground truth via datetime — exact by construction.
Difficulty dial: day offsets and week/weekday phrasing variants."""
from __future__ import annotations

import datetime as dt
import random

from ..base import Generator, TaskInstance


class CalendarMathGenerator(Generator):
    family = "calendar_math"

    def __init__(self, epoch: dt.date | None = None,
                 span: tuple[int, int] = (45, 900)):
        # variant dials (bank/variants.py): a disjoint epoch and offset span make
        # each variant a distinct region of the date line rather than a relabel.
        self.epoch = epoch or dt.date(2020, 1, 1)
        self.span = span

    def generate(self, rng: random.Random) -> TaskInstance:
        start = self.epoch + dt.timedelta(days=rng.randint(0, 4000))
        delta = rng.randint(*self.span) * rng.choice([1, -1])
        mode = rng.choice(["date", "weekday"])
        target = start + dt.timedelta(days=delta)
        direction = "after" if delta > 0 else "before"
        if mode == "date":
            q = (f"What is the date {abs(delta)} days {direction} {start.isoformat()}? "
                 "Answer in ISO format (YYYY-MM-DD).")
            answer = target.isoformat()
        else:
            q = f"What day of the week is {abs(delta)} days {direction} {start.isoformat()}?"
            answer = target.strftime("%A")
        prompt = q + "\nShow your reasoning, then give the final line as `ANSWER: <value>`."
        tid = f"calendar_math-{rng.getrandbits(32):08x}"
        return TaskInstance(tid, self.family, prompt, answer,
                            {"start": start.isoformat(), "delta": delta, "mode": mode})
