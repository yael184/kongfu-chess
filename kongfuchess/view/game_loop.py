# view/game_loop.py
"""The real-time driver for the OpenCV surface: clock in, pixels out.

This is the view's analogue of the text surface's ScriptRunner, but time flows on its own instead of
arriving as `wait` commands. Each iteration it measures the real elapsed time, advances the engine by
that much (so arrivals, captures and the victory condition happen), turns mouse clicks into engine
commands through the injected Controller, and draws the resulting state. It decides no chess and
maps no pixels itself — the Controller and BoardMapper already own that.
"""
import time

import cv2

# OpenCV mouse events, named once so the loop reads in intent, not magic numbers.
_LEFT_DOWN = cv2.EVENT_LBUTTONDOWN
_RIGHT_DOWN = cv2.EVENT_RBUTTONDOWN
_ESC_KEY = 27
_FRAME_DELAY_MS = 15   # ~66 fps ceiling; also pumps the OpenCV window's event queue


class GameLoop:
    """Drives the engine in real time and renders it in an OpenCV window until the window is closed.

    Left-click drives the select/move flow; right-click makes the clicked piece jump (a dodge).
    Every collaborator is injected; `clock` is injectable so the loop is testable without wall time.
    """

    def __init__(self, engine, controller, renderer, window_title,
                 clock=time.perf_counter, frame_delay_ms=_FRAME_DELAY_MS, quit_key=_ESC_KEY):
        self._engine = engine
        self._controller = controller
        self._renderer = renderer
        self._title = window_title
        self._clock = clock
        self._frame_delay_ms = frame_delay_ms
        self._quit_key = quit_key
        self._pending_clicks = []
        self._elapsed_ms = 0

    def run(self):
        cv2.namedWindow(self._title)
        cv2.setMouseCallback(self._title, self._on_mouse)
        last = self._clock()
        try:
            while True:
                now = self._clock()
                dt_ms = int((now - last) * 1000)
                last = now
                self._step(dt_ms)
                cv2.imshow(self._title, self._frame().img)
                if (cv2.waitKey(self._frame_delay_ms) & 0xFF) == self._quit_key:
                    break
        finally:
            cv2.destroyAllWindows()

    def _step(self, dt_ms):
        if dt_ms > 0:
            self._engine.wait(dt_ms)
            self._elapsed_ms += dt_ms
        self._drain_clicks()

    def _frame(self):
        return self._renderer.render(
            self._engine.snapshot(),
            self._engine.active_motions(),
            self._engine.airborne_cells(),
            self._controller.selected,
            self._elapsed_ms,
        )

    def _on_mouse(self, event, x, y, flags, param):
        if event in (_LEFT_DOWN, _RIGHT_DOWN):
            self._pending_clicks.append((event, x, y))

    def _drain_clicks(self):
        clicks, self._pending_clicks = self._pending_clicks, []
        for event, x, y in clicks:
            if event == _LEFT_DOWN:
                self._controller.handle_click(x, y)
            else:
                self._controller.handle_jump(x, y)
