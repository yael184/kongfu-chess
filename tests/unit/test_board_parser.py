# tests/unit/test_board_parser.py
import pytest

import config
from model.piece import Color, PieceKind
from model.position import Position
from text_io.board_parser import BoardParser, BoardParseError
from text_io.piece_factory import PieceFactory
from text_io.token_codec import TokenCodec, codec_for


def parser(codec=None):
    """A parser with its collaborators injected: no ambient factory, no global token format."""
    cfg = config.load()
    return BoardParser(PieceFactory(), codec or codec_for(cfg.pieces, cfg.empty_token))


def test_parse_infers_dimensions_and_places_pieces():
    board = parser().parse("wK . bK\n. . .")
    assert (board.width, board.height) == (3, 2)
    king = board.piece_at(Position(0, 0))
    assert king.color == Color.WHITE and king.kind == PieceKind.KING
    assert board.piece_at(Position(0, 1)) is None
    assert board.piece_at(Position(0, 2)).color == Color.BLACK


def test_parse_assigns_unique_ids_to_pieces():
    board = parser().parse("wK bK\nwR bR")
    assert len({piece.id for piece in board.pieces()}) == 4


def test_the_token_format_is_injected():
    # A codec with its own symbols and its own empty token: the parser learns the format from it,
    # so a piece it has never heard of parses without a line changing here.
    codec = TokenCodec({"D": PieceKind("dragon")}, empty_token="_")
    board = parser(codec).parse("wD _\n_ bD")
    assert board.piece_at(Position(0, 1)) is None
    assert board.piece_at(Position(1, 1)).kind == PieceKind("dragon")


def test_parse_empty_board_raises_unknown_token():
    with pytest.raises(BoardParseError) as exc:
        parser().parse("   ")
    assert exc.value.code == "UNKNOWN_TOKEN"


def test_parse_row_width_mismatch_raises():
    with pytest.raises(BoardParseError) as exc:
        parser().parse("wK .\n. bK .")
    assert exc.value.code == "ROW_WIDTH_MISMATCH"


def test_parse_unknown_token_raises():
    with pytest.raises(BoardParseError) as exc:
        parser().parse("wK wX\n. bK")
    assert exc.value.code == "UNKNOWN_TOKEN"
