# text_io/token_codec.py
from model.piece import Color, PieceKind

# Colors are a genuinely closed set — a piece belongs to one of two sides — so unlike piece kinds
# they stay an enum, and their prefixes stay here.
_COLOR_BY_PREFIX = {"w": Color.WHITE, "b": Color.BLACK}
_PREFIX_BY_COLOR = {color: prefix for prefix, color in _COLOR_BY_PREFIX.items()}


class TokenCodec:
    """The single source of truth for the `<color><symbol>` token format.

    The symbol for each piece kind is injected (built from config.toml's [[pieces]]), so a new
    piece brings its own token along with it: nothing here is edited, and no module-level map has
    to learn about it. This class is the only thing in the codebase that knows a piece can be
    spelled as text at all.
    """

    def __init__(self, kind_by_symbol, empty_token):
        self._kind_by_symbol = dict(kind_by_symbol)
        self._symbol_by_kind = {kind: symbol for symbol, kind in self._kind_by_symbol.items()}
        self._empty_token = empty_token

    @property
    def empty_token(self) -> str:
        return self._empty_token

    def is_empty(self, token) -> bool:
        return token == self._empty_token

    def decode(self, token):
        """Decode a two-char <color><symbol> token into (Color, PieceKind), or None if invalid."""
        if len(token) != 2:
            return None
        prefix, symbol = token[0], token[1]
        if prefix not in _COLOR_BY_PREFIX or symbol not in self._kind_by_symbol:
            return None
        return _COLOR_BY_PREFIX[prefix], self._kind_by_symbol[symbol]

    def encode(self, piece) -> str:
        """Encode a Piece into its two-char text token (e.g. a white rook -> "wR")."""
        return _PREFIX_BY_COLOR[piece.color] + self._symbol_by_kind[piece.kind]


def codec_for(specs, empty_token) -> TokenCodec:
    """Build the codec for the configured pieces: each spec carries its own symbol."""
    return TokenCodec({spec.symbol: PieceKind(spec.name) for spec in specs}, empty_token)
