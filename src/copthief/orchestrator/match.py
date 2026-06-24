"""The match runner: the core end-to-end pipeline (six subgames, self-play).

Every turn is appended to the audit log so the full game is reconstructable for
dispute resolution — the requirement the lecture emphasised above all else.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from copthief.constants import Outcome, Role
from copthief.domain.scoring import ScoreBook
from copthief.domain.subgame import Subgame
from copthief.orchestrator import negotiation, perception
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.setup import build_subgame, observe
from copthief.shared.logger import AuditLog


class MatchRunner:
    """Runs a full game of N subgames between a cop agent and a thief agent."""

    def __init__(self, game_cfg: dict[str, Any], scoring: dict[str, int], cop: Agent,
                 thief: Agent, audit: AuditLog, rng: random.Random | None = None,
                 reporter: Callable[[str], None] | None = None,
                 board_render: Callable[[Subgame], str] | None = None):
        self.game_cfg = game_cfg
        self.scorebook = ScoreBook(scoring)
        self.agents = {Role.COP: cop, Role.THIEF: thief}
        self.audit = audit
        self.rng = rng or random.Random()
        self.reporter = reporter
        self.board_render = board_render
        self.num_games = int(game_cfg.get("num_games", 6))
        self.radius, self.radius_mode = negotiation.negotiated_radius(game_cfg)
        self.exact = str(game_cfg.get("disclosure", "exact")).lower() == "exact"
        self.deception = bool(game_cfg.get("deception", False))
        cop.skeptical = self.deception  # only the cop runs counter-intelligence on lies

    def _say(self, text: str) -> None:
        """Echo human-readable progress to an optional reporter (used by the demo)."""
        if self.reporter is not None:
            self.reporter(text)

    def _negotiate(self) -> None:
        """Run the opening free-language protocol handshake, recorded to the audit log."""
        messages = negotiation.opening_messages(self.agents[Role.COP],
                                                self.agents[Role.THIEF], self.game_cfg)
        for role, message in messages.items():
            self.audit.record("negotiation", role=role.value, message=message)
            self._say(f"[negotiate] {role.value}: {message}")
        self.audit.record("vision_negotiation", radius=self.radius, outcome=self.radius_mode)

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
        for agent in self.agents.values():
            agent.reset()  # clear beliefs/trust/patrol so subgames are independent
        self.audit.record("subgame_start", index=index,
                          cop=game.cop.as_tuple(), thief=game.thief.as_tuple())
        self._say(f"\n== Subgame {index} | cop {game.cop.as_tuple()} vs "
                  f"thief {game.thief.as_tuple()}")
        last_message = ""
        while not game.finished():
            last_message = self._play_turn(game, index, last_message)
        outcome = game.outcome or Outcome.TECHNICAL_LOSS
        result = self.scorebook.score_subgame(index, outcome, game.move_number)
        self.audit.record("subgame_end", **result.to_dict())
        d = result.to_dict()
        self._say(f"   -> {d['outcome']} (cop {d['cop_score']}, thief {d['thief_score']})")
        return result

    def _play_turn(self, game: Subgame, index: int, last_message: str) -> str:
        """Execute one agent's turn under partial observation: perceive, decide, disclose."""
        role = game.turn
        agent = self.agents[role]
        opponent = self.agents[Role.THIEF if role is Role.COP else Role.COP]
        opp_true = opponent_position(game, role)

        visible = agent.perceive(game.position_of(role), opp_true, self.radius)
        obs = observe(game, role, last_message)
        move = agent.decide(obs, game.board)
        result = game.apply(move)

        deceiving = self.deception and role is Role.THIEF  # only the thief lures; cop is honest
        disclosed = perception.disclosed_cell(result.new_pos, opp_true, self.radius,
                                              self.exact, deceiving, game.board, self.rng)
        message = agent.voice(obs, move, disclosed)
        perception.relay(opponent, result.new_pos, opp_true, self.radius, message)

        self.audit.record(
            "turn", index=index, move=game.move_number, role=role.value,
            action=move.action.value, legal=result.legal, reason=result.reason,
            source=agent.last_source, visible=visible, revealed=disclosed is not None,
            cop=game.cop.as_tuple(), thief=game.thief.as_tuple(), message=message,
        )
        self._say(f"  {role.value} m{game.move_number}: {message}")
        if self.board_render is not None:
            self._say(self.board_render(game))
        return message


def opponent_position(game: Subgame, role: Role):
    """True position of the rival (used as the self-play belief fallback)."""
    return game.thief if role is Role.COP else game.cop
