# texttests/commands.py


class UnknownCommandError(Exception):
    """Raised by a handler when a line names it but the arguments do not fit it.

    The runner turns this into the same error the user sees for a command it has never heard of,
    so "print sideways" and "frobnicate" are reported identically.
    """


def pixel_command(action):
    """`<name> x y` -> action(x, y), where x and y are pixel coordinates."""

    def handler(args):
        if len(args) != 2:
            raise UnknownCommandError
        action(_to_int(args[0]), _to_int(args[1]))

    return handler


def duration_command(action):
    """`<name> <ms>` -> action(ms)."""

    def handler(args):
        if len(args) != 1:
            raise UnknownCommandError
        action(_to_int(args[0]))

    return handler


def print_board_command(engine, printer):
    """`print board` -> render the engine's current snapshot."""

    def handler(args):
        if args != ["board"]:
            raise UnknownCommandError
        print(printer.to_text(engine.snapshot()))

    return handler


def _to_int(text):
    try:
        return int(text)
    except ValueError:
        raise UnknownCommandError from None
