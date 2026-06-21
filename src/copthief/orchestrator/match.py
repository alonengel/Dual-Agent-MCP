"""The match runner: the core end-to-end pipeline (six subgames, self-play).

Every turn is appended to the audit log so the full game is reconstructable for
dispute resolution — the requirement the lecture emphasised above all else.
"""

from __future__ import annotations

import random
from typing import Any

from copthief.constants import Outcome, Role
from copthief.domain.scoring import ScoreBook
from copthief.domain.subgame import Subgame
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.negotiation import opening_messages
from copthief.orchestrator.setup import build_subgame, observe
from copthief.shared.logger import AuditLog


class MatchRunner:
    """Runs a full game of N subgames between a cop agent and a thief agent."""

    def __init__(self, game_cfg: dict[str, Any], scoring: dict[str, int], cop: Agent,
                 thief: Agent, audit: AuditLog, rng: random.Random | None = None):
        self.game_cfg = game_cfg
        self.scorebook = ScoreBook(scoring)
        self.agents = {Role.COP: cop, Role.THIEF: thief}
        self.audit = audit
        self.rng = rng or random.Random()
        self.num_games = int(game_cfg.get("num_games", 6))

    def _negotiate(self) -> None:
        """Run the opening free-language protocol handshake, recorded to the audit log."""
        messages = opening_messages(self.agents[Role.COP], self.agents[Role.THIEF],
                                    self.game_cfg)
        for role, message in messages.items():
            self.audit.record("negotiation", role=role.value, message=message)

    def run_match(self) -> dict[str, Any]:
        """Play all subgames and return the aggregated, serializable result."""
        self._negotiate()
        results = []
        for index in range(1, self.num_games + 1):
            results.append(self._run_subgame(index))
        totals = self.scorebook.totals(results)
        self.audit.record("match_complete", totals=totals)
        return {"sub_games": [r.to_dict() for r in results], "totals": totals}

    def _run_subgame(self, index: int):
        """Play one subgame to its terminal outcome and return its score."""
        game = build_subgame(self.game_cfg, self.rng)
        self.audit.record("subgame_start", index=index,
                          cop=game.cop.as_tuple(), thief=game.thief.as_tuple())
        last_message = ""
        while not game.finished():
            last_message = self._play_turn(game, index, last_message)
        outcome = game.outcome or Outcome.TECHNICAL_LOSS
        result = self.scorebook.score_subgame(index, outcome, game.move_number)
        self.audit.record("subgame_end", **result.to_dict())
        return result

    def _play_turn(self, game: Subgame, index: int, last_message: str) -> str:
        """Execute one agent's turn: decide, announce, apply, log, relay."""
        role = game.turn
        agent = self.agents[role]
        opponent = self.agents[Role.THIEF if role is Role.COP else Role.COP]
        obs = observe(game, role, last_message)

        move = agent.decide(obs, game.board, fallback_opponent=opponent_position(game, role))
        result = game.apply(move)
        message = agent.voice(obs, move, result.new_pos)
        opponent.update_belief_from(message)

        self.audit.record(
            "turn", index=index, move=game.move_number, role=role.value,
            action=move.action.value, legal=result.legal, reason=result.reason,
            cop=game.cop.as_tuple(), thief=game.thief.as_tuple(), message=message,
        )
        return message


def opponent_position(game: Subgame, role: Role):
    """True position of the rival (used as the self-play belief fallback)."""
    return game.thief if role is Role.COP else game.cop
