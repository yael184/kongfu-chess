# tests/unit/test_board_parser.py
import pytest

from model.piece import Color, PieceKind
from model.position import Position
from text_io.board_parser import BoardParser, BoardParseError


def test_parse_infers_dimensions_and_places_pieces():
    board = BoardParser().parse("wK . bK\n. . .")
    assert (board.width, board.height) == (3, 2)
    king = board.piece_at(Position(0, 0))
    assert king.color == Color.WHITE and king.kind == PieceKind.KING
    assert board.piece_at(Position(0, 1)) is None
    assert board.piece_at(Position(0, 2)).color == Color.BLACK


def test_parse_assigns_unique_ids_to_pieces():
    board = BoardParser().parse("wK bK\nwR bR")
    ids = {
        board.piece_at(Position(r, c)).id
        for r in range(board.height) for c in range(board.width)
    }
    assert len(ids) == 4


def test_parse_empty_board_raises_unknown_token():
    with pytest.raises(BoardParseError) as exc:
        BoardParser().parse("   ")
    assert exc.value.code == "UNKNOWN_TOKEN"


def test_parse_row_width_mismatch_raises():
    with pytest.raises(BoardParseError) as exc:
        BoardParser().parse("wK .\n. bK .")
    assert exc.value.code == "ROW_WIDTH_MISMATCH"


def test_parse_unknown_token_raises():
    with pytest.raises(BoardParseError) as exc:
        BoardParser().parse("wK wX\n. bK")
    assert exc.value.code == "UNKNOWN_TOKEN"
