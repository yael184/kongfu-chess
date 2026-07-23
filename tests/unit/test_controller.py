# tests/unit/test_controller.py
from kongfuchess.engine.game_engine import GameSnapshot, MoveResult, REASON_OK
from kongfuchess.input.board_mapper import BoardMapper
from kongfuchess.input.controller import ClickOutcome, Controller
from kongfuchess.model.board import BoardSnapshot
from kongfuchess.model.piece import Piece, Color, PieceKind
from kongfuchess.model.position import Position


def snapshot(width, height, placements=None, game_over=False):
    return GameSnapshot(BoardSnapshot(width, height, placements or {}), game_over)


def rook_at(row, col):
    return Piece(id="r", color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(row, col))


class FakeEngine:
    """Records request_move calls and returns a canned snapshot and result."""

    def __init__(self, snap, result=None):
        self._snapshot = snap
        self._result = result if result is not None else MoveResult.accepted()
        self.requests = []
        self.jumps = []

    def snapshot(self):
        return self._snapshot

    def request_move(self, source, destination):
        self.requests.append((source, destination))
        return self._result

    def request_jump(self, cell):
        self.jumps.append(cell)


# --- first click ---
def test_first_click_on_empty_cell_is_ignored():
    engine = FakeEngine(snapshot(3, 3))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)  # (0,0), empty
    assert controller.selected is None
    assert engine.requests == []


def test_first_click_outside_board_is_ignored_when_no_selection():
    engine = FakeEngine(snapshot(3, 3))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(500, 500)  # (5,5), outside
    assert controller.selected is None
    assert engine.requests == []


def test_first_click_on_a_piece_selects_it():
    engine = FakeEngine(snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)  # (0,0), occupied
    assert controller.selected == Position(0, 0)
    assert engine.requests == []


# --- second click ---
def test_second_in_board_click_requests_move_and_clears_selection():
    engine = FakeEngine(snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)             # select (0,0)
    outcome = controller.handle_click(250, 50)  # (0,2)
    assert engine.requests == [(Position(0, 0), Position(0, 2))]
    assert controller.selected is None
    assert outcome.result.reason == REASON_OK
    assert outcome.target == Position(0, 2)     # the outcome reports which cell the move aimed at


def test_a_non_move_click_reports_an_empty_outcome():
    engine = FakeEngine(snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}))
    controller = Controller(engine, BoardMapper(cell_size=100))
    outcome = controller.handle_click(50, 50)   # first click selects, requests no move
    assert outcome == ClickOutcome()            # no result and no target to react to


def test_a_rejected_move_carries_its_result_and_target_cell():
    engine = FakeEngine(
        snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}),
        result=MoveResult.rejected("illegal_piece_move"),
    )
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)             # select (0,0)
    outcome = controller.handle_click(150, 150)  # (1,1) -> illegal for a rook
    assert not outcome.result.is_accepted
    assert outcome.target == Position(1, 1)     # so a surface can flash exactly that cell


def test_selection_is_cleared_even_when_the_move_is_illegal():
    engine = FakeEngine(
        snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}),
        result=MoveResult.rejected("illegal_piece_move"),
    )
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)      # select (0,0)
    controller.handle_click(150, 150)    # (1,1) -> illegal for a rook, still sends + clears
    assert engine.requests == [(Position(0, 0), Position(1, 1))]
    assert controller.selected is None


def test_outside_board_second_click_cancels_selection_without_a_command():
    engine = FakeEngine(snapshot(3, 3, {Position(0, 0): rook_at(0, 0)}))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)      # select (0,0)
    controller.handle_click(500, 500)    # outside -> cancel, no command
    assert controller.selected is None
    assert engine.requests == []


def test_a_new_first_click_starts_a_fresh_selection_after_a_move():
    placements = {Position(0, 0): rook_at(0, 0), Position(2, 2): rook_at(2, 2)}
    engine = FakeEngine(snapshot(3, 3, placements))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)      # select (0,0)
    controller.handle_click(50, 150)     # (1,0) -> move + clear
    controller.handle_click(250, 250)    # (2,2) -> new first click selects
    assert controller.selected == Position(2, 2)
    assert engine.requests == [(Position(0, 0), Position(1, 0))]


def test_clicking_a_same_color_piece_switches_the_selection():
    placements = {Position(0, 0): rook_at(0, 0), Position(0, 2): rook_at(0, 2)}
    engine = FakeEngine(snapshot(3, 3, placements))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_click(50, 50)      # select (0,0)
    controller.handle_click(250, 50)     # (0,2) is same-color -> switch selection, no move
    assert controller.selected == Position(0, 2)
    assert engine.requests == []


# --- jump ---
def test_handle_jump_maps_pixels_and_delegates_to_request_jump():
    engine = FakeEngine(snapshot(3, 3))
    controller = Controller(engine, BoardMapper(cell_size=100))
    controller.handle_jump(150, 250)     # (row 2, col 1)
    assert engine.jumps == [Position(2, 1)]
