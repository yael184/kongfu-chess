# view/rendering/panel_renderer.py
"""Draws the side panel — player names, score, and the moves log — beside the board (final_plan
Phase 5). It composes the board frame into a wider canvas and draws the panel through Img.put_text
on its own region, so it never touches board or piece rendering. It reads the observers' accumulated
state (score/log), decoupled from how those were produced.

Layout follows the spec: each player owns a column. Black sits at the top with its own move list
running downward; white sits at the bottom with its list running upward; the score gap between the
opponents is shown in the middle. Each logged move carries its server-time stamp.
"""
import numpy as np

from kongfuchess.view.img import Img

_PANEL_BG = (30, 30, 30, 255)     # BGRA
_TEXT = (235, 235, 235, 255)
_ACCENT = (90, 200, 130, 255)
_MUTED = (150, 150, 150, 255)
_MARGIN = 24
_MOVE_STEP = 24                   # vertical spacing between logged moves
_MOVES_SHOWN = 8                  # how many recent moves each side's column shows


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
        # Black's column at the top, its moves running downward from under the header.
        canvas.put_text(self._black, x, 46, 0.9, color=_TEXT, thickness=2)
        canvas.put_text(str(self._score.score["black"]), x, 82, 1.0, color=_ACCENT, thickness=2)
        self._draw_moves_down(canvas, x, 128, self._log.entries["black"])

        # The gap between the opponents, in the middle.
        self._draw_lead(canvas, x, height // 2)

        # White's column at the bottom, its moves running upward toward the name.
        canvas.put_text(self._white, x, height - 58, 0.9, color=_TEXT, thickness=2)
        canvas.put_text(str(self._score.score["white"]), x, height - 22, 1.0, color=_ACCENT,
                        thickness=2)
        self._draw_moves_up(canvas, x, height - 90, self._log.entries["white"])

    def _draw_moves_down(self, canvas, x, top_y, entries):
        canvas.put_text("Moves", x, top_y, 0.7, color=_TEXT, thickness=1)
        y = top_y + 30
        for at_ms, text in entries[-_MOVES_SHOWN:]:
            canvas.put_text(_move_line(at_ms, text), x, y, 0.5, color=_TEXT, thickness=1)
            y += _MOVE_STEP

    def _draw_moves_up(self, canvas, x, bottom_y, entries):
        y = bottom_y
        for at_ms, text in reversed(entries[-_MOVES_SHOWN:]):
            canvas.put_text(_move_line(at_ms, text), x, y, 0.5, color=_TEXT, thickness=1)
            y -= _MOVE_STEP

    def _draw_lead(self, canvas, x, y):
        canvas.put_text(_lead_text(self._score.lead), x, y, 0.6, color=_MUTED, thickness=1)


def _move_line(at_ms, text) -> str:
    """One logged move, stamped with its server-time in seconds, e.g. '12.3s  N b1xc3'."""
    return f"{at_ms / 1000:5.1f}s  {text}"


def _lead_text(lead) -> str:
    """The score gap, phrased from the leader's side (or level)."""
    if lead == 0:
        return "Even"
    return f"White +{lead}" if lead > 0 else f"Black +{-lead}"
