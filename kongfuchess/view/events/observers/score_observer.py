# view/events/observers/score_observer.py
"""Keeps a running per-side score (final_plan §7.6). Pure side-effect object: it takes only the
piece-value table (config-driven, so no magic numbers) and reacts to capture events. Trivially
unit-testable without any UI machinery."""


class ScoreObserver:
    def __init__(self, values):
        self._values = values                    # {kind name: point value}
        self.score = {"white": 0, "black": 0}

    def on_capture(self, event):
        gainer = "black" if event.victim_color == "white" else "white"
        self.score[gainer] += self._values.get(event.victim_kind, 0)
