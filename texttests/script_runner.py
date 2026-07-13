# texttests/script_runner.py


class ScriptRunner:
    """Executes text-test commands against the game through the public boundaries.

    Commands:

      - ``click x y``   -> Controller.handle_click (pixel coords; selection + request_move)
      - ``jump x y``    -> Controller.handle_jump (pixel coords; dodge in place)
      - ``wait <ms>``   -> GameEngine.wait (advance simulated time)
      - ``print board`` -> render the current snapshot via the printer

    An empty line is a no-op; anything else prints an unknown-command error.
    """

    def __init__(self, engine, controller, printer):
        self._engine = engine
        self._controller = controller
        self._printer = printer

    def run(self, commands):
        for command in commands:
            self._execute(command)

    def _execute(self, command):
        parts = command.split()
        if not parts:
            return

        name = parts[0]
        if name == "click" and len(parts) == 3:
            self._controller.handle_click(int(parts[1]), int(parts[2]))
        elif name == "jump" and len(parts) == 3:
            self._controller.handle_jump(int(parts[1]), int(parts[2]))
        elif name == "wait" and len(parts) == 2:
            self._engine.wait(int(parts[1]))
        elif command.strip() == "print board":
            print(self._printer.to_text(self._engine.snapshot()))
        else:
            print(f"ERROR: Unknown command '{command}'")
