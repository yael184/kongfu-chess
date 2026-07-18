"""The mouse-coordinate translation for the resizable window — pure math, no window opened."""
from kongfuchess.view.rendering.cv2_renderer import scale_point


def test_a_click_in_a_shrunken_window_maps_up_to_canvas_pixels():
    # Window shown at 400x400, board canvas 800x800: a click at (100,100) is (200,200) on the board.
    assert scale_point(100, 100, 400, 400, 800, 800) == (200, 200)


def test_a_click_in_an_enlarged_window_maps_down_to_canvas_pixels():
    assert scale_point(400, 400, 1600, 1600, 800, 800) == (200, 200)


def test_identity_when_the_window_is_shown_at_canvas_size():
    assert scale_point(53, 61, 800, 800, 800, 800) == (53, 61)


def test_a_degenerate_window_size_falls_back_to_passthrough():
    assert scale_point(10, 20, 0, 0, 800, 800) == (10, 20)
