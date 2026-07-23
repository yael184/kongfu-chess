# view/events/observers/score_observer.py
"""Keeps a running per-side score (final_plan §7.6). Pure side-effect object: it takes only the
piece-value table (config-driven, so no magic numbers) and reacts to capture and promotion events.
Trivially unit-testable without any UI machinery.

`lead` exposes the difference between the sides, since the spec asks the panel to show the gap
between the opponents, not only two isolated totals."""


class ScoreObserver:
    def __init__(self, values):
        self._values = values                    # {kind name: point value}
        self.score = {"white": 0, "black": 0}

    def on_capture(self, event):
        gainer = "black" if event.victim_color == "white" else "white"
        self.score[gainer] += self._values.get(event.victim_kind, 0)

    def on_promotion(self, event):
        # A promotion scores on its own — the promoting side gains the value of what the piece became
        # (a queen's 9), whether or not the promoting move also captured.
        self.score[event.color] += self._values.get(event.new_kind, 0)

    @property
    def lead(self):
        """Signed white-minus-black gap; positive means white is ahead."""
        return self.score["white"] - self.score["black"]
