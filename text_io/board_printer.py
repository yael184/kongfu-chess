# text_io/board_printer.py
import config
from model.position import Position
from text_io.piece_factory import token_for_piece


class BoardPrinter:
    """Renders a board view to the current text format: cells space-separated, rows newline-
    separated. Empty cells render as the config empty token.

    It works on any read-only view exposing width, height, and piece_at(position) — a model
    Board or a GameSnapshot — so the core stays unaware of how it is displayed.
    """

    def to_text(self, view) -> str:
        """Return the view as a single text block in the current format."""
        rows = []
        for row in range(view.height):
            cells = []
            for col in range(view.width):
                piece = view.piece_at(Position(row, col))
                cells.append(config.EMPTY_TOKEN if piece is None else token_for_piece(piece))
            rows.append(" ".join(cells))
        return "\n".join(rows)
