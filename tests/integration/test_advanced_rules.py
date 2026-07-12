# tests/integration/test_advanced_rules.py
# End-to-end coverage of the advanced rules through main(): selection switch, pawn two-step,
# promotion, and jump/dodge. Mirrors the external text-test scenarios.
from io import StringIO

import main


def run(document):
    main.main(input_stream=StringIO(document))


def output(capsys):
    return capsys.readouterr().out.strip()


def test_clicking_another_piece_replaces_selection(capsys):
    run("Board:\nwR . wK\n. . .\nCommands:\n"
        "click 50 50\nclick 250 50\nclick 250 150\nwait 1000\nprint board\n")
    assert output(capsys) == "wR . .\n. . wK"


def test_white_pawn_double_from_start(capsys):
    run("Board:\n. . .\n. . .\n. . .\n. wP .\n. . .\nCommands:\n"
        "click 150 350\nclick 150 150\nwait 2000\nprint board\n")
    assert output(capsys) == ". . .\n. wP .\n. . .\n. . .\n. . ."


def test_black_pawn_double_from_start(capsys):
    run("Board:\n. . .\n. bP .\n. . .\n. . .\n. . .\nCommands:\n"
        "click 150 150\nclick 150 350\nwait 2000\nprint board\n")
    assert output(capsys) == ". . .\n. . .\n. . .\n. bP .\n. . ."


def test_white_pawn_promotes_to_queen(capsys):
    run("Board:\n. . .\n. wP .\nCommands:\nclick 150 150\nclick 150 50\nwait 1000\nprint board\n")
    assert output(capsys) == ". wQ .\n. . ."


def test_black_pawn_promotes_to_queen(capsys):
    run("Board:\n. bP .\n. . .\nCommands:\nclick 150 50\nclick 150 150\nwait 1000\nprint board\n")
    assert output(capsys) == ". . .\n. bQ ."


def test_promoted_queen_moves_diagonally(capsys):
    run("Board:\n. . .\n. wP .\n. . .\nCommands:\n"
        "click 150 150\nclick 150 50\nwait 1000\nclick 150 50\nclick 250 150\nwait 1000\nprint board\n")
    assert output(capsys) == ". . .\n. . wQ\n. . ."


def test_jump_lands_same_square(capsys):
    run("Board:\n. . .\n. wK .\n. . .\nCommands:\njump 150 150\nwait 1000\nprint board\n")
    assert output(capsys) == ". . .\n. wK .\n. . ."


def test_airborne_piece_captures_arriving_enemy(capsys):
    run("Board:\n. . .\nwK bR .\n. . .\nCommands:\n"
        "jump 50 150\nclick 150 150\nclick 50 150\nwait 1000\nprint board\n")
    assert output(capsys) == ". . .\nwK . .\n. . ."


def test_enemy_arrives_after_landing_captures_normally(capsys):
    run("Board:\n. . . .\nwK . . bR\n. . . .\nCommands:\n"
        "jump 50 150\nwait 1000\nclick 350 150\nclick 50 150\nwait 3000\nprint board\n")
    assert output(capsys) == ". . . .\nbR . . .\n. . . ."


def test_cannot_jump_while_moving(capsys):
    run("Board:\nwR . .\nCommands:\n"
        "click 50 50\nclick 250 50\nwait 500\njump 50 50\nwait 1500\nprint board\n")
    assert output(capsys) == ". . wR"


def test_airborne_capture_only_enemy(capsys):
    run("Board:\n. . .\nwK wR .\n. . .\nCommands:\n"
        "jump 50 150\nclick 150 150\nclick 50 150\nwait 1000\nprint board\n")
    assert output(capsys) == ". . .\nwK wR .\n. . ."
