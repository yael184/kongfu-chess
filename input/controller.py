# input/controller.py


class Controller:
    """Translates user clicks into GameEngine commands. It decides no chess legality.

    It maps pixels to cells (via BoardMapper), tracks the selected source cell, and on the
    second click delegates to GameEngine.request_move. It never calls Board.move_piece and
    never consults the rules; bounds and occupancy are read from GameEngine.snapshot().

    Selection policy:
      - First click: ignore clicks outside the board and clicks on empty cells; otherwise select.
      - Second click on a same-color piece: switch the selection to it (no command).
      - Second click, inside the board: send request_move and clear the selection (legal or not).
      - Second click, outside the board: cancel the selection and send no command.
    """

    def __init__(self, engine, mapper):
        self._engine = engine
        self._mapper = mapper
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def handle_click(self, x: int, y: int):
        """Handle a click; returns the MoveResult when a move was requested, otherwise None."""
        cell = self._mapper.to_cell(x, y)
        snapshot = self._engine.snapshot()
        if self._selected is None:
            return self._handle_first_click(cell, snapshot)
        return self._handle_second_click(cell, snapshot)

    def handle_jump(self, x: int, y: int):
        """Handle a jump command: the piece on the clicked cell jumps in place (a dodge)."""
        self._engine.request_jump(self._mapper.to_cell(x, y))

    def _handle_first_click(self, cell, snapshot):
        if not snapshot.is_within_bounds(cell):
            return None                       # outside-board click ignored when nothing is selected
        if snapshot.piece_at(cell) is None:
            return None                       # ignore first clicks on empty cells
        self._selected = cell                 # select this cell as the move source
        return None

    def _handle_second_click(self, cell, snapshot):
        if not snapshot.is_within_bounds(cell):
            self._selected = None             # outside-board click cancels the selection, no command
            return None

        selected_piece = snapshot.piece_at(self._selected)
        if selected_piece is not None and selected_piece.is_ally_of(snapshot.piece_at(cell)):
            self._selected = cell             # clicking a same-color piece switches the selection
            return None

        source = self._selected
        self._selected = None                 # any move attempt clears the selection (legal or not)
        return self._engine.request_move(source, cell)
