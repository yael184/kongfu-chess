# tests/integration/test_realtime_game_flow.py
# End-to-end vertical slice: GameEngine + the real rules + the real RealTimeArbiter over the model,
# wired through the composition root exactly as main.py wires it.
import config
from composition import app_factory
from engine.game_engine import REASON_OK, REASON_GAME_OVER, REASON_MOTION_IN_PROGRESS
from model.board import Board
from model.piece import Piece, Color, PieceKind, PieceState
from model.position import Position
from rules.rule_engine import REASON_ILLEGAL_PIECE_MOVE


def build_game():
    board = Board(3, 3)
    rook = Piece(id="wR", color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(0, 0))
    king = Piece(id="bK", color=Color.BLACK, kind=PieceKind.KING, cell=Position(0, 2))
    board.add_piece(rook)
    board.add_piece(king)
    engine = app_factory.build_engine(board, config.load())
    return engine, board, rook, king


def test_move_takes_time_and_board_updates_only_on_arrival():
    engine, board, rook, king = build_game()
    assert engine.request_move(Position(0, 0), Position(0, 1)).reason == REASON_OK
    engine.wait(500)                                   # mid-flight
    assert board.piece_at(Position(0, 0)) is rook      # still logically on source
    assert board.piece_at(Position(0, 1)) is None
    engine.wait(500)                                   # total 1000 -> arrived
    assert board.piece_at(Position(0, 0)) is None
    assert board.piece_at(Position(0, 1)) is rook


def test_second_move_rejected_while_a_motion_is_active():
    engine, board, rook, king = build_game()
    engine.request_move(Position(0, 0), Position(0, 1))
    result = engine.request_move(Position(0, 0), Position(1, 0))
    assert result.reason == REASON_MOTION_IN_PROGRESS


def test_illegal_move_is_rejected_before_any_motion():
    engine, board, rook, king = build_game()
    result = engine.request_move(Position(0, 0), Position(1, 1))  # diagonal, illegal for a rook
    assert result.reason == REASON_ILLEGAL_PIECE_MOVE
    # No motion started: a later wait leaves the board untouched.
    engine.wait(5000)
    assert board.piece_at(Position(0, 0)) is rook


def test_capturing_the_king_ends_the_game_and_freezes_moves():
    engine, board, rook, king = build_game()
    assert engine.request_move(Position(0, 0), Position(0, 2)).reason == REASON_OK  # 2 cells -> 2000ms
    engine.wait(2000)
    assert engine.snapshot().game_over is True
    assert board.piece_at(Position(0, 2)) is rook
    assert king.state == PieceState.CAPTURED
    # further moves are rejected once the game is over
    assert engine.request_move(Position(0, 2), Position(0, 1)).reason == REASON_GAME_OVER


def test_snapshot_tracks_the_logical_board_across_time():
    engine, board, rook, king = build_game()
    engine.request_move(Position(0, 0), Position(0, 1))
    before = engine.snapshot()
    assert before.piece_at(Position(0, 0)) is rook   # before arrival
    assert before.piece_at(Position(0, 1)) is None
    engine.wait(1000)
    after = engine.snapshot()
    assert after.piece_at(Position(0, 0)) is None
    assert after.piece_at(Position(0, 1)) is rook
