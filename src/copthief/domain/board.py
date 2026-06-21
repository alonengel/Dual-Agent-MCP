"""Board geometry: bounds checking, barriers and neighbour enumeration."""

from __future__ import annotations

import random

from copthief.constants import DIRECTIONS_4, DIRECTIONS_8
from copthief.domain.models import Position


class Board:
    """A configurable 2-D grid that tracks impassable barrier cells."""

    def __init__(self, width: int, height: int, origin: int = 1, diagonal: bool = True):
        self.width = width
        self.height = height
        self.origin = origin
        self.diagonal = diagonal
        self.barriers: set[tuple[int, int]] = set()

    def in_bounds(self, pos: Position) -> bool:
        """True if the cell lies inside the grid limits."""
        return (
            self.origin <= pos.x < self.origin + self.width
            and self.origin <= pos.y < self.origin + self.height
        )

    def is_barrier(self, pos: Position) -> bool:
        """True if the cell holds a barrier."""
        return pos.as_tuple() in self.barriers

    def is_free(self, pos: Position) -> bool:
        """True if the cell is inside the board and not blocked."""
        return self.in_bounds(pos) and not self.is_barrier(pos)

    def add_barrier(self, pos: Position) -> None:
        """Mark a cell as impassable."""
        self.barriers.add(pos.as_tuple())

    def directions(self) -> tuple[tuple[int, int], ...]:
        """Return legal step directions given the diagonal setting."""
        return DIRECTIONS_8 if self.diagonal else DIRECTIONS_4

    def free_neighbours(self, pos: Position) -> list[Position]:
        """All reachable adjacent cells (excludes barriers and out-of-bounds)."""
        result = []
        for dx, dy in self.directions():
            nxt = pos.shifted(dx, dy)
            if self.is_free(nxt):
                result.append(nxt)
        return result

    def random_free_cell(self, rng: random.Random, exclude: set[tuple[int, int]]) -> Position:
        """Pick a uniformly random free cell not in the excluded set."""
        candidates = [
            Position(x, y)
            for x in range(self.origin, self.origin + self.width)
            for y in range(self.origin, self.origin + self.height)
            if (x, y) not in exclude and (x, y) not in self.barriers
        ]
        if not candidates:
            raise ValueError("no free cell available on the board")
        return rng.choice(candidates)
