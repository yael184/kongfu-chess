# view/events/settlement_detector.py
"""Turns board changes into settlement events by diffing consecutive snapshots, then publishes them
to the EventBus.

This is the adaptation to our engine: final_plan assumed an engine that emits SettlementEvents, but
ours settles moves deep in the arbiter with no such hook. Rather than couple the engine to the UI, a
UI-side detector watches the read-only snapshot the loop already fetches each tick — a piece whose
cell changed settled a move; a piece that vanished was captured (an ordinary capture or a dodge). The
Observer architecture downstream is exactly the one final_plan describes; only the source differs.
"""
from kongfuchess.view.events.events import CaptureResolved, MoveResolved


class SettlementDetector:
    def __init__(self, event_bus, symbols):
        self._bus = event_bus
        self._symbols = symbols          # {kind name: symbol}, for the move text
        self._previous = None            # {piece id: (kind, color, cell)}

    def observe(self, snapshot):
        current = {p.id: (p.kind, p.color, p.cell) for p in snapshot.pieces()}
        if self._previous is not None:
            self._publish_changes(self._previous, current, snapshot.height)
        self._previous = current

    def _publish_changes(self, previous, current, board_height):
        for piece_id, (kind, color, cell) in previous.items():
            if piece_id not in current:
                self._bus.publish(CaptureResolved(color.value, kind.name))
            elif current[piece_id][2] != cell:
                destination = current[piece_id][2]
                text = f"{self._symbols.get(kind.name, '?')} " \
                       f"{_cell_name(cell, board_height)}-{_cell_name(destination, board_height)}"
                self._bus.publish(MoveResolved(color.value, text))


def _cell_name(cell, board_height):
    """Algebraic-ish cell name: column -> file letter, row -> rank counted from the bottom."""
    return f"{chr(ord('a') + cell.col)}{board_height - cell.row}"
