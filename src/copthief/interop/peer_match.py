"""In-process reference driver for the inter-group peer protocol.

Plays a full subgame between two of our own agents **without a shared referee**: each side
only perceives its own cell + a belief of the rival (from prose), publishes a commit-reveal
envelope each ply, and a capture is settled by claim + reveal + verify. This proves the
protocol composes end-to-end before game day; the networked driver swaps one side for a
remote `deliver_message` transport.
"""

from __future__ import annotations

import random

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.rules import validate
from copthief.interop import commitment, peer
from copthief.orchestrator import perception
from copthief.orchestrator.agent import Agent


class PeerMatch:
    """Drives a refereeless subgame via commit-reveal envelopes (reference implementation)."""

    def __init__(self, board: Board, cop: Agent, thief: Agent, max_moves: int,
                 max_barriers: int, radius: int):
        self.board = board
        self.agents = {Role.COP: cop, Role.THIEF: thief}
        self.max_moves = max_moves
        self.barriers_left = max_barriers
        self.radius = radius
        self.rng = random.Random(0)
        self.commit: dict[Role, str] = {}
        self.nonce: dict[Role, str] = {}

    def play(self, cop_pos: Position, thief_pos: Position) -> tuple[Outcome, int]:
        """Play one subgame; return the (outcome, rounds) both sides settle on."""
        pos = {Role.COP: cop_pos, Role.THIEF: thief_pos}
        for agent in self.agents.values():
            agent.reset()
        for rnd in range(self.max_moves):
            for role in (Role.THIEF, Role.COP):
                self._ply(role, pos, rnd)
                if self._capture_confirmed(pos):
                    return Outcome.COP_WIN, rnd + 1
        return Outcome.THIEF_WIN, self.max_moves

    def _ply(self, role: Role, pos: dict[Role, Position], rnd: int) -> None:
        """One side: perceive, decide, apply, publish a commitment, relay belief via prose."""
        agent = self.agents[role]
        opp = Role.THIEF if role is Role.COP else Role.COP
        agent.perceive(pos[role], pos[opp], self.radius)
        obs = Observation(role, pos[role], rnd, self.max_moves, self.barriers_left)
        move = agent.decide(obs, self.board)
        result = validate(move, pos[role], self.board, self.barriers_left)
        if result.legal and move.action is Action.MOVE:
            pos[role] = result.new_pos
        elif result.legal and move.action is Action.BLOCK:
            self.board.add_barrier(pos[role])
            self.barriers_left -= 1
        self.nonce[role] = commitment.new_nonce()
        self.commit[role] = commitment.commit(pos[role], self.board, self.nonce[role])
        disclosed = perception.disclosed_cell(pos[role], pos[opp], self.radius, False, False,
                                              self.board, self.rng)
        message = agent.voice(obs, move, disclosed)
        perception.relay(self.agents[opp], pos[role], pos[opp], self.radius, message)

    def _capture_confirmed(self, pos: dict[Role, Position]) -> bool:
        """Settle a capture only via commit-reveal: cop claims its cell, the thief reveals."""
        if pos[Role.COP] != pos[Role.THIEF] or Role.THIEF not in self.commit:
            return False
        reveal = {"cell": list(commitment.to_cell(pos[Role.THIEF], self.board)),
                  "nonce": self.nonce[Role.THIEF]}
        return peer.confirm_capture(self.commit[Role.THIEF], reveal, self.board, pos[Role.COP])
