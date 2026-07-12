# tests/unit/test_board_printer.py
from text_io.board_parser import BoardParser
from text_io.board_printer import BoardPrinter


def test_renders_board_to_text():
    board = BoardParser().parse("wK . bK\n. . .\n. wK .")
    expected = "wK . bK\n. . .\n. wK ."
    assert BoardPrinter().to_text(board) == expected


def test_parse_then_print_round_trips():
    text = "wR . bB\n. . .\n. . ."
    board = BoardParser().parse(text)
    assert BoardPrinter().to_text(board) == text


def test_renders_from_a_snapshot_view():
    # BoardPrinter works on any view with width/height/piece_at, including a GameSnapshot.
    from engine.game_engine import GameEngine
    from model.game_state import GameState

    class _NoArbiter:
        def has_active_motion(self):
            return False

    board = BoardParser().parse("wK . bK\n. . .")
    snapshot = GameEngine(GameState(board=board), _NoArbiter()).snapshot()
    assert BoardPrinter().to_text(snapshot) == "wK . bK\n. . ."
