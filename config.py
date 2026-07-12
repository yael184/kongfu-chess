# config.py
# Access layer for the game configuration. The values themselves live in an external,
# non-code file (config.toml) so they can be changed without editing code. The rest of the
# codebase keeps using config.CELL_SIZE, config.MS_PER_CELL, etc. exactly as before.
import tomllib
from pathlib import Path

# The external config file, resolved relative to this module so it works regardless of the
# current working directory.
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")


def load(path=None):
    """Read the TOML config file and (re)populate this module's constants.

    Called once on import. Call again to reload after the file has been edited at runtime;
    because every other module reads the values as config.<NAME>, the new values take effect
    immediately everywhere.
    """
    path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(path, "rb") as f:
        data = tomllib.load(f)

    global CELL_SIZE, MS_PER_CELL, JUMP_DURATION_MS, EMPTY_TOKEN

    CELL_SIZE = data["board"]["cell_size"]
    MS_PER_CELL = data["timing"]["ms_per_cell"]
    JUMP_DURATION_MS = data["timing"]["jump_duration_ms"]
    EMPTY_TOKEN = data["tokens"]["empty"]


# Load on import so config.CELL_SIZE and friends are available immediately.
load()
