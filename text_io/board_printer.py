# text_io/board_printer.py


class BoardPrinter:
    """Renders a board view to the current text format: cells space-separated, rows newline-
    separated. Empty cells render as the codec's empty token.

    It works on any BoardView — a model Board or a GameSnapshot — and asks the view to lay itself
    out via rows() rather than walking the grid coordinate by coordinate, so the board's structure
    stays entirely inside model/. How a piece is spelled is the injected codec's business. This
    class owns only the arrangement: spaces between cells, newlines between rows.
    """

    def __init__(self, codec):
        self._codec = codec

    def to_text(self, view) -> str:
        """Return the view as a single text block in the current format."""
        return "\n".join(
            " ".join(self._codec.empty_token if piece is None else self._codec.encode(piece)
                     for piece in row)
            for row in view.rows()
        )
