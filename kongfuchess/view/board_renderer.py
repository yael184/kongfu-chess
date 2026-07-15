# view/board_renderer.py
"""Draws one frame of the game onto a canvas Img, from read-only state.

The renderer is pure: given a board snapshot, the motions in flight, the airborne cells, the current
selection and the clock, it returns a fresh Img. It holds no game logic and never advances time — it
only reads. A moving piece is drawn *gliding* (interpolated between its source and destination cell)
rather than at the logical source cell the snapshot reports, which is what makes the real-time board
feel real. It reads the board via pieces()/snapshot ports only, so a binary board would reach it
unchanged.
"""
import cv2

from kongfuchess.model.piece import PieceState
from kongfuchess.view.img import Img

_SELECTION_COLOR = (0, 255, 0, 255)   # BGRA green
_SELECTION_THICKNESS = 4
_BANNER_TEXT = "GAME OVER"
_BANNER_SCALE = 3.0
_BANNER_COLOR = (0, 0, 255, 255)      # BGRA red
_BANNER_THICKNESS = 6


class BoardRenderer:
    """Renders the game onto a board-sized canvas at a fixed cell size.

    `state_names` is the (idle, move, jump) folder trio, injected from config so the renderer names
    no folder itself. `image_loader` is injected for testing.
    """

    def __init__(self, board_image, cell_size, sprite_repo,
                 idle_state, move_state, jump_state, image_loader=Img):
        self._cell = cell_size
        self._sprites = sprite_repo
        self._idle_state = idle_state
        self._move_state = move_state
        self._jump_state = jump_state
        self._background = image_loader().read(board_image)   # raw, scaled per board size on demand
        self._scaled_bg = {}                                  # (w, h) in cells -> scaled np array

    def render(self, snapshot, motions, airborne_cells, selected, now_ms) -> Img:
        canvas = self._canvas(snapshot.width, snapshot.height)

        moving_sources = {motion.source for motion in motions}
        for piece in snapshot.pieces():
            if piece.cell in moving_sources or piece.state is PieceState.CAPTURED:
                continue                                       # gliding (drawn below) or gone
            state = self._jump_state if piece.cell in airborne_cells else self._idle_state
            self._draw(canvas, piece.kind, piece.color, state, now_ms,
                       piece.cell.col, piece.cell.row)

        if selected is not None:
            self._highlight(canvas, selected)

        for motion in motions:
            col = _lerp(motion.source.col, motion.destination.col, motion.progress)
            row = _lerp(motion.source.row, motion.destination.row, motion.progress)
            self._draw(canvas, motion.piece.kind, motion.piece.color, self._move_state, now_ms,
                       col, row)

        if snapshot.game_over:
            self._banner(canvas)
        return canvas

    def _canvas(self, width_cells, height_cells) -> Img:
        key = (width_cells, height_cells)
        if key not in self._scaled_bg:
            target = (width_cells * self._cell, height_cells * self._cell)
            self._scaled_bg[key] = cv2.resize(self._background.img, target,
                                              interpolation=cv2.INTER_AREA)
        canvas = Img()
        canvas.img = self._scaled_bg[key].copy()
        return canvas

    def _draw(self, canvas, kind, color, state_name, now_ms, col, row):
        sprite = self._sprites.animation(kind, color, state_name).frame_at(now_ms)
        sprite.draw_on(canvas, int(col * self._cell), int(row * self._cell))

    def _highlight(self, canvas, cell):
        x, y = cell.col * self._cell, cell.row * self._cell
        cv2.rectangle(canvas.img, (x, y), (x + self._cell - 1, y + self._cell - 1),
                      _SELECTION_COLOR, _SELECTION_THICKNESS)

    def _banner(self, canvas):
        canvas.put_text(_BANNER_TEXT, self._cell // 2, canvas.img.shape[0] // 2,
                        _BANNER_SCALE, color=_BANNER_COLOR, thickness=_BANNER_THICKNESS)


def _lerp(start, end, t):
    return start + (end - start) * t
