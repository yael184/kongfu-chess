# config.py
# Access layer for the game configuration. The values themselves live in an external, non-code
# file (config.toml) so they can be changed without editing code.
#
# load() returns an immutable GameConfig rather than populating module globals: a configuration is
# a value that gets *injected* into the objects that need it (by composition/app_factory), not an
# ambient global that any layer can reach into. That is what lets a test — or a second game running
# in the same process — use different settings without disturbing anyone else.
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The external config file, resolved relative to this module so it works regardless of the
# current working directory.
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")


@dataclass(frozen=True)
class PieceSpec:
    """One piece as configuration: what it is called, how it is spelled, how it moves.

    This is plain data — it names a movement *pattern* rather than describing one, and knows
    nothing about the rule classes that read it (rules/rule_factory.py turns a spec into a rule).
    Adding a piece is adding one of these.
    """
    name: str
    symbol: str
    movement: str
    directions: tuple = ()
    offsets: tuple = ()
    promotes_to: str = None
    victory_on_capture: bool = False
    flies_over: bool = False


@dataclass(frozen=True)
class AssetsConfig:
    """Where the OpenCV view finds its art, and the folder vocabulary it renders with.

    Paths are absolute (resolved against the package), so the view loads them regardless of the
    current working directory. Re-skinning is entirely here: no literal path or folder name lives
    in view/.
    """
    board_image: Path
    pieces_dir: Path
    default_board: Path
    white_suffix: str
    black_suffix: str
    idle_state: str
    move_state: str
    jump_state: str
    short_rest_state: str
    long_rest_state: str


@dataclass(frozen=True)
class GameConfig:
    """The game's tunables, loaded from config.toml.

    Add a new tunable here and in config.toml — never as a literal in business logic.
    """
    cell_size: int
    ms_per_cell: int
    jump_duration_ms: int
    long_rest_ms: int
    short_rest_ms: int
    empty_token: str
    pieces: tuple = ()
    assets: AssetsConfig = None


def load(path=None) -> GameConfig:
    """Read the TOML config file and return the GameConfig it describes."""
    path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(path, "rb") as f:
        data = tomllib.load(f)

    return GameConfig(
        cell_size=data["board"]["cell_size"],
        ms_per_cell=data["timing"]["ms_per_cell"],
        jump_duration_ms=data["timing"]["jump_duration_ms"],
        long_rest_ms=data["timing"].get("long_rest_ms", 2000),
        short_rest_ms=data["timing"].get("short_rest_ms", 500),
        empty_token=data["tokens"]["empty"],
        pieces=tuple(_piece_spec(entry) for entry in data.get("pieces", [])),
        assets=_assets_config(data.get("assets"), path.parent),
    )


def _assets_config(entry, base_dir) -> "AssetsConfig":
    """Resolve the view's asset paths relative to the config file's directory (the package root)."""
    if entry is None:
        return None
    return AssetsConfig(
        board_image=base_dir / entry["board_image"],
        pieces_dir=base_dir / entry["pieces_dir"],
        default_board=base_dir / entry["default_board"],
        white_suffix=entry["white_suffix"],
        black_suffix=entry["black_suffix"],
        idle_state=entry["idle_state"],
        move_state=entry["move_state"],
        jump_state=entry["jump_state"],
        short_rest_state=entry["short_rest_state"],
        long_rest_state=entry["long_rest_state"],
    )


def _piece_spec(entry) -> PieceSpec:
    return PieceSpec(
        name=entry["name"],
        symbol=entry["symbol"],
        movement=entry["movement"],
        directions=tuple(tuple(step) for step in entry.get("directions", [])),
        offsets=tuple(tuple(step) for step in entry.get("offsets", [])),
        promotes_to=entry.get("promotes_to"),
        victory_on_capture=entry.get("victory_on_capture", False),
        flies_over=entry.get("flies_over", False),
    )
