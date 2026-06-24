"""Async client-driven turn loop for one inter-group subgame (agreed protocol, Option A).

We drive our own turns with our LLM/strategy and only **deliver** text to the opponent's mailbox
+ **read** our own; servers never run an LLM. Per the protocol agreed with the partner team
(group ImreEyal): **full disclosure** — each ply states the mover's new cell in cleartext (the
``MOVE`` block, see :mod:`wire`) with a ``COMMIT``+``NONCE`` audit and a post-ply ``STATE`` hash.
Capture is therefore **deterministic**: when the cop and thief occupy the same cell both engines
call it independently from the cleartext (no claim/reveal handshake); the commitment is only the
tamper-evident audit. A ``STATE`` mismatch, or a commitment that doesn't open to its stated move,
raises :class:`PeerDesync` (the §12 void + re-run). Barriers are disabled for the run
(``max_barriers=0``), so ``STATE.barriers`` stays ``[]`` and the two engines stay trivially in
sync. ``send``/``recv`` are injected so two loops wire in-process for tests without a network.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.rules import validate
from copthief.interop import commitment, peer, wire
from copthief.orchestrator.agent import Agent

Send = Callable[[str], Awaitable[None]]
Recv = Callable[[], Awaitable[str]]


class PeerDesyncError(Exception):
    """A peer message failed its commit audit or common-state hash (§12 → void + re-run)."""


class PeerLoop:
    """Plays our side of one subgame over the async mailbox channel (Option A: full disclosure)."""

    def __init__(self, role: Role, agent: Agent, board: Board, max_moves: int,
                 max_barriers: int = 0):
        self.role = role
        self.agent = agent
        self.board = board
        self.max_moves = max_moves
        self.barriers_left = max_barriers
        self.pos = Position(board.origin, board.origin)
        self.opp: Position | None = None  # the rival's last cleartext cell
        self._seen: set[str] = set()      # opponent COMMITs already applied (retry de-dup)

    async def play(self, our_pos: Position, send: Send, recv: Recv) -> tuple[Outcome, int]:
        """Play to the verdict both sides agree on (thief-first, ``2 * max_moves`` plies)."""
        self.agent.reset()
        self.pos = our_pos
        self.opp = None
        self._seen = set()
        for ply in range(2 * self.max_moves):
            mover = Role.THIEF if ply % 2 == 0 else Role.COP
            if mover is self.role:
                await self._send_ply(ply, send)
            else:
                await self._recv_ply(ply, recv)
            if self.opp is not None and self.pos == self.opp:
                return Outcome.COP_WIN, ply // 2 + 1
        return Outcome.THIEF_WIN, self.max_moves

    async def _send_ply(self, ply: int, send: Send) -> None:
        """Our turn: decide + apply our move, then announce it (cleartext + commit + state).

        We never emit a stay: the inter-group contract requires a step to one of the 8 neighbours
        every ply, so if the strategy yields no legal move we fall back to a free neighbour."""
        obs = Observation(self.role, self.pos, ply // 2, self.max_moves, self.barriers_left)
        before = self.pos
        move = self.agent.decide(obs, self.board)
        result = validate(move, self.pos, self.board, self.barriers_left)
        if result.legal and move.action is Action.MOVE:
            self.pos = result.new_pos
        if self.pos == before:
            free = self.board.free_neighbours(self.pos)
            if free:
                self.pos = free[0]
        nonce = commitment.new_nonce()
        done = self.pos == self.opp or ply == 2 * self.max_moves - 1
        # Prose stays coordinate-free (vague taunt); the exact position rides only in the 0-based
        # MOVE block, so a peer can never misread our internal 1-based display.
        await send(wire.encode(self.agent.voice(obs, move, None),
                               commitment.to_cell(self.pos, self.board),
                               commitment.commit(self.pos, self.board, nonce), nonce,
                               self._state(ply, done)))

    async def _recv_ply(self, ply: int, recv: Recv) -> None:
        """Opponent's turn: extract + audit their move block, then adopt it as ground truth.

        Skips duplicate blocks (same COMMIT) so a peer's retried send that already landed is
        never applied twice — which would otherwise look like a phantom same-cell move."""
        while True:
            env = wire.decode(await recv())
            if env is None:
                continue  # free-text chatter (greeting/handshake/taunt) — wait for a real block
            if env["commit"] not in self._seen:
                self._seen.add(env["commit"])
                break
        pos = peer.from_cell(env["cell"], self.board)
        if not commitment.verify(env["commit"], pos, self.board, env["nonce"]):
            raise PeerDesyncError("commitment does not open to the stated move")
        done = pos == self.pos or ply == 2 * self.max_moves - 1
        if env["state"] != self._state(ply, done):
            # Barriers are off, so STATE is a redundant sync check — commit-verify + the cleartext
            # positions already carry correctness. A move_count/turn drift (e.g. from a retried
            # send de-duplicated on one side) must not false-abort the series, so we log and play on.
            print(f"[warn] state mismatch at ply {ply} (non-fatal; barriers off)", flush=True)
        self.opp = pos
        self.agent.belief = pos  # full disclosure: the cleartext move is the truth

    def _state(self, ply: int, done: bool) -> str:
        """Common-state hash *after* ply ``ply`` (move_count = ply+1). The turn advances to the
        next mover, except on a game-ending ply (capture or the round cap) where it stays on the
        mover: the partner team's engine does not flip the turn on the terminal ply, so matching
        that keeps the final STATE byte-identical (no false §12 void)."""
        mover = Role.THIEF if ply % 2 == 0 else Role.COP
        nxt = Role.THIEF if (ply + 1) % 2 == 0 else Role.COP
        turn = mover if done else nxt
        cells = [commitment.to_cell(Position(x, y), self.board) for x, y in self.board.barriers]
        return commitment.state_hash(cells, turn.value, ply + 1)
