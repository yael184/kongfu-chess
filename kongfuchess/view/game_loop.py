# view/game_loop.py
"""The real-time driver: clock in, pixels out — the visual sibling of the text ScriptRunner.

Each iteration it measures real elapsed time, advances the engine by that much (so arrivals,
collisions, cooldowns and the victory condition happen), renders the state through the injected
BoardView, and turns the surface's input events into engine commands via the injected Controller. It
decides no chess and maps no pixels itself — the Renderer scales coordinates, the Controller owns
selection, and the engine owns the rules.
"""
import time

from kongfuchess.view.rendering.renderer import CLICK, JUMP, QUIT


class GameLoop:
    def __init__(self, engine, controller, board_view, renderer, clock=time.perf_counter):
        self._engine = engine
        self._controller = controller
        self._board_view = board_view
        self._renderer = renderer
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
                self._renderer.draw_frame(self._render(dt_ms))
                if self._handle(self._renderer.poll_events()):
                    break
        finally:
            self._renderer.close()

    def _render(self, dt_ms):
        return self._board_view.render(
            self._engine.snapshot(), self._engine.active_motions(),
            self._controller.selected, dt_ms,
        )

    def _handle(self, events) -> bool:
        """Apply input events; return True when the user asked to quit."""
        for event in events:
            if event.kind == QUIT:
                return True
            if event.kind == CLICK:
                self._controller.handle_click(event.x, event.y)
            elif event.kind == JUMP:
                self._controller.handle_jump(event.x, event.y)
        return False
