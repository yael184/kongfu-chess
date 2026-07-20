# view/rendering/cv2_renderer.py
"""The one concrete Renderer: a resizable OpenCV window and its mouse input.

This is the only module that drives cv2's display/input (`imshow`/`waitKey`/`setMouseCallback`) — the
same plumbing `Img.show()` uses internally, driven per-frame instead of blocking (final_plan §3).
The window is resizable (`WINDOW_NORMAL | WINDOW_KEEPRATIO`). It reports QUIT both on <Esc> and when
the user dismisses the window with its X button — see `_was_dismissed`.

**Mouse coordinates arrive already in canvas (image) pixels.** OpenCV's highgui backends undo the
window's own scaling before invoking the callback, so a click on a window shown at any zoom is
reported against the frame we drew. Rescaling it here — e.g. by `getWindowImageRect`, which reports
the *client area*, not the letterboxed image rect — would apply the zoom a second time and land the
move on the wrong square. Pass the coordinates through unchanged.
"""
import cv2

from kongfuchess.view.rendering.renderer import CLICK, JUMP, QUIT, InputEvent

_ESC_KEY = 27
_FRAME_DELAY_MS = 15   # ~66 fps ceiling; also pumps the window's event queue


class Cv2Renderer:
    def __init__(self, window_title, frame_delay_ms=_FRAME_DELAY_MS):
        self._title = window_title
        self._frame_delay_ms = frame_delay_ms
        self._created = False
        self._pending = []           # InputEvents captured by the mouse callback

    def draw_frame(self, frame):
        self._ensure_window()
        cv2.imshow(self._title, frame.img)

    def poll_events(self):
        key = cv2.waitKey(self._frame_delay_ms) & 0xFF
        events, self._pending = self._pending, []
        if key == _ESC_KEY or self._was_dismissed():
            events.append(InputEvent(QUIT))
        return events

    def _was_dismissed(self) -> bool:
        """True once the user has closed the window with its X button.

        cv2 delivers no close event — the window is simply gone, and the *next* `imshow` silently
        recreates it. Without this check the game loop never learns the window was dismissed, draws
        another frame, and the window reappears in the same state; the only way out is Ctrl-C.
        """
        if not self._created:
            return False
        try:
            return cv2.getWindowProperty(self._title, cv2.WND_PROP_VISIBLE) < 1
        except cv2.error:
            return True

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
        kind = CLICK if event == cv2.EVENT_LBUTTONDOWN else JUMP
        self._pending.append(InputEvent(kind, x, y))
