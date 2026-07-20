# view/rendering/overlay_renderer.py
"""Draws everything that is neither the board nor a piece (final_plan §7.2a): the selection
highlight, the legal-move targets, the cooldown countdown and the game-over banner. Keeping this a
separate collaborator is what stops BoardView from accumulating ad-hoc drawing.

It decides nothing it draws. Which cells are legal targets is the rules' answer, and how much of a
cooldown is left is the arbiter's — both arrive already computed on the ViewState.
"""
_SELECTION_COLOR = (0, 255, 0, 255)   # BGRA green
_SELECTION_THICKNESS = 4
_TARGET_COLOR = (0, 255, 0, 255)      # BGRA green, matching the selection it belongs to
_TARGET_OPACITY = 0.30
_REST_COLOR = (0, 235, 255, 255)      # BGRA yellow
_REST_OPACITY = 0.45
_BANNER_TEXT = "GAME OVER"
_BANNER_SCALE = 3.0
_BANNER_COLOR = (0, 0, 255, 255)      # BGRA red
_BANNER_THICKNESS = 6


class OverlayRenderer:
    def __init__(self, cell_size):
        self._cell = cell_size

    def draw(self, frame, state):
        for rest in state.rests:
            self._draw_cooldown(frame, rest)
        for target in state.targets:
            self._draw_target(frame, target)
        if state.selected is not None:
            self._draw_selection(frame, state.selected)
        if state.snapshot.game_over:
            frame.put_text(_BANNER_TEXT, self._cell // 2, frame.img.shape[0] // 2,
                           _BANNER_SCALE, color=_BANNER_COLOR, thickness=_BANNER_THICKNESS)

    def _draw_cooldown(self, frame, rest):
        """Shade the resting cell as a draining hourglass: full when the wait begins, emptying from
        the top down, so the yellow that is left is the time that is left."""
        height = int(self._cell * rest.remaining)
        if height <= 0:
            return
        frame.fill_rect(rest.cell.col * self._cell,
                        rest.cell.row * self._cell + (self._cell - height),
                        self._cell, height, _REST_COLOR, _REST_OPACITY)

    def _draw_target(self, frame, cell):
        frame.fill_rect(cell.col * self._cell, cell.row * self._cell,
                        self._cell, self._cell, _TARGET_COLOR, _TARGET_OPACITY)

    def _draw_selection(self, frame, cell):
        frame.draw_rect(cell.col * self._cell, cell.row * self._cell,
                        self._cell - 1, self._cell - 1,
                        _SELECTION_COLOR, _SELECTION_THICKNESS)
