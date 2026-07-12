# tests/test_registry.py
# Tests for the factory that converts tokens into piece objects.
import pytest

from registry import create_piece_from_token
from pieces import King, Rook, Bishop, Queen, Knight, Pawn, EmptyCell


def test_empty_token_returns_empty_cell():
    assert isinstance(create_piece_from_token("."), EmptyCell)


@pytest.mark.parametrize(
    "token,expected_cls,expected_color",
    [
        ("wK", King, "WHITE"),
        ("bK", King, "BLACK"),
        ("wR", Rook, "WHITE"),
        ("bB", Bishop, "BLACK"),
        ("wQ", Queen, "WHITE"),
        ("bN", Knight, "BLACK"),
        ("wP", Pawn, "WHITE"),
    ],
)
def test_valid_tokens_build_correct_piece(token, expected_cls, expected_color):
    piece = create_piece_from_token(token)
    assert isinstance(piece, expected_cls)
    assert piece.color == expected_color


@pytest.mark.parametrize("token", ["K", "wKx", "", "wKKK"])
def test_wrong_length_token_returns_none(token):
    assert create_piece_from_token(token) is None


def test_invalid_color_prefix_returns_none():
    assert create_piece_from_token("xK") is None


def test_valid_color_invalid_symbol_returns_none():
    assert create_piece_from_token("wZ") is None
