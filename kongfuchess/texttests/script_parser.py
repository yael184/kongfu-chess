# texttests/script_parser.py


class ScriptParseError(Exception):
    """Raised when the document structure is invalid. `code` is a stable machine-readable reason."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ParsedScript:
    """A parsed text-test document: the raw board section plus the list of command lines."""
    def __init__(self, board_text, commands):
        self.board_text = board_text
        self.commands = commands


class ScriptParser:
    """Splits a text-test document into its board section and command list.

    Format (both markers required):
        Board:
        <rows>
        Commands:
        <one command per line>
    """
    BOARD_MARKER = "Board:"
    COMMANDS_MARKER = "Commands:"

    def parse(self, text: str) -> ParsedScript:
        if self.COMMANDS_MARKER not in text or self.BOARD_MARKER not in text:
            raise ScriptParseError("UNKNOWN_TOKEN")

        board_part, commands_part = text.split(self.COMMANDS_MARKER, 1)
        board_text = board_part.replace(self.BOARD_MARKER, "", 1).strip()
        commands = [line.strip() for line in commands_part.strip().split("\n") if line.strip()]
        return ParsedScript(board_text, commands)
