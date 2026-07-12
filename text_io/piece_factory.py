# text_io/piece_factory.py
from model.piece import Piece, Color, PieceKind

# Single source of truth for the token <-> piece correspondence in the text format.
_KIND_BY_SYMBOL = {
    "K": PieceKind.KING,
    "Q": PieceKind.QUEEN,
    "R": PieceKind.ROOK,
    "B": PieceKind.BISHOP,
    "N": PieceKind.KNIGHT,
    "P": PieceKind.PAWN,
}
_SYMBOL_BY_KIND = {kind: symbol for symbol, kind in _KIND_BY_SYMBOL.items()}
_COLOR_BY_PREFIX = {"w": Color.WHITE, "b": Color.BLACK}
_PREFIX_BY_COLOR = {color: prefix for prefix, color in _COLOR_BY_PREFIX.items()}


def decode_token(token):
    """Decode a two-char <color><symbol> token into (Color, PieceKind), or None if invalid."""
    if len(token) != 2:
        return None
    prefix, symbol = token[0], token[1]
    if prefix not in _COLOR_BY_PREFIX or symbol not in _KIND_BY_SYMBOL:
        return None
    return _COLOR_BY_PREFIX[prefix], _KIND_BY_SYMBOL[symbol]


def token_for_piece(piece):
    """Encode a Piece into its two-char text token (e.g. a white rook -> "wR")."""
    return _PREFIX_BY_COLOR[piece.color] + _SYMBOL_BY_KIND[piece.kind]


class PieceFactory:
    """Creates model pieces, assigning a unique, stable id at creation time.

    Ids are handed out in creation order, so identical input produces identical ids and no two
    pieces ever share an id. The factory also owns token decoding for the text format.
    """

    def __init__(self):
        self._next_id = 0

    def create(self, color, kind, cell):
        """Create a Piece of the given color/kind at `cell` with a fresh unique id."""
        self._next_id += 1
        return Piece(id=self._next_id, color=color, kind=kind, cell=cell)

    def create_from_token(self, token, cell):
        """Create a Piece from a text token at `cell`, or return None if the token is invalid."""
        decoded = decode_token(token)
        if decoded is None:
            return None
        color, kind = decoded
        return self.create(color, kind, cell)
