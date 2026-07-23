# view/events/settlement_detector.py
"""Turns board changes into settlement events by diffing consecutive snapshots, then publishes them
to the EventBus.

This is the adaptation to our engine: final_plan assumed an engine that emits SettlementEvents, but
ours settles moves deep in the arbiter with no such hook. Rather than couple the engine to the UI, a
UI-side detector watches the read-only snapshot the loop already fetches each tick — a piece whose
cell changed settled a move; a piece that vanished was captured (an ordinary capture or a dodge); a
piece whose kind changed was promoted. The Observer architecture downstream is exactly the one
final_plan describes; only the source differs.

Each observe() carries the server clock so a settled move can be stamped with when it happened —
the same time base collisions are ordered by. It is passed in, not read here, so this stays timing-
and config-free (it never touches the engine or the clock itself).
"""
from kongfuchess.view.events.events import CaptureResolved, MoveResolved, PromotionResolved


class SettlementDetector:
    def __init__(self, event_bus, symbols):
        self._bus = event_bus
        self._symbols = symbols          # {kind name: symbol}, for the move text
        self._previous = None            # {piece id: (kind, color, cell)}

    def observe(self, snapshot, now_ms=0):
        current = {p.id: (p.kind, p.color, p.cell) for p in snapshot.pieces()}
        if self._previous is not None:
            self._publish_changes(self._previous, current, snapshot.height, now_ms)
        self._previous = current

    def _publish_changes(self, previous, current, board_height, now_ms):
        # The cells a piece vanished from this tick — a move that lands on one of them is a capture.
        vacated_by_capture = {cell for piece_id, (_, _, cell) in previous.items()
                              if piece_id not in current}
        for piece_id, (kind, color, cell) in previous.items():
            if piece_id not in current:
                self._bus.publish(CaptureResolved(color.value, kind.name))
                continue
            new_kind, _, destination = current[piece_id]
            if destination != cell:
                self._publish_move(kind, color, cell, destination, board_height,
                                   destination in vacated_by_capture, now_ms)
            if new_kind != kind:
                self._bus.publish(PromotionResolved(color.value, new_kind.name))

    def _publish_move(self, kind, color, source, destination, board_height, is_capture, now_ms):
        link = "x" if is_capture else "-"       # algebraic: a capture is written with an x
        text = f"{self._symbols.get(kind.name, '?')} " \
               f"{_cell_name(source, board_height)}{link}{_cell_name(destination, board_height)}"
        self._bus.publish(MoveResolved(color.value, text, now_ms))


def _cell_name(cell, board_height):
    """Algebraic-ish cell name: column -> file letter, row -> rank counted from the bottom."""
    return f"{chr(ord('a') + cell.col)}{board_height - cell.row}"
