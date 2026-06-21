"""Immutable project constants. Tunable game parameters live in config, not here."""

from enum import Enum

PACKAGE_ROOT_ENV = "COPTHIEF_ROOT"
DEFAULT_CONFIG_PATH = "config/config.yaml"
RATE_LIMITS_PATH = "config/rate_limits.json"
LOGGING_CONFIG_PATH = "config/logging_config.json"


class Role(str, Enum):
    """Which side an agent plays."""

    COP = "cop"
    THIEF = "thief"


class Action(str, Enum):
    """Atomic action kinds an agent may take on its turn."""

    MOVE = "move"
    BLOCK = "block"  # cop-only: place a barrier on the current cell
    STAY = "stay"


class Outcome(str, Enum):
    """Terminal result of a single subgame."""

    COP_WIN = "cop_win"
    THIEF_WIN = "thief_win"
    TECHNICAL_LOSS = "technical_loss"


# The 8 movement directions as (dx, dy). Cardinal first, then diagonals.
DIRECTIONS_8: tuple[tuple[int, int], ...] = (
    (0, 1), (0, -1), (1, 0), (-1, 0),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
)
DIRECTIONS_4: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))
