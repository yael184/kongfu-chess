# texttests/script_runner.py
from kongfuchess.texttests.commands import UnknownCommandError


class ScriptRunner:
    """Executes text-test commands by dispatching each line to an injected command table.

    The table maps a command name to a handler taking the line's remaining arguments; it is built
    in composition/app_factory (see texttests/commands.py for the handlers). The runner therefore
    knows no command by name: adding `undo` or `speed 2` is a new entry in that table, not an edit
    here.

    An empty line is a no-op. A line naming no known command — or naming one with arguments that
    do not fit it — prints an unknown-command error.
    """

    def __init__(self, commands):
        self._commands = commands

    def run(self, lines):
        for line in lines:
            self._execute(line)

    def _execute(self, line):
        parts = line.split()
        if not parts:
            return

        handler = self._commands.get(parts[0])
        if handler is None:
            self._report_unknown(line)
            return

        try:
            handler(parts[1:])
        except UnknownCommandError:
            self._report_unknown(line)

    def _report_unknown(self, line):
        print(f"ERROR: Unknown command '{line}'")
