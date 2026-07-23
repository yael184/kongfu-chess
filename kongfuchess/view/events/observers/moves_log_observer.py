# view/events/observers/moves_log_observer.py
"""Keeps the most recent moves for the panel (final_plan §7.6). Pure side-effect object, bounded so
the log never grows without limit.

The spec asks for a separate column per player, so the log is kept per colour rather than as one
interleaved list: `entries["white"]` / `entries["black"]`, each a list of (at_ms, text) newest-last,
so the panel can draw two columns and stamp each move with its server-time."""


class MovesLogObserver:
    def __init__(self, limit=8):
        self._limit = limit
        self.entries = {"white": [], "black": []}   # per side: list of (at_ms, text), oldest first

    def on_move(self, event):
        column = self.entries[event.color]
        column.append((event.at_ms, event.text))
        if len(column) > self._limit:
            self.entries[event.color] = column[-self._limit:]
