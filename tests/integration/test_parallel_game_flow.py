# tests/integration/test_parallel_game_flow.py
# The real-time heart of Kung-Fu-Chess: many pieces move at once, and a piece rests after acting.
# Wired through the composition root exactly as the game is.
import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.engine.game_engine import REASON_OK, REASON_PIECE_BUSY
from kongfuchess.model.board import Board
from kongfuchess.model.piece import Color, Piece, PieceKind, PieceState
from kongfuchess.model.position import Position


def build(*pieces, width=5, height=5):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return app_factory.build_engine(board, config.load()), board


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def test_two_pieces_move_at_the_same_time_and_both_arrive():
    a = pc("a", Color.WHITE, PieceKind.ROOK, 0, 0)
    b = pc("b", Color.WHITE, PieceKind.ROOK, 4, 0)
    engine, board = build(a, b)
    assert engine.request_move(Position(0, 0), Position(0, 3)).reason == REASON_OK
    assert engine.request_move(Position(4, 0), Position(4, 3)).reason == REASON_OK  # in parallel
    engine.wait(3000)
    assert board.piece_at(Position(0, 3)) is a
    assert board.piece_at(Position(4, 3)) is b


def test_a_piece_is_busy_through_its_move_and_its_long_rest():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    engine, board = build(rook)
    engine.request_move(Position(0, 0), Position(0, 1))     # arrives at 1000, rests until 3000
    engine.wait(1000)
    assert rook.state == PieceState.LONG_REST
    # Still resting: a fresh command for it is rejected.
    assert engine.request_move(Position(0, 1), Position(0, 2)).reason == REASON_PIECE_BUSY
    engine.wait(2000)                                        # long rest elapses (total 3000)
    assert rook.state == PieceState.IDLE
    assert engine.request_move(Position(0, 1), Position(0, 2)).reason == REASON_OK
