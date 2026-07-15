# gui.py
"""Entry point for the graphical (OpenCV) surface, the visual sibling of main.py's text surface.

Run it with `python -m kongfuchess.gui [board-file]`. With no argument it loads the starting
position named in config. It only reads config, parses a board and hands off to the composition
root — all wiring lives there.
"""
import sys
from pathlib import Path

import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.text_io.board_parser import BoardParseError

WINDOW_TITLE = "Kung Fu Chess"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cfg = config.load()

    board_path = Path(argv[0]) if argv else cfg.assets.default_board
    try:
        board = app_factory.build_board_parser(cfg).parse(board_path.read_text(encoding="utf-8"))
    except BoardParseError as error:
        print(f"ERROR {error.code}")
        sys.exit(0)

    app_factory.build_gui_app(board, cfg, WINDOW_TITLE).run()


if __name__ == "__main__":
    main()
