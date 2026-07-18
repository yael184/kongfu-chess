# view/events/events.py
"""The settlement events the UI reacts to (final_plan §7.6). Plain data — a color as its string
value, a captured piece's kind name, a ready-to-print move text — so observers never touch the
model. These are view-side: nothing in engine/ or model/ knows they exist.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MoveResolved:
    """A piece finished travelling to a new cell."""
    color: str          # "white" / "black"
    text: str           # display string, e.g. "N b1-c3"


@dataclass(frozen=True)
class CaptureResolved:
    """A piece was taken off the board (a capture or a dodge)."""
    victim_color: str
    victim_kind: str    # kind name, e.g. "rook"
