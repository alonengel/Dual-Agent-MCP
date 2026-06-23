"""An agent: a role-bound bundle of strategy, LLM voice and a belief about the rival.

The agent decides a move via its strategy, verbalises it through the LLM, and updates
its belief from vision and the opponent's free-text message. When a cop loses sight of
the thief it does not idle at the board centre — it **hunts**: it makes for the cell
where the thief was last seen and then sweeps the corners to flush it out.
"""

from __future__ import annotations

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.llm.base import LLMProvider
from copthief.orchestrator import dialogue
from copthief.strategy.base import Strategy, chebyshev


class Agent:
    """Wraps one side's decision-making and natural-language communication."""

    def __init__(self, role: Role, strategy: Strategy, provider: LLMProvider):
        self.role = role
        self.strategy = strategy
        self.provider = provider
        self.skeptical = False  # a counter-intelligence cop that distrusts proven lies
        self.belief: Position | None = None
        self.belief_trusted = False  # True only when the belief came from direct sight
        self.trust_claims = True     # cleared once a stated position is exposed as a lie
        self.last_seen: Position | None = None  # cop: last cell the thief was seen in
        self._patrol = 0                         # cop: index into the corner sweep

    def reset(self) -> None:
        """Forget all per-subgame state so each subgame starts from a clean slate."""
        self.belief = None
        self.belief_trusted = False
        self.trust_claims = True
        self.last_seen = None
        self._patrol = 0

    def update_belief_from(self, message: str) -> Position | None:
        """Adopt a position stated by the rival. A skeptical cop treats it as a single
        *unverified lead* (it ignores further chatter until it checks this one, and a
        proven liar is ignored entirely); everyone else simply takes the latest claim."""
        parsed = dialogue.parse_position(message)
        if parsed is None:
            return self.belief
        if self.skeptical and (not self.trust_claims or self.belief is not None):
            return self.belief  # locked on a lead, or done trusting this liar
        self.belief = parsed
        self.belief_trusted = False
        return self.belief

    def perceive(self, self_pos: Position, opponent_true: Position, vision_radius: int) -> bool:
        """Acquire the rival's exact cell within sight; else expose a stale or *false* lead.

        Returns True if the rival is currently visible (ground truth acquired). A skeptical
        cop that reaches a *claimed* cell and finds nobody concludes it was deceived and
        stops trusting the rival's stated positions for the rest of the subgame.
        """
        if chebyshev(self_pos, opponent_true) <= vision_radius:
            self.belief = opponent_true
            self.belief_trusted = True
            self.last_seen = opponent_true
            return True
        if self.belief is not None and self_pos == self.belief:
            if self.skeptical and not self.belief_trusted:
                self.trust_claims = False  # arrived at a claimed cell, nobody here -> a lie
            self.belief = None  # reached the lead but the target is not here
        return False

    def decide(self, obs: Observation, board: Board) -> Move:
        """Choose a move aimed at the belief, or an active search target when blind."""
        return self.strategy.decide(obs, self._target(obs.self_pos, board), board)

    def _target(self, here: Position, board: Board) -> Position:
        """Resolve the cell to aim at: known belief, else role-specific blind behaviour.

        Blind cop -> hunt (last-seen then corner sweep). Blind thief -> flee from where
        the cop was last seen (or the centre if never seen), so it keeps distance from
        the approaching sweeper rather than idling in an easily-swept corner.
        """
        if self.belief is not None:
            return self.belief
        if self.role is Role.THIEF:
            return self.last_seen if self.last_seen is not None else _center(board)
        return self._hunt(here, board)

    def _hunt(self, here: Position, board: Board) -> Position:
        """Blind cop: head to the last-seen cell, then sweep the corners to flush the thief."""
        if self.last_seen is not None and here != self.last_seen:
            return self.last_seen
        self.last_seen = None
        corners = _corners(board)
        spot = corners[self._patrol % len(corners)]
        if here == spot:
            self._patrol += 1
            spot = corners[self._patrol % len(corners)]
        return spot

    def voice(self, obs: Observation, move: Move, disclosed: Position | None) -> str:
        """Produce the free-text message; ``disclosed`` is the cell to reveal (or None)."""
        return dialogue.announce(self.provider, obs, move, disclosed)


def _center(board: Board) -> Position:
    """Board centre — the thief's flee-from anchor when it cannot see the cop."""
    return Position(board.origin + board.width // 2, board.origin + board.height // 2)


def _corners(board: Board) -> list[Position]:
    """The four board corners — the cop's patrol circuit while hunting blind."""
    xs = (board.origin, board.origin + board.width - 1)
    ys = (board.origin, board.origin + board.height - 1)
    return [Position(x, y) for x in xs for y in ys]
