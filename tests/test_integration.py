# tests/test_integration.py
# End-to-end tests of complete game scenarios through main (injected input).
from io import StringIO

import main


def test_king_legal_and_illegal_commands(capsys):
    input_data = (
        "Board:\n"
        "wK . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"   # select the king at (0,0)
        "click 250 50\n"  # illegal move (distance 2) - ignored
        "print board\n"
        "click 50 50\n"   # reselect
        "click 150 150\n"  # legal move (diagonal 1)
        "wait 1000\n"      # wait until the move arrives
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    assert "wK . .\n. . ." in out   # after the illegal move the piece did not move
    assert ". . .\n. wK ." in out   # after the legal move


def test_rook_and_bishop_integration(capsys):
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". bB .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"    # select the rook (0,0)
        "click 50 250\n"   # move the rook to (2,0) - legal straight line (distance 2 -> 2000ms)
        "wait 2000\n"      # the rook arrives; the board unlocks (no concurrent movement)
        "click 150 150\n"  # select the bishop (1,1)
        "click 250 250\n"  # move the bishop to (2,2) - legal diagonal (distance 1 -> 1000ms)
        "wait 1000\n"      # the bishop arrives
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        ". . .\n"
        ". . .\n"
        "wR . bB"
    )
    assert expected in out


def test_movement_over_time_shows_origin_then_destination(capsys):
    # Before the arrival time the printed board still shows the piece at the origin; after a sufficient wait - at the destination.
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"    # select the rook (0,0)
        "click 50 250\n"   # move to (2,0), distance 2 -> arrival time 2000ms
        "print board\n"    # still in flight: the rook is at the origin
        "wait 2000\n"      # complete the move
        "print board\n"    # after arrival: the rook is at the destination
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    assert "wR . .\n. . .\n. . ." in out   # before arrival - at the origin
    assert ". . .\n. . .\nwR . ." in out   # after arrival - at the destination


def test_opposite_colors_do_not_move_concurrently_in_common_route(capsys):
    # While one move is in progress the board is locked: the black rook cannot set off
    # concurrently with the white rook, so it stays put.
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". . .\n"
        "bR . .\n"
        "Commands:\n"
        "click 50 50\n"    # select the white rook (0,0)
        "click 250 50\n"   # launch a move to (0,2) - the board locks
        "click 50 250\n"   # attempt to select the black rook (2,0) - ignored while locked
        "click 250 250\n"  # attempt to move it to (2,2) - ignored
        "wait 2000\n"      # the white rook arrives
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        ". . wR\n"
        ". . .\n"
        "bR . ."
    )
    assert expected in out


def test_jump_dodges_and_eats_attacker(capsys):
    # The pawn jumps; the adjacent rook arrives during the jump and is eaten by the jumper.
    input_data = (
        "Board:\n"
        "wP bR .\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "jump 50 50\n"     # (0,0) jumps
        "click 150 50\n"   # select the rook (0,1)
        "click 50 50\n"    # attack toward (0,0), distance 1 -> arrival 1000 (during the jump)
        "wait 1000\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        "wP . .\n"
        ". . .\n"
        ". . ."
    )
    assert expected in out


def test_jump_lands_before_attacker_and_is_eaten(capsys):
    # The rook is far and arrives after the jumper landed -> the rook eats the pawn.
    input_data = (
        "Board:\n"
        "wP . bR\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "jump 50 50\n"     # (0,0) jumps, lands at 1000
        "click 250 50\n"   # select the rook (0,2)
        "click 50 50\n"    # attack toward (0,0), distance 2 -> arrival 2000 (after landing)
        "wait 2000\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        "bR . .\n"
        ". . .\n"
        ". . ."
    )
    assert expected in out


def test_capturing_king_ends_game_and_freezes_board(capsys):
    # Capturing the king ends the game; subsequent moves are ignored and the board is frozen.
    input_data = (
        "Board:\n"
        "wR . bK\n"
        ". bR .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"    # select the white rook (0,0)
        "click 250 50\n"   # move toward the black king at (0,2)
        "wait 2000\n"      # arrival captures the king -> game over
        "click 150 150\n"  # attempt to select bR after the game ended - ignored
        "click 50 150\n"   # attempt a move - ignored
        "wait 2000\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    # The white rook took the king's cell, and the black rook stayed put.
    expected = (
        ". . wR\n"
        ". bR .\n"
        ". . ."
    )
    assert expected in out
