# tests/test_main.py
# בדיקות אינטגרציה ל-parse_input ולזרימת ה-main.
import sys
from io import StringIO

import pytest

import main
from pieces import EmptyCell


# --- parse_input ---
def test_parse_input_valid():
    txt = "Board:\nwK .\n. bK\nCommands:\nprint board"
    board, commands = main.parse_input(txt)
    assert str(board.grid[0][0]) == "wK"
    assert isinstance(board.grid[0][1], EmptyCell)
    assert commands == ["print board"]


def test_parse_input_missing_commands_section_exits():
    with pytest.raises(SystemExit):
        main.parse_input("Board:\nwK .\n. bK")


def test_parse_input_missing_board_section_exits():
    with pytest.raises(SystemExit):
        main.parse_input("Commands:\nprint board")


def test_parse_input_empty_board_exits():
    # אין שורות לוח כלל בין Board: ל-Commands:
    with pytest.raises(SystemExit):
        main.parse_input("Board:\nCommands:\nprint board")


def test_parse_input_row_width_mismatch_exits():
    txt = "Board:\nwK .\n. bK .\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(txt)


def test_parse_input_unknown_token_exits():
    txt = "Board:\nwK wX\n. bK\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(txt)


# --- main (זרימה מלאה) ---
def test_main_execution_flow(capsys):
    input_data = (
        "Board:\n"
        "wK . bK\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"
        "click 150 50\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    assert ". wK bK\n. . ." in out


def test_main_random_text_exits():
    with pytest.raises(SystemExit):
        main.main(input_stream=StringIO("Just random text"))


def test_main_no_commands_prints_error(capsys):
    # לוח תקין אך ללא פקודות -> ההסתעפות 'not commands' ב-main
    input_data = "Board:\nwK\nCommands:\n"
    main.main(input_stream=StringIO(input_data))
    assert "ERROR UNKNOWN_TOKEN" in capsys.readouterr().out


def test_main_reads_from_stdin_by_default(capsys, monkeypatch):
    # כיסוי ההסתעפות שבה input_stream הוא None ונקרא מ-sys.stdin
    input_data = (
        "Board:\n"
        "wK .\n"
        ". .\n"
        "Commands:\n"
        "print board\n"
    )
    monkeypatch.setattr(sys, "stdin", StringIO(input_data))
    main.main()
    assert "wK ." in capsys.readouterr().out
