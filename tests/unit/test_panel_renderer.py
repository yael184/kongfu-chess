"""PanelRenderer composites the board frame into a wider canvas and draws the panel. Headless: it
builds its own in-memory board frame, no assets or window."""
import numpy as np

from kongfuchess.view.img import Img
from kongfuchess.view.rendering.panel_renderer import PanelRenderer


class FakeScore:
    score = {"white": 3, "black": 5}
    lead = -2


class FakeLog:
    entries = {"white": [(1000, "N b1-c3")], "black": [(2000, "P e7-e5")]}


def board_frame(width=800, height=800):
    frame = Img()
    frame.img = np.zeros((height, width, 4), dtype=np.uint8)
    frame.img[:, :, 3] = 255
    return frame


def panel():
    return PanelRenderer(300, "White", "Black", FakeScore(), FakeLog())


def test_compose_widens_the_canvas_by_the_panel_width():
    out = panel().compose(board_frame(800, 800))
    assert out.img.shape == (800, 1100, 4)


def test_the_composite_is_fully_opaque():
    out = panel().compose(board_frame())
    assert (out.img[:, :, 3] == 255).all()


def test_the_board_region_is_preserved_from_the_frame():
    frame = board_frame()
    frame.img[10, 20] = (111, 122, 133, 255)      # a marker pixel on the board
    out = panel().compose(frame)
    assert tuple(out.img[10, 20][:3]) == (111, 122, 133)
