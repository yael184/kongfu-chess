# view/rendering/piece_renderer.py
"""Composites piece sprites onto the frame — and nothing else (final_plan §7.2a).

Each piece keeps its own AnimatedSprite across frames (keyed by the stable piece id *and* its current
kind) so its animation clock persists — and so a promotion, which changes the kind of the very same
piece, swaps it to the sprites of what it became. The engine's `PieceState` is mapped to a sprite-state folder (injected, config-driven)
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
        self._sprites = {}                            # (piece id, kind) -> AnimatedSprite

    def draw(self, frame, snapshot, motions, dt_ms):
        gliding = {motion.piece.id: motion for motion in motions}
        seen = set()
        for piece in snapshot.pieces():
            if piece.state is PieceState.CAPTURED:
                continue
            key = self._key(piece)
            seen.add(key)
            state_name = self._state_folders[piece.state]
            sprite = self._sprite_for(piece, key, state_name)
            sprite.update(dt_ms, state_name)
            col, row = self._position(piece, gliding.get(piece.id))
            sprite.current_frame.draw_on(frame, int(col * self._cell), int(row * self._cell))
        self._sprites = {key: s for key, s in self._sprites.items() if key in seen}

    def _position(self, piece, motion):
        if motion is None:
            return piece.cell.col, piece.cell.row
        col = motion.source.col + (motion.destination.col - motion.source.col) * motion.progress
        row = motion.source.row + (motion.destination.row - motion.source.row) * motion.progress
        return col, row

    def _key(self, piece):
        """A sprite belongs to a piece *as it currently is*, not just to its identity.

        A promotion changes `kind` on the same piece object — same id — so keying on the id alone
        would keep serving the pawn's frames after it became a queen. Including the kind retires the
        old sprite (the prune below drops it) and builds one for what the piece is now.
        """
        return piece.id, piece.kind

    def _sprite_for(self, piece, key, state_name):
        if key not in self._sprites:
            self._sprites[key] = AnimatedSprite(self._library, piece.kind, piece.color, state_name)
        return self._sprites[key]
