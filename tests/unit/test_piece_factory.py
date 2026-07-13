# tests/unit/test_piece_factory.py
from model.piece import Color, PieceKind
from model.position import Position
from text_io.piece_factory import PieceFactory


def test_creates_a_piece_at_the_given_cell():
    piece = PieceFactory().create(Color.WHITE, PieceKind.ROOK, Position(1, 2))
    assert piece.color == Color.WHITE
    assert piece.kind == PieceKind.ROOK
    assert piece.cell == Position(1, 2)


def test_ids_are_unique_and_assigned_in_creation_order():
    factory = PieceFactory()
    first = factory.create(Color.WHITE, PieceKind.KING, Position(0, 0))
    second = factory.create(Color.BLACK, PieceKind.KING, Position(0, 1))
    third = factory.create(Color.WHITE, PieceKind.PAWN, Position(1, 0))
    assert len({first.id, second.id, third.id}) == 3  # all distinct


def test_the_factory_can_create_a_kind_it_has_never_heard_of():
    # Kinds are open: the factory needs no knowledge of which pieces the game has.
    piece = PieceFactory().create(Color.BLACK, PieceKind("dragon"), Position(0, 0))
    assert piece.kind == PieceKind("dragon")
