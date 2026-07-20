"""The mouse-coordinate contract for the resizable window — no window opened.

OpenCV hands the callback coordinates already expressed in canvas (image) pixels, whatever size the
window is shown at. The renderer must therefore pass them through untouched: rescaling them by the
window size applies the zoom twice and lands clicks on the wrong square.
"""
import cv2

from kongfuchess.view.rendering.cv2_renderer import Cv2Renderer
from kongfuchess.view.rendering.renderer import CLICK, JUMP


def _click(renderer, event, x, y):
    renderer._on_mouse(event, x, y, flags=0, param=None)
    return renderer._pending


def test_a_left_click_becomes_a_click_event_at_the_reported_pixels():
    renderer = Cv2Renderer("t")
    (event,) = _click(renderer, cv2.EVENT_LBUTTONDOWN, 53, 61)
    assert (event.kind, event.x, event.y) == (CLICK, 53, 61)


def test_a_right_click_becomes_a_jump_event_at_the_reported_pixels():
    renderer = Cv2Renderer("t")
    (event,) = _click(renderer, cv2.EVENT_RBUTTONDOWN, 340, 7)
    assert (event.kind, event.x, event.y) == (JUMP, 340, 7)


def test_coordinates_are_never_rescaled_by_the_window_size():
    # The frame drawn is irrelevant to the mapping: whatever zoom the window is at, the coordinates
    # the callback reports are canvas pixels already.
    renderer = Cv2Renderer("t")
    (event,) = _click(renderer, cv2.EVENT_LBUTTONDOWN, 799, 799)
    assert (event.x, event.y) == (799, 799)


def test_other_mouse_events_are_ignored():
    renderer = Cv2Renderer("t")
    assert _click(renderer, cv2.EVENT_MOUSEMOVE, 10, 20) == []
