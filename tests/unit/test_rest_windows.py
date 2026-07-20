"""The cooldown countdown the renderer draws: rest_windows, the timing sibling of active_motions.

Pure timing — the arbiter reports a cell and how much of the wait is left, and nothing here knows
why the piece is waiting.
"""
from kongfuchess.model.piece import Color, PieceKind, PieceState
from kongfuchess.model.position import Position

from tests.unit.test_real_time_arbiter import board_with, make_arbiter, pc


def _resting_rook():
    """A rook one cell from its destination, arbiter clocked so its move has just landed."""
    rook = pc("r1", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(8, 8, rook)
    arbiter = make_arbiter(ms_per_cell=1000, long_rest_ms=2000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    return arbiter, rook


def test_nothing_rests_before_anything_has_happened():
    board = board_with(8, 8, pc("r1", Color.WHITE, PieceKind.ROOK, 0, 0))
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    assert arbiter.rest_windows() == []          # still in flight, not resting


def test_a_cooldown_starts_full_and_drains_to_empty():
    arbiter, rook = _resting_rook()
    arbiter.advance_time(1000)                   # arrives; the 2000ms cooldown begins now
    assert rook.state is PieceState.LONG_REST
    (window,) = arbiter.rest_windows()
    assert window.cell == Position(0, 1)
    assert window.remaining == 1.0

    arbiter.advance_time(1000)                   # halfway through the rest
    (window,) = arbiter.rest_windows()
    assert window.remaining == 0.5

    arbiter.advance_time(1000)                   # the rest is over
    assert arbiter.rest_windows() == []
    assert rook.state is PieceState.IDLE


def test_the_countdown_is_measured_from_the_arrival_not_the_tick_end():
    """One coarse tick that both lands the move and eats into the rest must not restart the clock."""
    arbiter, _ = _resting_rook()
    arbiter.advance_time(2000)                   # 1000ms of travel + 1000ms of the 2000ms rest
    (window,) = arbiter.rest_windows()
    assert window.remaining == 0.5               # not 1.0


def test_a_jump_reads_as_one_continuous_countdown_across_both_of_its_phases():
    piece = pc("r1", Color.WHITE, PieceKind.ROOK, 4, 4)
    board = board_with(8, 8, piece)
    arbiter = make_arbiter(jump_duration_ms=1000, short_rest_ms=1000)
    arbiter.request_jump(board, Position(4, 4))

    (window,) = arbiter.rest_windows()
    assert window.remaining == 1.0

    arbiter.advance_time(1000)                   # jump done, short rest begins — no restart
    assert piece.state is PieceState.SHORT_REST
    (window,) = arbiter.rest_windows()
    assert window.remaining == 0.5

    arbiter.advance_time(1000)
    assert arbiter.rest_windows() == []


def test_a_captured_piece_leaves_no_countdown_behind():
    white = pc("w", Color.WHITE, PieceKind.ROOK, 0, 0)
    black = pc("b", Color.BLACK, PieceKind.ROOK, 0, 1)
    board = board_with(8, 8, white, black)
    arbiter = make_arbiter(ms_per_cell=1000, long_rest_ms=2000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    arbiter.advance_time(1000)                   # white takes black and rests

    cells = [window.cell for window in arbiter.rest_windows()]
    assert cells == [Position(0, 1)]             # only the survivor
