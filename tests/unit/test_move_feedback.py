"""The refused-move flash: it starts full, fades with elapsed time, and clears itself.

Pure timing state — no board, no engine — so the tests just drive `reject`/`age` and read `flash`.
"""
from kongfuchess.model.position import Position
from kongfuchess.view.rendering.move_feedback import MoveFeedback


def test_no_flash_before_anything_is_refused():
    assert MoveFeedback(500).flash is None


def test_a_refused_move_flashes_its_cell_at_full_intensity():
    feedback = MoveFeedback(500)
    feedback.reject(Position(1, 2))
    flash = feedback.flash
    assert flash.cell == Position(1, 2)
    assert flash.intensity == 1.0


def test_the_flash_fades_as_time_passes():
    feedback = MoveFeedback(500)
    feedback.reject(Position(0, 0))
    feedback.age(250)                       # half the window elapsed
    assert feedback.flash.intensity == 0.5


def test_the_flash_clears_itself_once_it_has_fully_faded():
    feedback = MoveFeedback(500)
    feedback.reject(Position(0, 0))
    feedback.age(500)
    assert feedback.flash is None


def test_ageing_past_the_window_does_not_go_negative():
    feedback = MoveFeedback(500)
    feedback.reject(Position(0, 0))
    feedback.age(9000)
    assert feedback.flash is None           # cleared, not a negative intensity


def test_a_new_refusal_restarts_the_flash():
    feedback = MoveFeedback(500)
    feedback.reject(Position(0, 0))
    feedback.age(400)
    feedback.reject(Position(3, 3))         # a second refusal
    flash = feedback.flash
    assert flash.cell == Position(3, 3) and flash.intensity == 1.0


def test_a_zero_duration_disables_the_flash_entirely():
    feedback = MoveFeedback(0)
    feedback.reject(Position(0, 0))
    assert feedback.flash is None


def test_rejecting_no_cell_is_a_no_op():
    feedback = MoveFeedback(500)
    feedback.reject(None)
    assert feedback.flash is None
