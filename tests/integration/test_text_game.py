# tests/integration/test_text_game.py
# End-to-end through main(): parse a Board:/Commands: document and run it on the new stack.
from io import StringIO

import kongfuchess.main as main


def run(document):
    main.main(input_stream=StringIO(document))


def test_move_takes_time_and_print_board_reflects_arrival(capsys):
    document = (
        "Board:\n"
        "wR . .\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"     # select the rook at (0,0)
        "click 50 250\n"    # move to (2,0): distance 2 -> 2000 ms
        "print board\n"     # still in flight -> shown at the origin
        "wait 2000\n"       # arrival
        "print board\n"     # now at the destination
    )
    run(document)
    out = capsys.readouterr().out
    assert "wR . .\n. . .\n. . ." in out   # before arrival
    assert ". . .\n. . .\nwR . ." in out   # after arrival


def test_capturing_the_king_freezes_the_board(capsys):
    document = (
        "Board:\n"
        "wR . bK\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"     # select white rook (0,0)
        "click 250 50\n"    # move to the black king at (0,2): 2 cells -> 2000 ms
        "wait 2000\n"       # captures the king -> game over
        "click 250 50\n"    # further clicks are ignored (game over)
        "click 50 50\n"
        "wait 2000\n"
        "print board\n"
    )
    run(document)
    out = capsys.readouterr().out
    assert ". . wR\n. . .\n. . ." in out   # rook took the king's cell; nothing else moved


def test_missing_sections_prints_error():
    import pytest
    with pytest.raises(SystemExit):
        run("just some text with no markers")


def test_unknown_command_reports_error(capsys):
    document = "Board:\nwK\nCommands:\nteleport 1 2\n"
    run(document)
    assert "ERROR: Unknown command" in capsys.readouterr().out
