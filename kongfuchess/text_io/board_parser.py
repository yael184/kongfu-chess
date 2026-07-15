# text_io/board_parser.py
from kongfuchess.model.board import Board
from kongfuchess.model.position import Position


class BoardParseError(Exception):
    """Raised when the text board cannot be parsed.

    `code` is a stable, machine-readable reason ("ROW_WIDTH_MISMATCH", "UNKNOWN_TOKEN") so
    callers can translate it into whatever error surface they use.
    """
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BoardParser:
    """Builds a model Board from the current text board format.

    Format: one row per line, cells separated by whitespace, each cell either the empty token or a
    two-char <color><symbol> token. Dimensions are inferred from the text. Which tokens are valid
    is the injected codec's business, and ids come from the injected factory — so a new piece needs
    no change here, and neither does a change to the token format.

    This class is one half of "the conversion": it, and BoardPrinter, are the only things that know
    how a board is spelled. If the board's internal representation changes, they are what changes
    with it.
    """

    def __init__(self, piece_factory, codec):
        self._factory = piece_factory
        self._codec = codec

    def parse(self, board_text: str) -> Board:
        """Convert the raw board text into a Board, or raise BoardParseError on malformed input."""
        rows = [line.split() for line in board_text.split("\n") if line.strip()]
        if not rows:
            raise BoardParseError("UNKNOWN_TOKEN")

        width = len(rows[0])
        board = Board(width, len(rows))

        for row_index, row in enumerate(rows):
            if len(row) != width:
                raise BoardParseError("ROW_WIDTH_MISMATCH")
            for col_index, token in enumerate(row):
                if self._codec.is_empty(token):
                    continue
                decoded = self._codec.decode(token)
                if decoded is None:
                    raise BoardParseError("UNKNOWN_TOKEN")
                color, kind = decoded
                board.add_piece(self._factory.create(color, kind, Position(row_index, col_index)))

        return board
