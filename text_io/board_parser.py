# text_io/board_parser.py
import config
from model.board import Board
from model.position import Position
from text_io.piece_factory import PieceFactory


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

    Format: one row per line, cells separated by whitespace, each cell either the empty token
    or a two-char <color><symbol> token. Dimensions are inferred from the text. Pieces get
    stable ids from a PieceFactory. This class is specific to this text format.
    """

    def __init__(self, piece_factory=None):
        self._factory = piece_factory if piece_factory is not None else PieceFactory()

    def parse(self, board_text: str) -> Board:
        """Convert the raw board text into a Board, or raise BoardParseError on malformed input."""
        rows = [line.split() for line in board_text.split("\n") if line.strip()]
        if not rows:
            raise BoardParseError("UNKNOWN_TOKEN")

        width = len(rows[0])
        height = len(rows)
        board = Board(width, height)

        for row_index, row in enumerate(rows):
            if len(row) != width:
                raise BoardParseError("ROW_WIDTH_MISMATCH")
            for col_index, token in enumerate(row):
                if token == config.EMPTY_TOKEN:
                    continue
                piece = self._factory.create_from_token(token, Position(row_index, col_index))
                if piece is None:
                    raise BoardParseError("UNKNOWN_TOKEN")
                board.add_piece(piece)

        return board
