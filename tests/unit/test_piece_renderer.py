"""PieceRenderer's sprite bookkeeping: which sprites it asks the library for, and when.

A fake library records every (kind, color, state) request and returns single-frame clips, so this
runs with no assets and no window. The point of interest is promotion: the piece keeps its id and
gains a new kind, and the drawn sprite must follow.
"""
from kongfuchess.model.piece import Color, Piece, PieceKind, PieceState
from kongfuchess.model.position import Position
from kongfuchess.view.rendering.piece_renderer import PieceRenderer

CELL = 10
STATE_FOLDERS = {
    PieceState.IDLE: "idle",
    PieceState.MOVING: "move",
    PieceState.JUMPING: "jump",
    PieceState.SHORT_REST: "idle",
    PieceState.LONG_REST: "idle",
}


class FakeFrame:
    def __init__(self, label):
        self.label = label

    def draw_on(self, frame, x, y):
        frame.drawn.append((self.label, x, y))


class FakeClip:
    """Stands in for a SpriteState: one frame, never finishes, remembers its own name."""

    def __init__(self, kind, color, state_name):
        self.name = state_name
        self.next_state_when_finished = None
        self._frame = FakeFrame(f"{kind.name}-{color.name}-{state_name}")

    def reset(self):
        pass

    def advance(self, dt_ms):
        pass

    @property
    def is_finished(self):
        return False

    @property
    def current_frame(self):
        return self._frame


class FakeLibrary:
    def __init__(self):
        self.requests = []

    def state_for(self, kind, color, state_name):
        self.requests.append((kind, color, state_name))
        return FakeClip(kind, color, state_name)


class FakeFrameBuffer:
    def __init__(self):
        self.drawn = []


class FakeSnapshot:
    def __init__(self, *pieces):
        self._pieces = pieces

    def pieces(self):
        return self._pieces


def _renderer():
    library = FakeLibrary()
    return library, PieceRenderer(library, CELL, STATE_FOLDERS)


def _draw(renderer, *pieces):
    frame = FakeFrameBuffer()
    renderer.draw(frame, FakeSnapshot(*pieces), motions=(), dt_ms=16)
    return frame.drawn


def test_a_promoted_pawn_is_drawn_with_the_new_kinds_sprite():
    pawn = Piece(id="p1", color=Color.WHITE, kind=PieceKind.PAWN, cell=Position(1, 0))
    library, renderer = _renderer()

    assert _draw(renderer, pawn) == [("pawn-WHITE-idle", 0, CELL)]

    pawn.kind = PieceKind.QUEEN            # what TransformPiece does on promotion: same piece object
    pawn.cell = Position(0, 0)

    assert _draw(renderer, pawn) == [("queen-WHITE-idle", 0, 0)]
    assert (PieceKind.QUEEN, Color.WHITE, "idle") in library.requests


def test_the_pawns_sprite_is_retired_once_it_has_promoted():
    pawn = Piece(id="p1", color=Color.WHITE, kind=PieceKind.PAWN, cell=Position(1, 0))
    library, renderer = _renderer()
    _draw(renderer, pawn)
    pawn.kind = PieceKind.QUEEN
    _draw(renderer, pawn)
    _draw(renderer, pawn)

    assert len(renderer._sprites) == 1     # the stale pawn entry is not kept around

    kinds_asked = [kind for kind, _, _ in library.requests]
    assert kinds_asked.count(PieceKind.QUEEN) == 1   # and the queen's sprite is built once, not per frame


def test_an_unchanged_piece_keeps_its_sprite_across_frames():
    """The animation clock must persist — a fresh sprite every frame would restart the animation."""
    rook = Piece(id="r1", color=Color.BLACK, kind=PieceKind.ROOK, cell=Position(0, 0))
    library, renderer = _renderer()
    _draw(renderer, rook)
    _draw(renderer, rook)
    _draw(renderer, rook)

    assert len(library.requests) == 1


def test_a_captured_piece_is_not_drawn():
    rook = Piece(id="r1", color=Color.BLACK, kind=PieceKind.ROOK, cell=Position(0, 0))
    rook.state = PieceState.CAPTURED
    _, renderer = _renderer()

    assert _draw(renderer, rook) == []
