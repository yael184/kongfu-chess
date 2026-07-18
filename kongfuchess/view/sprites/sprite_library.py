# view/sprites/sprite_library.py
"""The Strategy for asset loading (final_plan §7.4): the one place that knows the on-disk sprite
layout, so nothing else in the view touches a Path.

Adapted to our layout: a piece's base folder (resolved per (kind, color) at the composition root)
holds `states/<state>/sprites/<n>.png` alongside `states/<state>/config.json`. Frames and parsed
config are cached; each `state_for` call returns a *fresh* SpriteState so every piece animates on its
own clock (a cached, shared SpriteState would stomp its playback across pieces).
"""
import json

from kongfuchess.view.sprites.sprite_state import SpriteState, StateConfig

# The asset layout, named once.
_STATES_DIR = "states"
_SPRITES_DIR = "sprites"
_STATE_CONFIG = "config.json"
_SPRITE_GLOB = "*.png"


class SpriteLibrary:
    """Turns (kind, color, state-folder) into a ready SpriteState, loading and caching lazily.

    `piece_folders` maps a (PieceKind, Color) to that piece's base folder — built from the configured
    symbols at the composition root, so this class never spells a piece name or colour. `image_loader`
    is injected for testing; sprites are scaled to `cell_size` on load.
    """

    def __init__(self, piece_folders, cell_size, image_loader):
        self._folders = piece_folders
        self._cell_size = cell_size
        self._image_loader = image_loader
        self._cache = {}                     # (kind, color, state) -> (StateConfig, tuple[Img])

    def state_for(self, kind, color, state_name) -> SpriteState:
        config, frames = self._loaded(kind, color, state_name)
        return SpriteState(config, frames)

    def _loaded(self, kind, color, state_name):
        key = (kind, color, state_name)
        if key not in self._cache:
            self._cache[key] = self._load(self._folders[(kind, color)], state_name)
        return self._cache[key]

    def _load(self, base_folder, state_name):
        state_dir = base_folder / _STATES_DIR / state_name
        data = json.loads((state_dir / _STATE_CONFIG).read_text(encoding="utf-8"))
        config = StateConfig.from_asset(state_name, data)
        paths = sorted((state_dir / _SPRITES_DIR).glob(_SPRITE_GLOB), key=_frame_order)
        size = (self._cell_size, self._cell_size)
        frames = tuple(self._image_loader().read(p, size=size) for p in paths)
        if not frames:
            raise FileNotFoundError(f"No sprites in {state_dir / _SPRITES_DIR}")
        return config, frames


def _frame_order(path):
    """Order sprite files numerically ('2.png' before '10.png'), falling back to name."""
    return int(path.stem) if path.stem.isdigit() else path.stem
