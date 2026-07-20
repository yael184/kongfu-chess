"""Closing the window with its X button must end the game — no window is opened here.

cv2 delivers no close event and its next `imshow` silently recreates a dismissed window, so the
renderer polls the window's visibility and reports QUIT itself.
"""
import cv2
import pytest

from kongfuchess.view.rendering.cv2_renderer import Cv2Renderer
from kongfuchess.view.rendering.renderer import QUIT

_NO_KEY = 255


@pytest.fixture
def renderer(monkeypatch):
    monkeypatch.setattr(cv2, "waitKey", lambda delay: _NO_KEY)
    made = Cv2Renderer("t")
    made._created = True          # as if a frame had already been drawn
    return made


def _visibility(monkeypatch, value):
    monkeypatch.setattr(cv2, "getWindowProperty", lambda title, prop: value)


def test_a_dismissed_window_reports_quit(monkeypatch, renderer):
    _visibility(monkeypatch, 0.0)
    assert [event.kind for event in renderer.poll_events()] == [QUIT]


def test_a_visible_window_reports_nothing(monkeypatch, renderer):
    _visibility(monkeypatch, 1.0)
    assert renderer.poll_events() == []


def test_a_backend_that_errors_on_a_gone_window_also_reports_quit(monkeypatch, renderer):
    def boom(title, prop):
        raise cv2.error("window does not exist")
    monkeypatch.setattr(cv2, "getWindowProperty", boom)
    assert [event.kind for event in renderer.poll_events()] == [QUIT]


def test_no_quit_before_the_first_frame_is_drawn(monkeypatch):
    monkeypatch.setattr(cv2, "waitKey", lambda delay: _NO_KEY)
    monkeypatch.setattr(cv2, "getWindowProperty", lambda title, prop: 0.0)
    assert Cv2Renderer("t").poll_events() == []
