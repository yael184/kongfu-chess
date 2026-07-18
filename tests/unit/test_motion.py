# tests/unit/test_motion.py
from kongfuchess.model.piece import Piece, Color, PieceKind
from kongfuchess.model.position import Position
from kongfuchess.realtime.motion import Motion, MotionView, cell_distance


def piece_at(row, col):
    return Piece(id="p", color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(row, col))


def test_one_square_takes_1000ms():
    motion = Motion.start(piece_at(0, 0), Position(0, 1), now_ms=0, ms_per_cell=1000)
    assert motion.arrival_ms == 1000


def test_two_squares_take_2000ms():
    motion = Motion.start(piece_at(0, 0), Position(0, 2), now_ms=0, ms_per_cell=1000)
    assert motion.arrival_ms == 2000


def test_diagonal_one_square_takes_1000ms():
    motion = Motion.start(piece_at(0, 0), Position(1, 1), now_ms=0, ms_per_cell=1000)
    assert motion.arrival_ms == 1000


def test_diagonal_three_squares_take_3000ms():
    motion = Motion.start(piece_at(0, 0), Position(3, 3), now_ms=0, ms_per_cell=1000)
    assert motion.arrival_ms == 3000


def test_start_time_offset_is_respected():
    motion = Motion.start(piece_at(0, 0), Position(0, 1), now_ms=500, ms_per_cell=1000)
    assert motion.arrival_ms == 1500


def test_has_arrived_is_inclusive_at_arrival_time():
    motion = Motion.start(piece_at(0, 0), Position(0, 1), now_ms=0, ms_per_cell=1000)
    assert motion.has_arrived(999) is False
    assert motion.has_arrived(1000) is True
    assert motion.has_arrived(1500) is True


def test_cell_distance_is_chebyshev():
    assert cell_distance(Position(0, 0), Position(0, 3)) == 3
    assert cell_distance(Position(0, 0), Position(3, 3)) == 3
    assert cell_distance(Position(0, 0), Position(2, 3)) == 3


# --- progress / MotionView: what a renderer interpolates a gliding piece with ---
def test_progress_runs_from_zero_to_one():
    motion = Motion.start(piece_at(0, 0), Position(0, 3), now_ms=1000, ms_per_cell=1000)
    assert motion.progress(1000) == 0.0            # at the source
    assert motion.progress(2500) == 0.5            # halfway (arrival at 4000)
    assert motion.progress(4000) == 1.0            # arrived
    assert motion.progress(9999) == 1.0            # clamped past arrival


def test_zero_length_motion_is_immediately_arrived():
    motion = Motion.start(piece_at(2, 2), Position(2, 2), now_ms=0, ms_per_cell=1000)
    assert motion.progress(0) == 1.0


def test_motion_view_is_a_plain_read_only_record():
    view = MotionView(piece_at(0, 0), Position(0, 0), Position(0, 3), 0.5)
    assert view.progress == 0.5 and view.destination == Position(0, 3)
