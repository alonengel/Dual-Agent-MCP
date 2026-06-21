"""SDK layer: the single entry point through which all consumers (CLI, GUI,
tests, future integrations) access the application's business logic.
"""

from copthief.sdk.sdk import CopThiefSDK

__all__ = ["CopThiefSDK"]
