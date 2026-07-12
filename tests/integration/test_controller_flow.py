# tests/integration/test_controller_flow.py
# End-to-end: Controller -> GameEngine -> RuleEngine + RealTimeArbiter over the model.
from engine.game_engine import GameEngine
from input.controller import Controller
from model.board import Board
from model.game_state import GameState
from model.piece import Piece, Color, PieceKind
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter


def build_controller():
    board = Board(3, 3)
    rook = Piece(id="wR", color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(0, 0))
    board.add_piece(rook)
    state = GameState(board=board)
    engine = GameEngine(state, RealTimeArbiter())
    return Controller(engine), engine, state, board, rook


def test_click_to_select_then_move_drives_a_real_motion():
    controller, engine, state, board, rook = build_controller()
    controller.handle_click(50, 50)     # select (0,0)
    assert controller.selected == Position(0, 0)
    controller.handle_click(150, 50)    # (0,1) -> request move, clears selection
    assert controller.selected is None
    # The move takes time: still on source until it arrives.
    engine.wait(500)
    assert board.piece_at(Position(0, 0)) is rook
    engine.wait(500)                    # total 1000 -> arrived
    assert board.piece_at(Position(0, 1)) is rook


def test_illegal_click_move_is_absorbed_and_leaves_board_unchanged():
    controller, engine, state, board, rook = build_controller()
    controller.handle_click(50, 50)     # select (0,0)
    controller.handle_click(150, 150)   # (1,1) diagonal -> illegal for a rook
    assert controller.selected is None
    engine.wait(2000)
    assert board.piece_at(Position(0, 0)) is rook   # never moved
    assert engine._arbiter.has_active_motion() is False


def test_outside_board_click_cancels_selection_without_moving():
    controller, engine, state, board, rook = build_controller()
    controller.handle_click(50, 50)     # select (0,0)
    controller.handle_click(999, 999)   # outside -> cancel, no command
    assert controller.selected is None
    engine.wait(2000)
    assert board.piece_at(Position(0, 0)) is rook
