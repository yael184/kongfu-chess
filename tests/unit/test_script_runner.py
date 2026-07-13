# tests/unit/test_script_runner.py
import pytest

from texttests.commands import (
    UnknownCommandError, duration_command, pixel_command, print_board_command,
)
from texttests.script_runner import ScriptRunner


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


def test_dispatches_a_command_to_its_handler():
    spy = Spy()
    ScriptRunner({"click": pixel_command(spy)}).run(["click 150 250"])
    assert spy.calls == [(150, 250)]


def test_the_runner_knows_no_command_by_name():
    # Adding a command is a new entry in the table, never an edit to the runner.
    spy = Spy()
    ScriptRunner({"teleport": pixel_command(spy)}).run(["teleport 10 20"])
    assert spy.calls == [(10, 20)]


def test_blank_lines_are_ignored():
    spy = Spy()
    ScriptRunner({"wait": duration_command(spy)}).run(["", "   ", "wait 500"])
    assert spy.calls == [(500,)]


def test_an_unknown_command_is_reported(capsys):
    ScriptRunner({}).run(["frobnicate 1 2"])
    assert capsys.readouterr().out.strip() == "ERROR: Unknown command 'frobnicate 1 2'"


def test_a_known_command_with_wrong_arguments_is_reported_the_same_way(capsys):
    ScriptRunner({"click": pixel_command(Spy())}).run(["click 50"])
    assert capsys.readouterr().out.strip() == "ERROR: Unknown command 'click 50'"


def test_non_numeric_coordinates_are_reported_not_crashed(capsys):
    ScriptRunner({"click": pixel_command(Spy())}).run(["click here now"])
    assert capsys.readouterr().out.strip() == "ERROR: Unknown command 'click here now'"


# --- the handlers themselves ---
def test_pixel_command_rejects_the_wrong_arity():
    with pytest.raises(UnknownCommandError):
        pixel_command(Spy())(["50"])


def test_duration_command_rejects_the_wrong_arity():
    with pytest.raises(UnknownCommandError):
        duration_command(Spy())(["500", "extra"])


def test_print_command_only_understands_the_board(capsys):
    class FakeEngine:
        def snapshot(self):
            return "the-snapshot"

    class FakePrinter:
        def to_text(self, view):
            return f"rendered({view})"

    handler = print_board_command(FakeEngine(), FakePrinter())
    handler(["board"])
    assert capsys.readouterr().out.strip() == "rendered(the-snapshot)"

    with pytest.raises(UnknownCommandError):
        handler(["sideways"])
