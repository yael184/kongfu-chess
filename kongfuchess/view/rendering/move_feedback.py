# view/rendering/move_feedback.py
"""The short-lived 'that move was refused' flash — a pure view affordance, no chess, no engine.

When the engine rejects a move (illegal, the piece is busy, the game is over), the player deserves
to see that the click did something rather than vanishing silently. This holds which cell to flash
and how much of the flash is left, ageing itself by the frame's dt so it fades and clears on its
own. It is the visual sibling of the arbiter's rest windows: state that only a renderer cares about,
kept out of the engine. GameLoop feeds it rejections and ages it; OverlayRenderer draws `flash`.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RejectionFlash:
    """One frame's worth of the refused-move flash: which cell, and how solid (1.0 -> 0.0)."""
    cell: object
    intensity: float


class MoveFeedback:
    """Tracks the fading flash of the last refused move. `duration_ms == 0` disables it entirely."""

    def __init__(self, duration_ms):
        self._duration = duration_ms
        self._cell = None
        self._remaining = 0

    def reject(self, cell):
        """A move aimed at `cell` was refused: start (or restart) the flash there."""
        if self._duration <= 0 or cell is None:
            return
        self._cell = cell
        self._remaining = self._duration

    def age(self, dt_ms):
        """Advance the flash by a frame; it clears itself once it has fully faded."""
        if self._cell is None:
            return
        self._remaining -= dt_ms
        if self._remaining <= 0:
            self._cell = None
            self._remaining = 0

    @property
    def flash(self):
        """The current flash for the overlay to draw, or None when nothing is fading."""
        if self._cell is None:
            return None
        return RejectionFlash(self._cell, self._remaining / self._duration)
