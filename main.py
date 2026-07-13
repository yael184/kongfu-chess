# main.py
import sys

import config
from composition import app_factory
from text_io.board_parser import BoardParseError
from texttests.script_parser import ScriptParser, ScriptParseError


def main(input_stream=None):
    """Read a Board:/Commands: document, build the game, and run every command."""
    if input_stream is None:
        input_stream = sys.stdin
    text = input_stream.read()

    cfg = config.load()

    try:
        script = ScriptParser().parse(text)
        board = app_factory.build_board_parser(cfg).parse(script.board_text)
    except (ScriptParseError, BoardParseError) as error:
        print(f"ERROR {error.code}")
        sys.exit(0)

    app_factory.build_script_runner(board, cfg).run(script.commands)


if __name__ == "__main__":
    main()
