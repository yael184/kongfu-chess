# tests/unit/test_real_time_arbiter.py
import config
from model.board import Board
from model.piece import Piece, Color, PieceKind, PieceState
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def board_with(width, height, *pieces):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return board


def test_no_motion_active_initially():
    assert RealTimeArbiter().has_active_motion() is False


def test_start_motion_marks_active_and_keeps_piece_on_source():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    assert arbiter.has_active_motion() is True
    # The logical board is unchanged until arrival.
    assert board.piece_at(Position(0, 0)) is rook
    assert board.piece_at(Position(0, 2)) is None
    assert rook.state == PieceState.MOVING


def test_motion_is_not_resolved_before_arrival():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))  # 2 cells -> 2000ms
    outcome = arbiter.advance_time(1000)  # only halfway
    assert arbiter.has_active_motion() is True
    assert board.piece_at(Position(0, 0)) is rook
    assert board.piece_at(Position(0, 2)) is None
    assert outcome.king_captured is False


def test_motion_resolves_on_arrival():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 0)) is None
    assert board.piece_at(Position(0, 2)) is rook
    assert rook.cell == Position(0, 2)
    assert rook.state == PieceState.IDLE
    assert arbiter.has_active_motion() is False


def test_single_square_takes_1000ms_exactly():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    arbiter.advance_time(999)
    assert board.piece_at(Position(0, 0)) is rook  # not yet arrived
    arbiter.advance_time(1)  # total 1000
    assert board.piece_at(Position(0, 1)) is rook


def test_diagonal_uses_cell_step_duration():
    bishop = pc("b", Color.WHITE, PieceKind.BISHOP, 0, 0)
    board = board_with(4, 4, bishop)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(3, 3))  # 3 diagonal cells -> 3000ms
    arbiter.advance_time(2999)
    assert board.piece_at(Position(0, 0)) is bishop
    arbiter.advance_time(1)
    assert board.piece_at(Position(3, 3)) is bishop


def test_arrival_captures_enemy_and_reports_non_king():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, enemy)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    outcome = arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 2)) is rook
    assert enemy.state == PieceState.CAPTURED
    assert outcome.king_captured is False


def test_capturing_a_king_reports_king_capture():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    king = pc("k", Color.BLACK, PieceKind.KING, 0, 2)
    board = board_with(3, 3, rook, king)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    outcome = arbiter.advance_time(2000)
    assert outcome.king_captured is True
    assert board.piece_at(Position(0, 2)) is rook
    assert king.state == PieceState.CAPTURED


def test_default_ms_per_cell_comes_from_config():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter()  # no override -> uses config
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    arbiter.advance_time(config.MS_PER_CELL)
    assert board.piece_at(Position(0, 1)) is rook


def test_pawn_promotes_to_queen_on_arrival():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 1, 0)
    board = board_with(3, 3, pawn)
    arbiter = RealTimeArbiter(ms_per_cell=1000)
    arbiter.start_motion(board, Position(1, 0), Position(0, 0))  # reaches white's last row
    arbiter.advance_time(1000)
    assert board.piece_at(Position(0, 0)).kind == PieceKind.QUEEN


# --- jump / dodge ---
def test_airborne_piece_eats_an_attacker_arriving_during_the_jump():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 0)
    rook = pc("r", Color.BLACK, PieceKind.ROOK, 1, 1)
    board = board_with(3, 3, king, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000, jump_duration_ms=1000)
    arbiter.request_jump(board, Position(1, 0))                 # king jumps, lands at 1000
    arbiter.start_motion(board, Position(1, 1), Position(1, 0))  # rook attacks, arrives at 1000
    arbiter.advance_time(1000)
    assert board.piece_at(Position(1, 0)) is king   # king survived
    assert board.piece_at(Position(1, 1)) is None   # attacker removed from its origin
    assert rook.state == PieceState.CAPTURED


def test_attacker_arriving_after_landing_captures_normally():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 0)
    rook = pc("r", Color.BLACK, PieceKind.ROOK, 1, 3)
    board = board_with(4, 3, king, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000, jump_duration_ms=1000)
    arbiter.request_jump(board, Position(1, 0))     # jump lands at 1000
    arbiter.advance_time(1000)                       # king lands
    arbiter.start_motion(board, Position(1, 3), Position(1, 0))  # arrives at 1000 + 3000 = 4000
    arbiter.advance_time(3000)
    assert board.piece_at(Position(1, 0)) is rook   # normal capture
    assert king.state == PieceState.CAPTURED


def test_cannot_jump_a_moving_piece_or_an_empty_cell():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = RealTimeArbiter(ms_per_cell=1000, jump_duration_ms=1000)
    arbiter.request_jump(board, Position(2, 2))                 # empty cell -> ignored
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))  # rook now in flight
    arbiter.request_jump(board, Position(0, 0))                 # in flight -> ignored
    arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 2)) is rook   # the move completed normally
