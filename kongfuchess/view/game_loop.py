# view/game_loop.py
"""The real-time driver: clock in, pixels out — the visual sibling of the text ScriptRunner.

Each iteration it measures real elapsed time, advances the engine by that much (so arrivals,
collisions, cooldowns and the victory condition happen), lets the optional settlement detector turn
the new snapshot into events, renders the state through the injected BoardView, and turns the
surface's input events into engine commands via the injected Controller. It decides no chess and
maps no pixels itself — the Renderer scales window coordinates, the Controller owns selection, and
the engine owns the rules.
"""
import time

from kongfuchess.view.rendering.renderer import CLICK, JUMP, QUIT


class GameLoop:
    def __init__(self, engine, controller, board_view, renderer,
                 settlement_detector=None, board_width_px=None, clock=time.perf_counter):
        self._engine = engine
        self._controller = controller
        self._board_view = board_view
        self._renderer = renderer
        self._detector = settlement_detector
        self._board_width_px = board_width_px   # clicks at or beyond this x are on the side panel
        self._clock = clock

    def run(self):
        last = self._clock()
        try:
            while True:
                now = self._clock()
                dt_ms = int((now - last) * 1000)
                last = now
                if dt_ms > 0:
                    self._engine.wait(dt_ms)
                snapshot = self._engine.snapshot()
                if self._detector is not None:
                    self._detector.observe(snapshot)
                frame = self._board_view.render(
                    snapshot, self._engine.active_motions(), self._controller.selected, dt_ms)
                self._renderer.draw_frame(frame)
                if self._handle(self._renderer.poll_events()):
                    break
        finally:
            self._renderer.close()

    def _handle(self, events) -> bool:
        """Apply input events; return True when the user asked to quit."""
        for event in events:
            if event.kind == QUIT:
                return True
            if self._on_panel(event):
                continue
            if event.kind == CLICK:
                self._controller.handle_click(event.x, event.y)
            elif event.kind == JUMP:
                self._controller.handle_jump(event.x, event.y)
        return False

    def _on_panel(self, event) -> bool:
        return self._board_width_px is not None and event.x >= self._board_width_px
