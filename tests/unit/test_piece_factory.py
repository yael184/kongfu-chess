# tests/unit/test_piece_factory.py
from model.piece import Color, PieceKind
from model.position import Position
from text_io.piece_factory import PieceFactory, decode_token, token_for_piece


def test_creates_piece_from_token():
    piece = PieceFactory().create_from_token("wR", Position(1, 2))
    assert piece.color == Color.WHITE
    assert piece.kind == PieceKind.ROOK
    assert piece.cell == Position(1, 2)


def test_ids_are_unique_and_assigned_in_creation_order():
    factory = PieceFactory()
    first = factory.create_from_token("wK", Position(0, 0))
    second = factory.create_from_token("bK", Position(0, 1))
    third = factory.create(Color.WHITE, PieceKind.PAWN, Position(1, 0))
    ids = {first.id, second.id, third.id}
    assert len(ids) == 3  # all distinct


def test_invalid_tokens_return_none():
    factory = PieceFactory()
    assert factory.create_from_token("wX", Position(0, 0)) is None   # unknown symbol
    assert factory.create_from_token("xK", Position(0, 0)) is None   # unknown color
    assert factory.create_from_token("K", Position(0, 0)) is None    # wrong length


def test_decode_and_encode_round_trip():
    for token in ("wK", "bQ", "wR", "bB", "wN", "bP"):
        color, kind = decode_token(token)
        piece = PieceFactory().create(color, kind, Position(0, 0))
        assert token_for_piece(piece) == token
