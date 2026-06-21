"""Single source of truth for the code version (kept in sync with config files)."""

__version__ = "1.0.0"


def assert_config_version(config_version: str) -> None:
    """Validate at startup that config version matches the code version.

    We compare only major.minor so patch-level config edits do not block startup.
    """
    code_mm = ".".join(__version__.split(".")[:2])
    cfg_mm = ".".join(str(config_version).split(".")[:2])
    if code_mm != cfg_mm:
        raise ValueError(
            f"Config version {config_version} incompatible with code {__version__}"
        )
