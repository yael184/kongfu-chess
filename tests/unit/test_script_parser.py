# tests/unit/test_script_parser.py
import pytest

from kongfuchess.texttests.script_parser import ScriptParser, ScriptParseError


def test_splits_board_section_and_commands():
    text = "Board:\nwK . bK\n. . .\nCommands:\nclick 50 50\nwait 1000\nprint board"
    script = ScriptParser().parse(text)
    assert script.board_text == "wK . bK\n. . ."
    assert script.commands == ["click 50 50", "wait 1000", "print board"]


def test_missing_commands_marker_raises():
    with pytest.raises(ScriptParseError) as exc:
        ScriptParser().parse("Board:\nwK . bK")
    assert exc.value.code == "UNKNOWN_TOKEN"


def test_missing_board_marker_raises():
    with pytest.raises(ScriptParseError) as exc:
        ScriptParser().parse("Commands:\nprint board")
    assert exc.value.code == "UNKNOWN_TOKEN"


def test_blank_command_lines_are_dropped():
    script = ScriptParser().parse("Board:\nwK\nCommands:\n\nwait 5\n\n")
    assert script.commands == ["wait 5"]
