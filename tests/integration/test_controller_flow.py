# tests/integration/test_controller_flow.py
# End-to-end: Controller -> GameEngine -> rules + RealTimeArbiter over the model.
# Wired through the composition root, exactly as main.py wires it.
import config
from composition import app_factory
from model.board import Board
from model.piece import Piece, Color, PieceKind
from model.position import Position


def build_controller():
    cfg = config.load()
    board = Board(3, 3)
    rook = Piece(id="wR", color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(0, 0))
    board.add_piece(rook)
    engine = app_factory.build_engine(board, cfg)
    controller = app_factory.build_controller(engine, cfg)
    return controller, engine, board, rook


def test_click_to_select_then_move_drives_a_real_motion():
    controller, engine, board, rook = build_controller()
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
    controller, engine, board, rook = build_controller()
    controller.handle_click(50, 50)     # select (0,0)
    controller.handle_click(150, 150)   # (1,1) diagonal -> illegal for a rook
    assert controller.selected is None
    engine.wait(2000)
    assert board.piece_at(Position(0, 0)) is rook   # never moved


def test_outside_board_click_cancels_selection_without_moving():
    controller, engine, board, rook = build_controller()
    controller.handle_click(50, 50)     # select (0,0)
    controller.handle_click(999, 999)   # outside -> cancel, no command
    assert controller.selected is None
    engine.wait(2000)
    assert board.piece_at(Position(0, 0)) is rook
