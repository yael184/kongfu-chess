"""The board background: the artwork is tiled so its painted squares line up with the real cells.

A synthetic 8-cell checkerboard stands in for the asset, so this needs no files. The assertions read
cells back out of the frame: a cell must be one solid colour, and neighbours must differ — that is
exactly what a stretched (rather than tiled) background breaks on a board that is not 8x8.
"""
import numpy as np
import pytest

from kongfuchess.view.img import Img
from kongfuchess.view.rendering.board_renderer import BoardRenderer

CELL = 10
IMAGE_CELLS = 8
SQUARE_PX = 16                      # the artwork's own square size, deliberately != CELL

LIGHT = (240, 240, 240)
DARK = (20, 20, 20)


def _checkerboard():
    """An 8x8 checkerboard, 3-channel (so the BGRA conversion is exercised too)."""
    side = IMAGE_CELLS * SQUARE_PX
    art = np.zeros((side, side, 3), dtype=np.uint8)
    for row in range(IMAGE_CELLS):
        for col in range(IMAGE_CELLS):
            colour = LIGHT if (row + col) % 2 == 0 else DARK
            art[row * SQUARE_PX:(row + 1) * SQUARE_PX,
                col * SQUARE_PX:(col + 1) * SQUARE_PX] = colour
    return art


class FakeLoader:
    def read(self, path, size=None, **kwargs):
        image = Img()
        image.img = _checkerboard()
        return image


@pytest.fixture
def renderer():
    return BoardRenderer("ignored.png", CELL, IMAGE_CELLS, image_loader=FakeLoader)


def _cell_colours(frame, row, col):
    """Every distinct colour inside one cell — a single entry means the cell is solid."""
    patch = frame.img[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL, :3]
    return {tuple(pixel) for pixel in patch.reshape(-1, 3)}


def _is_light(frame, row, col):
    (colour,) = _cell_colours(frame, row, col)
    return colour[0] > 128


@pytest.mark.parametrize("width,height", [(8, 8), (4, 4), (3, 5), (12, 10), (1, 1)])
def test_every_cell_is_one_solid_square_of_the_right_size(width, height):
    """The painted squares match the cells at any board size — the bug this fixes."""
    frame = BoardRenderer("x", CELL, IMAGE_CELLS, image_loader=FakeLoader).fresh_frame(width, height)

    assert frame.img.shape == (height * CELL, width * CELL, 4)
    for row in range(height):
        for col in range(width):
            assert len(_cell_colours(frame, row, col)) == 1, f"cell {(row, col)} is not solid"


@pytest.mark.parametrize("width,height", [(4, 4), (12, 10)])
def test_neighbouring_cells_alternate_across_the_whole_board(width, height):
    """Including across a tile seam — an even-celled artwork keeps the alternation going."""
    frame = BoardRenderer("x", CELL, IMAGE_CELLS, image_loader=FakeLoader).fresh_frame(width, height)

    for row in range(height):
        for col in range(width):
            assert _is_light(frame, row, col) == ((row + col) % 2 == 0)


def test_a_board_matching_the_artwork_is_just_the_scaled_artwork(renderer):
    """The standard 8x8 path is unchanged: one tile, no repetition, no crop."""
    frame = renderer.fresh_frame(IMAGE_CELLS, IMAGE_CELLS)
    assert frame.img.shape == (IMAGE_CELLS * CELL, IMAGE_CELLS * CELL, 4)
    assert _is_light(frame, 0, 0)


def test_each_frame_is_a_fresh_copy(renderer):
    """Draws must never compound across frames."""
    first = renderer.fresh_frame(4, 4)
    first.img[:] = 0
    assert _cell_colours(renderer.fresh_frame(4, 4), 0, 0) != {(0, 0, 0)}
