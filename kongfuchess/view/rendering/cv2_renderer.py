# view/rendering/cv2_renderer.py
"""The one concrete Renderer: a resizable OpenCV window and its mouse input.

This is the only module that drives cv2's display/input (`imshow`/`waitKey`/`setMouseCallback`) — the
same plumbing `Img.show()` uses internally, driven per-frame instead of blocking (final_plan §3).
The window is resizable (`WINDOW_NORMAL | WINDOW_KEEPRATIO`); clicks arrive in the *displayed* window
and are scaled back to board-canvas pixels via `getWindowImageRect`, so a move lands on the right
square at any zoom. If a cv2 backend reports coordinates differently, switch to a fixed-size window
(`WINDOW_AUTOSIZE`) — then `scale_point` is a 1:1 pass-through (final_plan §3 #6 / Phase 3).
"""
import cv2

from kongfuchess.view.rendering.renderer import CLICK, JUMP, QUIT, InputEvent

_ESC_KEY = 27
_FRAME_DELAY_MS = 15   # ~66 fps ceiling; also pumps the window's event queue


def scale_point(x, y, displayed_w, displayed_h, canvas_w, canvas_h):
    """Translate a click in the displayed (possibly resized) window to board-canvas pixels.

    Pure and side-effect free so the coordinate math is unit-tested without a window. A degenerate
    displayed size falls back to a 1:1 mapping.
    """
    if displayed_w <= 0 or displayed_h <= 0:
        return x, y
    return int(x * canvas_w / displayed_w), int(y * canvas_h / displayed_h)


class Cv2Renderer:
    def __init__(self, window_title, frame_delay_ms=_FRAME_DELAY_MS):
        self._title = window_title
        self._frame_delay_ms = frame_delay_ms
        self._created = False
        self._canvas_size = (0, 0)   # (w, h) of the last drawn frame, in canvas pixels
        self._pending = []           # InputEvents captured by the mouse callback (already scaled)

    def draw_frame(self, frame):
        self._ensure_window()
        height, width = frame.img.shape[:2]
        self._canvas_size = (width, height)
        cv2.imshow(self._title, frame.img)

    def poll_events(self):
        key = cv2.waitKey(self._frame_delay_ms) & 0xFF
        events, self._pending = self._pending, []
        if key == _ESC_KEY:
            events.append(InputEvent(QUIT))
        return events

    def close(self):
        cv2.destroyAllWindows()

    def _ensure_window(self):
        if self._created:
            return
        cv2.namedWindow(self._title, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback(self._title, self._on_mouse)
        self._created = True

    def _on_mouse(self, event, x, y, flags, param):
        if event not in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
            return
        canvas_w, canvas_h = self._canvas_size
        _, _, shown_w, shown_h = cv2.getWindowImageRect(self._title)
        cx, cy = scale_point(x, y, shown_w, shown_h, canvas_w, canvas_h)
        kind = CLICK if event == cv2.EVENT_LBUTTONDOWN else JUMP
        self._pending.append(InputEvent(kind, cx, cy))
