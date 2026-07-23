# view/events/events.py
"""The settlement events the UI reacts to (final_plan §7.6). Plain data — a color as its string
value, a captured piece's kind name, a ready-to-print move text — so observers never touch the
model. These are view-side: nothing in engine/ or model/ knows they exist.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MoveResolved:
    """A piece finished travelling to a new cell.

    `at_ms` is the server clock when the move settled — the same time base collisions are ordered by
    (the spec's server-time), so the panel can stamp each move with when it happened.
    """
    color: str          # "white" / "black"
    text: str           # display string, e.g. "N b1-c3" (or "N b1xc3" for a capture)
    at_ms: int = 0      # server-time of the settlement, in ms


@dataclass(frozen=True)
class CaptureResolved:
    """A piece was taken off the board (a capture or a dodge)."""
    victim_color: str
    victim_kind: str    # kind name, e.g. "rook"


@dataclass(frozen=True)
class PromotionResolved:
    """A piece changed kind on arrival (a pawn reaching the far rank becomes a queen). This scores on
    its own — the spec credits a promotion even when it captures nothing — so it is a distinct event
    from a capture, published whenever a piece's kind changes between two snapshots."""
    color: str          # the promoting side, "white" / "black"
    new_kind: str       # what it became, e.g. "queen"
