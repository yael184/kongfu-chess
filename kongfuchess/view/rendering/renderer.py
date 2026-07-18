# view/rendering/renderer.py
"""The window/input port (final_plan §7.7): a small interface the game loop depends on instead of
cv2 directly, so the loop is testable with an in-memory fake and the concrete OpenCV window
(cv2_renderer.py) is the only place that imports cv2 for display/input.
"""
from dataclasses import dataclass
from typing import Protocol

# Input event kinds a surface reports, already translated to board-canvas pixel coordinates.
CLICK = "click"     # select / move (left button)
JUMP = "jump"       # dodge (right button)
QUIT = "quit"       # the user asked to close the window


@dataclass(frozen=True)
class InputEvent:
    kind: str
    x: int = 0
    y: int = 0


class Renderer(Protocol):
    def draw_frame(self, frame) -> None:
        """Put an Img's pixels on screen."""

    def poll_events(self) -> list:
        """Return the InputEvents since the last poll (canvas coordinates), pumping the window."""
