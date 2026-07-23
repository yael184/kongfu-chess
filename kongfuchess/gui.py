# gui.py
"""Entry point for the graphical (OpenCV) surface, the visual sibling of main.py's text surface.

Run it with `python -m kongfuchess.gui [board-file] [--white NAME] [--black NAME]`. With no board
argument it loads the starting position named in config; with no name arguments it uses the names
configured under [players]. It only reads config, parses a board and hands off to the composition
root — all wiring lives there. Passing names here is the easy, forward-compatible hook the spec asks
for: a name-entry screen later fills in the same two arguments and nothing else changes.
"""
import argparse
import sys
from pathlib import Path

import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.text_io.board_parser import BoardParseError

WINDOW_TITLE = "Kung Fu Chess"


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="kongfuchess.gui", description="Kung Fu Chess (OpenCV).")
    parser.add_argument("board", nargs="?", default=None,
                        help="board file to load (defaults to the configured starting position)")
    parser.add_argument("--white", default=None, help="name shown for the white player")
    parser.add_argument("--black", default=None, help="name shown for the black player")
    return parser.parse_args(argv)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = _parse_args(argv)
    cfg = config.load()

    board_path = Path(args.board) if args.board else cfg.assets.default_board
    try:
        board = app_factory.build_board_parser(cfg).parse(board_path.read_text(encoding="utf-8"))
    except BoardParseError as error:
        print(f"ERROR {error.code}")
        sys.exit(0)

    app_factory.build_gui_app(board, cfg, WINDOW_TITLE,
                              white_name=args.white, black_name=args.black).run()


if __name__ == "__main__":
    main()
