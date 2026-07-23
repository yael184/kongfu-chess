# input/controller.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ClickOutcome:
    """What a click did, for a surface that wants to react to it (e.g. flash a refused move).

    `result` is the MoveResult of an attempted move (else None, when the click only selected,
    switched or cancelled a selection), and `target` is the cell that move aimed at. Both are None
    for a click that requested no move. It carries data only — deciding what to draw from it is the
    view's job, so the controller still owns no rendering.
    """
    result: object = None
    target: object = None


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

    def handle_click(self, x: int, y: int) -> ClickOutcome:
        """Handle a click; returns a ClickOutcome (its `result`/`target` are None unless a move was
        requested), so a surface can react to a refused move without asking the engine again."""
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
            return ClickOutcome()             # outside-board click ignored when nothing is selected
        if snapshot.piece_at(cell) is None:
            return ClickOutcome()             # ignore first clicks on empty cells
        self._selected = cell                 # select this cell as the move source
        return ClickOutcome()

    def _handle_second_click(self, cell, snapshot):
        if not snapshot.is_within_bounds(cell):
            self._selected = None             # outside-board click cancels the selection, no command
            return ClickOutcome()

        selected_piece = snapshot.piece_at(self._selected)
        if selected_piece is not None and selected_piece.is_ally_of(snapshot.piece_at(cell)):
            self._selected = cell             # clicking a same-color piece switches the selection
            return ClickOutcome()

        source = self._selected
        self._selected = None                 # any move attempt clears the selection (legal or not)
        return ClickOutcome(self._engine.request_move(source, cell), cell)
