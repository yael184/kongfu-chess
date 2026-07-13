# tests/unit/test_token_codec.py
import config
from model.piece import Color, Piece, PieceKind
from model.position import Position
from text_io.token_codec import TokenCodec, codec_for


def standard_codec():
    cfg = config.load()
    return codec_for(cfg.pieces, cfg.empty_token)


def piece_of(color, kind):
    return Piece(id=1, color=color, kind=kind, cell=Position(0, 0))


def test_decodes_the_configured_tokens():
    codec = standard_codec()
    assert codec.decode("wR") == (Color.WHITE, PieceKind.ROOK)
    assert codec.decode("bK") == (Color.BLACK, PieceKind.KING)


def test_decode_and_encode_round_trip():
    codec = standard_codec()
    for token in ("wK", "bQ", "wR", "bB", "wN", "bP"):
        color, kind = codec.decode(token)
        assert codec.encode(piece_of(color, kind)) == token


def test_invalid_tokens_decode_to_none():
    codec = standard_codec()
    assert codec.decode("wX") is None   # unknown symbol
    assert codec.decode("xK") is None   # unknown color
    assert codec.decode("K") is None    # wrong length


def test_the_empty_token_is_injected():
    codec = TokenCodec({"R": PieceKind.ROOK}, empty_token="_")
    assert codec.is_empty("_") is True
    assert codec.is_empty(".") is False
    assert codec.empty_token == "_"


def test_a_new_piece_brings_its_own_symbol_with_no_code_change():
    # The symbol map is data, not a module-level constant: an unheard-of piece just works.
    codec = TokenCodec({"D": PieceKind("dragon")}, empty_token=".")
    assert codec.decode("wD") == (Color.WHITE, PieceKind("dragon"))
    assert codec.encode(piece_of(Color.BLACK, PieceKind("dragon"))) == "bD"
