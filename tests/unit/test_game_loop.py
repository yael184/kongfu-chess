"""GameLoop wiring for the refused-move flash: a rejected click becomes a flash on a later frame.

The loop is driven with in-memory fakes (the point of the Renderer port). A real MoveFeedback is
used so the actual reject->flash path is exercised; only the surface around it is faked.
"""
from kongfuchess.engine.game_engine import MoveResult
from kongfuchess.input.controller import ClickOutcome
from kongfuchess.model.position import Position
from kongfuchess.view.game_loop import GameLoop
from kongfuchess.view.rendering.move_feedback import MoveFeedback
from kongfuchess.view.rendering.renderer import CLICK, InputEvent, QUIT


class FakeSnapshot:
    game_over = False


class FakeEngine:
    def wait(self, dt_ms):
        pass

    def snapshot(self):
        return FakeSnapshot()

    def active_motions(self):
        return ()

    def rest_windows(self):
        return ()

    def legal_destinations(self, cell):
        return ()

    def game_time_ms(self):
        return 0


class FakeController:
    """Returns a canned ClickOutcome for a click, and never selects anything."""

    def __init__(self, outcome):
        self._outcome = outcome
        self.selected = None

    def handle_click(self, x, y):
        return self._outcome

    def handle_jump(self, x, y):
        pass


class RecordingBoardView:
    def __init__(self):
        self.states = []

    def render(self, state, dt_ms):
        self.states.append(state)
        return object()


class ScriptedRenderer:
    """Plays a fixed list of event batches, one per frame, then reports QUIT forever."""

    def __init__(self, batches):
        self._batches = list(batches)

    def draw_frame(self, frame):
        pass

    def poll_events(self):
        return self._batches.pop(0) if self._batches else [InputEvent(QUIT)]

    def close(self):
        pass


def _run(outcome):
    board_view = RecordingBoardView()
    loop = GameLoop(
        FakeEngine(),
        FakeController(outcome),
        board_view,
        ScriptedRenderer([[InputEvent(CLICK, 150, 150)], [InputEvent(QUIT)]]),
        move_feedback=MoveFeedback(500),
        clock=lambda: 0.0,          # no wall time elapses: isolates the flash from ageing
    )
    loop.run()
    return board_view.states


def test_a_rejected_click_flashes_the_target_on_the_next_frame():
    rejected = ClickOutcome(MoveResult.rejected("illegal_piece_move"), Position(1, 1))
    states = _run(rejected)
    assert states[0].rejected is None                       # first frame, before the click
    assert states[1].rejected.cell == Position(1, 1)        # the refused cell now flashes


def test_an_accepted_move_raises_no_flash():
    accepted = ClickOutcome(MoveResult.accepted(), Position(1, 1))
    states = _run(accepted)
    assert all(state.rejected is None for state in states)
