# view/sprite_repository.py
"""Loads piece sprites from disk and hands out ready-to-draw Animations.

This module owns one thing: the on-disk asset *layout* — that a piece folder holds
`states/<state>/sprites/<n>.png` alongside a `states/<state>/config.json` describing playback. That
is this layer's format knowledge, exactly as text_io owns the token format. Nothing here knows what
a piece *is* or how it moves; it is handed a resolved folder per (kind, color) by the composition
root and only reads files.
"""
import json

from kongfuchess.view.animation import Animation
from kongfuchess.view.img import Img

# The asset layout, in one place (a re-skin changes files, not this vocabulary).
_STATES_DIR = "states"
_SPRITES_DIR = "sprites"
_STATE_CONFIG = "config.json"
_SPRITE_GLOB = "*.png"
_GRAPHICS = "graphics"
_FPS = "frames_per_sec"
_IS_LOOP = "is_loop"


class SpriteRepository:
    """Turns (kind, color, state) into an Animation, loading and caching lazily.

    `piece_folders` maps a (PieceKind, Color) to that piece's base folder; the composition root
    builds it from the configured symbols, so this class never spells out a piece name or color.
    Sprites are scaled to `cell_size` on load. `image_loader` is injected for testing.
    """

    def __init__(self, piece_folders, cell_size, image_loader=Img):
        self._folders = piece_folders
        self._cell_size = cell_size
        self._image_loader = image_loader
        self._cache = {}

    def animation(self, kind, color, state_name) -> Animation:
        key = (kind, color, state_name)
        if key not in self._cache:
            self._cache[key] = self._load(self._folders[(kind, color)], state_name)
        return self._cache[key]

    def _load(self, base_folder, state_name) -> Animation:
        state_dir = base_folder / _STATES_DIR / state_name
        graphics = json.loads((state_dir / _STATE_CONFIG).read_text(encoding="utf-8")).get(_GRAPHICS, {})
        paths = sorted((state_dir / _SPRITES_DIR).glob(_SPRITE_GLOB), key=_frame_order)
        frames = tuple(self._image_loader().read(p, size=(self._cell_size, self._cell_size))
                       for p in paths)
        if not frames:
            raise FileNotFoundError(f"No sprites in {state_dir / _SPRITES_DIR}")
        return Animation(frames, graphics.get(_FPS, 0), graphics.get(_IS_LOOP, False))


def _frame_order(path):
    """Order sprite files numerically ('2.png' before '10.png'), falling back to name."""
    return int(path.stem) if path.stem.isdigit() else path.stem
