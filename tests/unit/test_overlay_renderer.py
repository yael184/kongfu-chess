"""The overlays: legal-move targets and the draining cooldown square, drawn on a real Img.

No window and no assets — a blank BGRA canvas stands in for the frame, and the assertions read the
pixels back, so the geometry (which cell, which part of it) is checked rather than mocked.
"""
import numpy as np
import pytest

from kongfuchess.model.position import Position
from kongfuchess.realtime.motion import RestView
from kongfuchess.view.img import Img
from kongfuchess.view.rendering.overlay_renderer import OverlayRenderer
from kongfuchess.view.rendering.view_state import ViewState

CELL = 40


class FakeSnapshot:
    game_over = False


@pytest.fixture
def frame():
    canvas = Img()
    canvas.img = np.zeros((CELL * 8, CELL * 8, 4), dtype=np.uint8)
    canvas.img[..., 3] = 255
    return canvas


def _state(**kwargs):
    return ViewState(snapshot=FakeSnapshot(), **kwargs)


def _is_painted(frame, row, col, row_offset):
    """Whether the pixel `row_offset` rows into that cell has any colour on it."""
    return frame.img[row * CELL + row_offset, col * CELL + CELL // 2, :3].any()


def test_legal_targets_shade_their_whole_cell(frame):
    OverlayRenderer(CELL).draw(frame, _state(targets=(Position(3, 4),)))

    assert _is_painted(frame, 3, 4, 1)                  # top of the cell
    assert _is_painted(frame, 3, 4, CELL - 2)           # bottom of the cell
    assert not _is_painted(frame, 3, 5, CELL // 2)      # the neighbour is untouched


def test_a_full_cooldown_covers_the_whole_cell(frame):
    OverlayRenderer(CELL).draw(frame, _state(rests=(RestView(Position(2, 2), 1.0),)))

    assert _is_painted(frame, 2, 2, 1)
    assert _is_painted(frame, 2, 2, CELL - 2)


def test_a_cooldown_empties_from_the_top_down(frame):
    """Half-elapsed: the top half is clear and the remaining yellow sits at the bottom."""
    OverlayRenderer(CELL).draw(frame, _state(rests=(RestView(Position(2, 2), 0.5),)))

    assert not _is_painted(frame, 2, 2, 1)             # drained from the top
    assert not _is_painted(frame, 2, 2, CELL // 2 - 2)
    assert _is_painted(frame, 2, 2, CELL // 2 + 2)     # what is left is at the bottom
    assert _is_painted(frame, 2, 2, CELL - 2)


def test_an_expired_cooldown_draws_nothing(frame):
    OverlayRenderer(CELL).draw(frame, _state(rests=(RestView(Position(2, 2), 0.0),)))

    assert not frame.img[..., :3].any()


def test_the_shading_is_translucent_not_opaque(frame):
    """The piece underneath must stay visible — the overlay tints, it does not hide."""
    frame.img[..., :3] = 200                           # a "piece" already drawn
    OverlayRenderer(CELL).draw(frame, _state(targets=(Position(0, 0),)))

    tinted = frame.img[CELL // 2, CELL // 2, :3]
    assert tinted[2] not in (0, 200)                   # blended with the original, not replaced


def test_the_frames_alpha_is_left_intact(frame):
    OverlayRenderer(CELL).draw(frame, _state(rests=(RestView(Position(1, 1), 1.0),)))

    assert (frame.img[..., 3] == 255).all()
