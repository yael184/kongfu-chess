# tests/integration/test_custom_game.py
"""The acceptance test for the whole decoupling exercise.

Each test here invents a game that is *not* the chess this codebase was written for — a piece that
has never existed, a promotion into something else, a different way to win — and plays it end to
end through the real stack: parser, engine, rules, real-time arbiter, printer.

Every one of them is defined entirely in a config file. Not a line of production code outside
config.toml is involved in adding them, which is the property the architecture is supposed to have.
"""
import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.model.piece import PieceKind
from kongfuchess.model.position import Position
from kongfuchess.texttests.script_runner import ScriptRunner

# A game with a piece that does not exist in chess: the "dragon", which leaps two cells sideways
# or downwards, over anything in the way. Nothing in model/, rules/, realtime/, engine/, input/ or
# text_io/ has ever heard of it.
DRAGON_GAME = """
[board]
cell_size = 100
[timing]
ms_per_cell = 1000
jump_duration_ms = 1000
[tokens]
empty = "."

[[pieces]]
name = "dragon"
symbol = "D"
movement = "leap"
offsets = [[0, 2], [0, -2], [2, 0], [-2, 0]]

[[pieces]]
name = "king"
symbol = "K"
movement = "leap"
offsets = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]
victory_on_capture = true
"""


def write_config(tmp_path, text):
    path = tmp_path / "custom.toml"
    path.write_text(text)
    return config.load(path)


def play(cfg, board_text, commands):
    """Run a board and a command list through the real stack, exactly as main.py does."""
    board = app_factory.build_board_parser(cfg).parse(board_text)
    engine = app_factory.build_engine(board, cfg)
    controller = app_factory.build_controller(engine, cfg)
    table = app_factory.build_command_table(engine, controller, app_factory.build_printer(cfg))
    ScriptRunner(table).run(commands)
    return engine, board


def test_a_piece_that_does_not_exist_in_chess_is_pure_configuration(tmp_path):
    cfg = write_config(tmp_path, DRAGON_GAME)
    # The dragon at (0,0) leaps two cells right onto the enemy king, straight over the piece between.
    engine, board = play(cfg, "wD wD bK\n. . .", ["click 50 50", "click 250 50", "wait 2000"])

    assert board.piece_at(Position(0, 2)).kind == PieceKind("dragon")   # it landed
    assert engine.snapshot().game_over is True                          # taking the king still wins


def test_the_new_piece_round_trips_through_the_text_format(tmp_path):
    cfg = write_config(tmp_path, DRAGON_GAME)
    text = "wD . bK\n. . ."
    board = app_factory.build_board_parser(cfg).parse(text)
    assert app_factory.build_printer(cfg).to_text(board) == text


def test_a_rule_change_alone_changes_the_game(tmp_path):
    """Same pieces, one config edit: pawns now promote to a rook, not a queen."""
    cfg = write_config(tmp_path, """
[board]
cell_size = 100
[timing]
ms_per_cell = 1000
jump_duration_ms = 1000
[tokens]
empty = "."

[[pieces]]
name = "rook"
symbol = "R"
movement = "slide"
directions = [[0, 1], [0, -1], [1, 0], [-1, 0]]

[[pieces]]
name = "pawn"
symbol = "P"
movement = "pawn"
promotes_to = "rook"
""")
    engine, board = play(cfg, ". . .\n. wP .\n. . .", ["click 150 150", "click 150 50", "wait 1000"])

    assert board.piece_at(Position(0, 1)).kind == PieceKind("rook")   # not a queen


def test_the_victory_condition_is_configuration(tmp_path):
    """A game won by capturing the *rook*. Nothing in engine/ or realtime/ knows about kings."""
    cfg = write_config(tmp_path, """
[board]
cell_size = 100
[timing]
ms_per_cell = 1000
jump_duration_ms = 1000
[tokens]
empty = "."

[[pieces]]
name = "rook"
symbol = "R"
movement = "slide"
directions = [[0, 1], [0, -1], [1, 0], [-1, 0]]
victory_on_capture = true

[[pieces]]
name = "king"
symbol = "K"
movement = "leap"
offsets = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]
""")
    # A king takes a rook -> the game ends, because in *this* game the rook is the prize.
    engine, board = play(cfg, "wK bR .\n. . .", ["click 50 50", "click 150 50", "wait 1000"])

    assert board.piece_at(Position(0, 1)).kind == PieceKind("king")
    assert engine.snapshot().game_over is True


def test_a_piece_can_be_composed_from_two_existing_patterns(tmp_path):
    """An archbishop — bishop plus knight — with no new code: `combined` unions the two patterns."""
    cfg = write_config(tmp_path, """
[board]
cell_size = 100
[timing]
ms_per_cell = 1000
jump_duration_ms = 1000
[tokens]
empty = "."

[[pieces]]
name = "archbishop"
symbol = "A"
movement = "combined"
directions = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
offsets = [[2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [1, -2], [-1, 2], [-1, -2]]
""")
    rules = app_factory.build_rules(cfg)
    board = app_factory.build_board_parser(cfg).parse("wA . .\n. . .\n. . .")
    archbishop = board.piece_at(Position(0, 0))
    destinations = rules.legal_destinations(board, archbishop)

    assert Position(1, 1) in destinations   # the bishop half
    assert Position(2, 2) in destinations
    assert Position(1, 2) in destinations   # the knight half
    assert Position(2, 1) in destinations
    assert Position(0, 1) not in destinations   # it is neither a rook nor a king
