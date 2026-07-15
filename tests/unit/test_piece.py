# tests/unit/test_piece.py
import dataclasses

from kongfuchess.model.piece import Piece, Color, PieceKind, PieceState
from kongfuchess.model.position import Position


def test_piece_holds_its_fields():
    piece = Piece(id="p1", color=Color.WHITE, kind=PieceKind.KING, cell=Position(0, 0))
    assert piece.id == "p1"
    assert piece.color == Color.WHITE
    assert piece.kind == PieceKind.KING
    assert piece.cell == Position(0, 0)


def test_piece_defaults_to_idle_state():
    piece = Piece(id="p1", color=Color.WHITE, kind=PieceKind.PAWN, cell=Position(1, 1))
    assert piece.state == PieceState.IDLE


def test_piece_state_is_a_mutable_lifecycle_flag():
    piece = Piece(id="p1", color=Color.BLACK, kind=PieceKind.ROOK, cell=Position(2, 2))
    piece.state = PieceState.MOVING
    assert piece.state == PieceState.MOVING
    piece.state = PieceState.CAPTURED
    assert piece.state == PieceState.CAPTURED


def test_piece_has_readable_repr():
    piece = Piece(id="p1", color=Color.WHITE, kind=PieceKind.QUEEN, cell=Position(0, 0))
    text = repr(piece)
    assert "p1" in text
    assert "queen" in text


def test_piece_exposes_only_lifecycle_fields():
    # Locks the surface: no path, destination, elapsed time, speed, or interpolation on Piece.
    names = {field.name for field in dataclasses.fields(Piece)}
    assert names == {"id", "color", "kind", "cell", "state"}
