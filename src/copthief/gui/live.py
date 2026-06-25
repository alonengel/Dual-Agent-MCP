"""Real-time ASCII board for live terminal display during a match.

Rendered after every turn (verbose self-play / demo) so the agents' and barriers'
movement is visible in real time in the CLI, complementing the saved PNG/filmstrip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copthief.domain.subgame import Subgame

_COP, _THIEF, _BOTH, _BARRIER, _EMPTY = "C", "T", "X", "#", "."


def _cell(pos: tuple[int, int], cop: tuple[int, int], thief: tuple[int, int],
          barriers: set[tuple[int, int]]) -> str:
    """Return the glyph for one board cell (capture shows as X)."""
    if pos == cop and pos == thief:
        return _BOTH
    if pos == cop:
        return _COP
    if pos == thief:
        return _THIEF
    if pos in barriers:
        return _BARRIER
    return _EMPTY


def render_live(game: Subgame, message: str = "") -> str:
    """Render the current board as text rows (top row = highest y), with a legend.

    ``message`` (the turn's taunt) is part of the board-render hook signature but unused
    here: in the terminal the dialogue is already printed on its own line by the reporter.
    """
    board = game.board
    cop, thief = game.cop.as_tuple(), game.thief.as_tuple()
    rows = []
    for y in range(board.origin + board.height - 1, board.origin - 1, -1):
        cells = [_cell((x, y), cop, thief, board.barriers)
                 for x in range(board.origin, board.origin + board.width)]
        rows.append(f"{y:>2} " + " ".join(cells))
    footer = "   " + " ".join(str(x) for x in range(board.origin, board.origin + board.width))
    return "\n".join(rows) + "\n" + footer
