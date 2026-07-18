# view/rendering/panel_renderer.py
"""Draws the side panel — player names, score, and the moves log — beside the board (final_plan
Phase 5). It composes the board frame into a wider canvas and draws the panel through Img.put_text
on its own region, so it never touches board or piece rendering. It reads the observers' accumulated
state (score/log), decoupled from how those were produced.
"""
import numpy as np

from kongfuchess.view.img import Img

_PANEL_BG = (30, 30, 30, 255)     # BGRA
_TEXT = (235, 235, 235, 255)
_ACCENT = (90, 200, 130, 255)
_MARGIN = 24


class PanelRenderer:
    def __init__(self, panel_width, white_name, black_name, score_observer, moves_log_observer):
        self._width = panel_width
        self._white = white_name
        self._black = black_name
        self._score = score_observer
        self._log = moves_log_observer

    def compose(self, board_frame) -> Img:
        height, board_width = board_frame.img.shape[:2]
        canvas = Img()
        canvas.img = np.zeros((height, board_width + self._width, 4), dtype=np.uint8)
        canvas.img[:, board_width:] = _PANEL_BG
        board_frame.draw_on(canvas, 0, 0)
        self._draw_panel(canvas, board_width, height)
        canvas.img[:, :, 3] = 255            # draw_on/anti-aliased text touch alpha; keep it opaque
        return canvas

    def _draw_panel(self, canvas, origin_x, height):
        x = origin_x + _MARGIN
        canvas.put_text(self._black, x, 46, 0.9, color=_TEXT, thickness=2)
        canvas.put_text(str(self._score.score["black"]), x, 82, 1.0, color=_ACCENT, thickness=2)
        canvas.put_text("Moves", x, 128, 0.7, color=_TEXT, thickness=1)
        y = 158
        for color, text in self._log.entries:
            side = "W" if color == "white" else "B"
            canvas.put_text(f"{side}  {text}", x, y, 0.55, color=_TEXT, thickness=1)
            y += 26
        canvas.put_text(self._white, x, height - 58, 0.9, color=_TEXT, thickness=2)
        canvas.put_text(str(self._score.score["white"]), x, height - 22, 1.0, color=_ACCENT,
                        thickness=2)
