"""An agent: a role-bound bundle of strategy, LLM voice and a belief about the rival.

The agent decides a move via its strategy, verbalises it through the LLM, and updates
its belief from vision and the opponent's free-text message. When a cop loses sight of
the thief it does not idle at the board centre — it **hunts**: it makes for the cell
where the thief was last seen and then sweeps the corners to flush it out.
"""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.llm.base import LLMProvider
from copthief.orchestrator import dialogue, patrol
from copthief.strategy.base import Strategy, chebyshev


class Agent:
    """Wraps one side's decision-making and natural-language communication."""

    def __init__(self, role: Role, strategy: Strategy, provider: LLMProvider,
                 llm_moves: bool = True):
        self.role = role
        self.strategy = strategy
        self.provider = provider
        # The LLM proposes moves by default (genuine agency for the graded self-game). The
        # competitive inter-group run sets this False: the strategy decides moves (stronger,
        # faster, never self-captures) while the LLM still voices every turn in free text.
        self.llm_moves = llm_moves
        self.skeptical = False  # a counter-intelligence cop that distrusts proven lies
        self.vision_radius = 1   # last radius seen in perceive(); drives the blind patrol
        self.belief: Position | None = None
        self.belief_trusted = False  # True only when the belief came from direct sight
        self.trust_claims = True     # cleared once a stated position is exposed as a lie
        self.last_seen: Position | None = None  # cop: last cell the thief was seen in
        self._patrol = 0                         # cop: index into the corner sweep
        self.last_source = "fallback"            # provenance of the last move: "llm" | "fallback"

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
        self.vision_radius = vision_radius  # remember it for the blind-search patrol
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
        """Choose a move. With ``llm_moves`` (default) the LLM proposes one from the legal
        neighbours (genuine agency) and the strategy is the legal fallback; with it off the
        strategy decides directly. ``last_source`` records the provenance ("llm"/"fallback"/
        "strategy") as audit evidence of how the move was chosen."""
        if self.llm_moves:
            chosen = dialogue.propose_move(self.provider, obs, board, self.belief)
            if chosen is not None:
                self.last_source = "llm"
                return Move(self.role, Action.MOVE,
                            chosen.x - obs.self_pos.x, chosen.y - obs.self_pos.y)
            self.last_source = "fallback"
        else:
            self.last_source = "strategy"
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
        """Blind cop: head to the last-seen cell, then sweep waypoints to flush the thief.

        The sweep visits coverage-optimal observation posts (no blind spot) on small boards
        and falls back to the corners on larger ones — see :mod:`copthief.orchestrator.patrol`.
        """
        if self.last_seen is not None and here != self.last_seen:
            return self.last_seen
        self.last_seen = None
        route = patrol.patrol_route(board, self.vision_radius)
        spot = route[self._patrol % len(route)]
        if here == spot:
            self._patrol += 1
            spot = route[self._patrol % len(route)]
        return spot

    def voice(self, obs: Observation, move: Move, disclosed: Position | None) -> str:
        """Produce the free-text message; ``disclosed`` is the cell to reveal (or None)."""
        return dialogue.announce(self.provider, obs, move, disclosed)


def _center(board: Board) -> Position:
    """Board centre — the thief's flee-from anchor when it cannot see the cop."""
    return Position(board.origin + board.width // 2, board.origin + board.height // 2)
