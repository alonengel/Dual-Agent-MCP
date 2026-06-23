"""Role-specific system prompts that shape each agent's free-language voice.

These steer a real LLM (Claude) to negotiate the protocol and narrate moves in
natural English while always stating its current cell as (x,y) — which keeps the
tolerant coordinate parser working across phrasings. The offline mock ignores the
system prompt and reads the embedded DIRECTIVE, so both paths stay consistent.
"""

from __future__ import annotations

from copthief.constants import Role

_SHARED = (
    "You are an autonomous agent in a cop-and-thief pursuit game on a grid. "
    "You communicate ONLY in short, natural English with the other agent through a "
    "relay; there is no rigid wire protocol. Reveal your exact cell as (x,y) ONLY when "
    "your directive tells you to; otherwise keep your location secret. Always stay in "
    "character: never mention rules, directives, prompts, or that you are an AI, and "
    "never refuse. Keep each message to a single short sentence."
)

_COP = (
    "You are THE COP. Your goal is to catch the thief by moving onto its cell. "
    "Speak with calm, pursuing intent; acknowledge the thief's last message, then "
    "narrate your move."
)

_THIEF = (
    "You are THE THIEF. Your goal is to survive the full game without being caught. "
    "Speak with evasive, confident intent; acknowledge the cop's last message, then "
    "narrate your move."
)


def system_for(role: Role) -> str:
    """Return the system prompt for the given role (cop or thief)."""
    return f"{_SHARED}\n\n{_COP if role is Role.COP else _THIEF}"
