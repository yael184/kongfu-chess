# tests/unit/test_board_printer.py
import config
from engine.game_engine import GameEngine
from model.game_state import GameState
from model.piece import PieceKind
from text_io.board_parser import BoardParser
from text_io.board_printer import BoardPrinter
from text_io.piece_factory import PieceFactory
from text_io.token_codec import TokenCodec, codec_for


def standard_codec():
    cfg = config.load()
    return codec_for(cfg.pieces, cfg.empty_token)


def parse(text, codec=None):
    return BoardParser(PieceFactory(), codec or standard_codec()).parse(text)


def test_renders_board_to_text():
    board = parse("wK . bK\n. . .\n. wK .")
    assert BoardPrinter(standard_codec()).to_text(board) == "wK . bK\n. . .\n. wK ."


def test_parse_then_print_round_trips():
    text = "wR . bB\n. . .\n. . ."
    assert BoardPrinter(standard_codec()).to_text(parse(text)) == text


def test_the_token_format_is_injected():
    # Same board, a different codec: the printer owns the layout (spaces, newlines), the codec
    # owns the spelling. Neither knows which pieces exist.
    codec = TokenCodec({"D": PieceKind("dragon")}, empty_token="_")
    board = parse("wD _\n_ _", codec)
    assert BoardPrinter(codec).to_text(board) == "wD _\n_ _"


def test_renders_from_a_snapshot_view():
    # BoardPrinter works on any BoardView, including a GameSnapshot.
    class _NoArbiter:
        def has_active_motion(self):
            return False

    class _NoRules:
        pass

    board = parse("wK . bK\n. . .")
    engine = GameEngine(GameState(board=board), _NoArbiter(), _NoRules())
    assert BoardPrinter(standard_codec()).to_text(engine.snapshot()) == "wK . bK\n. . ."
