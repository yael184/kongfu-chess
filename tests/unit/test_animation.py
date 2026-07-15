"""The view's time-driven frame selection and the motion-progress the renderer interpolates with.

Pure logic, no OpenCV: Animation.frame_at is a function of elapsed time, and Motion.progress is a
function of the clock. Both are what let the renderer stay stateless.
"""
from kongfuchess.model.piece import Color, Piece, PieceKind
from kongfuchess.model.position import Position
from kongfuchess.realtime.motion import Motion, MotionView
from kongfuchess.view.animation import Animation


def test_looping_animation_wraps_through_its_frames():
    anim = Animation(frames=("a", "b", "c"), frames_per_sec=4, is_loop=True)
    assert anim.frame_at(0) == "a"
    assert anim.frame_at(250) == "b"
    assert anim.frame_at(500) == "c"
    assert anim.frame_at(750) == "a"      # wraps back to the start


def test_one_shot_animation_holds_on_its_last_frame():
    anim = Animation(frames=("a", "b", "c"), frames_per_sec=4, is_loop=False)
    assert anim.frame_at(750) == "c"
    assert anim.frame_at(100000) == "c"


def test_single_frame_and_zero_fps_show_the_first_frame():
    assert Animation(("only",), frames_per_sec=8, is_loop=True).frame_at(9999) == "only"
    assert Animation(("a", "b"), frames_per_sec=0, is_loop=True).frame_at(9999) == "a"


def _piece_at(row, col):
    return Piece(id=1, color=Color.WHITE, kind=PieceKind.ROOK, cell=Position(row, col))


def test_motion_progress_runs_from_zero_to_one():
    motion = Motion.start(_piece_at(0, 0), Position(0, 3), now_ms=1000, ms_per_cell=1000)
    assert motion.progress(1000) == 0.0            # at the source
    assert motion.progress(2500) == 0.5            # halfway (arrival at 4000)
    assert motion.progress(4000) == 1.0            # arrived
    assert motion.progress(9999) == 1.0            # clamped past arrival


def test_zero_length_motion_is_immediately_arrived():
    motion = Motion.start(_piece_at(2, 2), Position(2, 2), now_ms=0, ms_per_cell=1000)
    assert motion.progress(0) == 1.0


def test_motion_view_is_a_plain_read_only_record():
    view = MotionView(_piece_at(0, 0), Position(0, 0), Position(0, 3), 0.5)
    assert view.progress == 0.5 and view.destination == Position(0, 3)
