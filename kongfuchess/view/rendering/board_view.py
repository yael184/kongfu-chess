# view/rendering/board_view.py
"""BoardView — a thin coordinator, not a god object (final_plan §7.2a).

It draws nothing itself: it holds three focused collaborators and calls them in order each frame —
BoardRenderer for the background, PieceRenderer for the pieces, OverlayRenderer for everything else.
A new kind of overlay is a change to OverlayRenderer only, never here.
"""


class BoardView:
    def __init__(self, board_renderer, piece_renderer, overlay_renderer, panel_renderer=None):
        self._board = board_renderer
        self._pieces = piece_renderer
        self._overlay = overlay_renderer
        self._panel = panel_renderer

    def render(self, snapshot, motions, selected, dt_ms):
        frame = self._board.fresh_frame(snapshot.width, snapshot.height)
        self._pieces.draw(frame, snapshot, motions, dt_ms)
        self._overlay.draw(frame, snapshot, selected)
        if self._panel is not None:
            return self._panel.compose(frame)   # widen the canvas with the side panel
        return frame
