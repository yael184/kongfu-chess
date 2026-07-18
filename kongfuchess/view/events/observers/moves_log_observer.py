# view/events/observers/moves_log_observer.py
"""Keeps the most recent moves per side for the panel (final_plan §7.6). Pure side-effect object,
bounded so the log never grows without limit."""


class MovesLogObserver:
    def __init__(self, limit=14):
        self._limit = limit
        self.entries = []                        # list of (color, text), oldest first

    def on_move(self, event):
        self.entries.append((event.color, event.text))
        if len(self.entries) > self._limit:
            self.entries = self.entries[-self._limit:]
