# view/rendering/piece_renderer.py
"""Composites piece sprites onto the frame — and nothing else (final_plan §7.2a).

Each piece keeps its own AnimatedSprite across frames (keyed by the stable piece id) so its animation
clock persists. The engine's `PieceState` is mapped to a sprite-state folder (injected, config-driven)
and fed to the sprite as the authoritative state each frame. A piece in flight is drawn *gliding*
between cells via its MotionView progress; every other piece sits on its logical cell; a captured
piece is not drawn.
"""
from kongfuchess.model.piece import PieceState
from kongfuchess.view.sprites.sprite_state import AnimatedSprite


class PieceRenderer:
    def __init__(self, sprite_library, cell_size, state_folders):
        self._library = sprite_library
        self._cell = cell_size
        self._state_folders = state_folders          # PieceState -> asset folder name
        self._sprites = {}                            # piece id -> AnimatedSprite

    def draw(self, frame, snapshot, motions, dt_ms):
        gliding = {motion.piece.id: motion for motion in motions}
        seen = set()
        for piece in snapshot.pieces():
            if piece.state is PieceState.CAPTURED:
                continue
            seen.add(piece.id)
            state_name = self._state_folders[piece.state]
            sprite = self._sprite_for(piece, state_name)
            sprite.update(dt_ms, state_name)
            col, row = self._position(piece, gliding.get(piece.id))
            sprite.current_frame.draw_on(frame, int(col * self._cell), int(row * self._cell))
        self._sprites = {pid: s for pid, s in self._sprites.items() if pid in seen}

    def _position(self, piece, motion):
        if motion is None:
            return piece.cell.col, piece.cell.row
        col = motion.source.col + (motion.destination.col - motion.source.col) * motion.progress
        row = motion.source.row + (motion.destination.row - motion.source.row) * motion.progress
        return col, row

    def _sprite_for(self, piece, state_name):
        if piece.id not in self._sprites:
            self._sprites[piece.id] = AnimatedSprite(self._library, piece.kind, piece.color,
                                                     state_name)
        return self._sprites[piece.id]
