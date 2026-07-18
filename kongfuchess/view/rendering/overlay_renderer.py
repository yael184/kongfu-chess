# view/rendering/overlay_renderer.py
"""Draws everything that is neither the board nor a piece (final_plan §7.2a): the selection
highlight and the game-over banner today; debug markers and side panels later. Keeping this a
separate collaborator is what stops BoardView from accumulating ad-hoc drawing.
"""
_SELECTION_COLOR = (0, 255, 0, 255)   # BGRA green
_SELECTION_THICKNESS = 4
_BANNER_TEXT = "GAME OVER"
_BANNER_SCALE = 3.0
_BANNER_COLOR = (0, 0, 255, 255)      # BGRA red
_BANNER_THICKNESS = 6


class OverlayRenderer:
    def __init__(self, cell_size):
        self._cell = cell_size

    def draw(self, frame, snapshot, selected):
        if selected is not None:
            frame.draw_rect(selected.col * self._cell, selected.row * self._cell,
                            self._cell - 1, self._cell - 1,
                            _SELECTION_COLOR, _SELECTION_THICKNESS)
        if snapshot.game_over:
            frame.put_text(_BANNER_TEXT, self._cell // 2, frame.img.shape[0] // 2,
                           _BANNER_SCALE, color=_BANNER_COLOR, thickness=_BANNER_THICKNESS)
