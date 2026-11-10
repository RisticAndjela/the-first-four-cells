"""Permitted timing features at each prediction landmark."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark:
    event: str
    clock: str
    intervals: tuple[str, ...]

    def models(self):
        yield "median", ()
        yield "clock", (self.clock,)
        if self.intervals:
            yield "rhythm", (self.clock, *self.intervals)


LANDMARKS = (
    Landmark("t2", "t2_h", ()),
    Landmark("t3", "t3_h", ("two_cell_h",)),
    Landmark("t4", "t4_h", ("two_cell_h", "three_cell_h")),
)
