"""A Bayes filter over the opponent's cell — a probability grid for partial observation.

``BeliefGrid`` keeps a normalised distribution over the board's free cells (barriers carry
zero mass — impassable to both agents). It realises the Dec-POMDP observation function via
three channels:

* :meth:`diffuse` — physics: the opponent is forced one 8-direction step each ply, so every
  cell hands its mass to its free neighbours;
* :meth:`observe_not_at` — hard negative info (a commit-reveal mismatch, or "no capture, so
  the rival is not on my cell") zeroes a cell;
* :meth:`observe_claim` — a *soft* nudge toward a fallible free-text claim.

Coordinates are this project's origin-aware ``Position(x, y)``; the distribution is held as a
width x height numpy array indexed ``[x-origin, y-origin]``.
"""

from __future__ import annotations

import numpy as np

from copthief.domain.board import Board
from copthief.domain.models import Position


class BeliefGrid:
    """A normalised belief distribution over a board's free cells."""

    def __init__(self, board: Board):
        self.board = board
        self.reset_uniform()

    def reset_uniform(self) -> None:
        """Reset to a uniform prior over the free cells (maximal entropy)."""
        grid = np.zeros((self.board.width, self.board.height))
        for x in range(self.board.origin, self.board.origin + self.board.width):
            for y in range(self.board.origin, self.board.origin + self.board.height):
                if self.board.is_free(Position(x, y)):
                    grid[self._ix(x, y)] = 1.0
        self._grid = grid
        self._normalize()

    def _ix(self, x: int, y: int) -> tuple[int, int]:
        """Map a board coordinate to a grid index."""
        return x - self.board.origin, y - self.board.origin

    def as_array(self) -> np.ndarray:
        """A copy of the distribution (sums to 1) as a width x height array."""
        return self._grid.copy()

    def set_point(self, pos: Position) -> None:
        """Collapse to a point mass at ``pos`` — a confirmed sighting."""
        self._grid = np.zeros_like(self._grid)
        self._grid[self._ix(pos.x, pos.y)] = 1.0

    def most_likely(self) -> Position:
        """The cell carrying the most belief mass (row-major tie-break)."""
        fx, fy = np.unravel_index(int(np.argmax(self._grid)), self._grid.shape)
        return Position(int(fx) + self.board.origin, int(fy) + self.board.origin)

    def expected_distance(self, cell: Position) -> float:
        """``Σ P(c)·Chebyshev(cell, c)`` — expected distance to the belief mass."""
        total = 0.0
        for (fx, fy), prob in np.ndenumerate(self._grid):
            if prob > 0.0:
                d = max(abs(cell.x - (fx + self.board.origin)),
                        abs(cell.y - (fy + self.board.origin)))
                total += float(prob) * d
        return total

    def diffuse(self) -> None:
        """Physics update: each cell spreads its mass equally to its free neighbours."""
        nxt = np.zeros_like(self._grid)
        for x in range(self.board.origin, self.board.origin + self.board.width):
            for y in range(self.board.origin, self.board.origin + self.board.height):
                mass = self._grid[self._ix(x, y)]
                if mass == 0.0:
                    continue
                neighbours = self.board.free_neighbours(Position(x, y))
                if not neighbours:
                    nxt[self._ix(x, y)] += mass  # stranded mass stays rather than vanishing
                    continue
                share = mass / len(neighbours)
                for nb in neighbours:
                    nxt[self._ix(nb.x, nb.y)] += share
        self._grid = nxt
        self._normalize()

    def observe_not_at(self, pos: Position) -> None:
        """Hard negative info: rule the opponent out of ``pos`` (zero its mass)."""
        self._grid[self._ix(pos.x, pos.y)] = 0.0
        if self._grid.sum() == 0.0:
            self.reset_uniform()  # ruled-out cell held all the mass: fall back to the prior
        else:
            self._normalize()

    def observe_claim(self, pos: Position, discount: float) -> None:
        """Soft update toward a fallible claim: ``grid = (1-d)·grid + d·onehot(pos)``."""
        if discount <= 0.0 or not self.board.is_free(pos):
            return
        onehot = np.zeros_like(self._grid)
        onehot[self._ix(pos.x, pos.y)] = 1.0
        self._grid = (1.0 - discount) * self._grid + discount * onehot
        self._normalize()

    def _normalize(self) -> None:
        """Rescale so the distribution sums to 1 (no-op on an all-zero grid)."""
        total = self._grid.sum()
        if total > 0.0:
            self._grid /= total
