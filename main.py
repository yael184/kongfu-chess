# main.py
import sys

from engine.game_engine import GameEngine
from input.controller import Controller
from model.game_state import GameState
from realtime.real_time_arbiter import RealTimeArbiter
from text_io.board_parser import BoardParser, BoardParseError
from text_io.board_printer import BoardPrinter
from texttests.script_parser import ScriptParser, ScriptParseError
from texttests.script_runner import ScriptRunner


def build_engine(board):
    """Wire the full stack around a parsed board: state + arbiter + engine."""
    return GameEngine(GameState(board=board), RealTimeArbiter())


def main(input_stream=None):
    """Read a Board:/Commands: document, build the game, and run every command."""
    if input_stream is None:
        input_stream = sys.stdin
    text = input_stream.read()

    try:
        script = ScriptParser().parse(text)
        board = BoardParser().parse(script.board_text)
    except (ScriptParseError, BoardParseError) as error:
        print(f"ERROR {error.code}")
        sys.exit(0)

    engine = build_engine(board)
    controller = Controller(engine)
    runner = ScriptRunner(engine, controller, BoardPrinter())
    runner.run(script.commands)


if __name__ == "__main__":
    main()
