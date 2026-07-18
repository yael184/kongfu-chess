# model/collision.py
from dataclasses import dataclass

from kongfuchess.model.piece import Piece
from kongfuchess.model.position import Position

# How a mover's motion is adjusted after a collision. The arbiter reads these and simply retargets
# the Motion (setting its destination and making it arrive now), so the existing arrival machinery
# does the actual landing/capture/rest — a collision needs no new mutation path.
STOP_BEFORE = "stop_before"   # truncate to the cell just before the blocker
STOP_ON = "stop_on"           # truncate onto the blocker's cell (capture there, or be eaten if it is protected)
CANCEL = "cancel"             # the move fails; the piece settles back on its own cell and rests
KEEP = "keep"                 # no change — the motion continues


@dataclass(frozen=True)
class BlockContext:
    """A moving piece meets a *stationary* piece on `at_cell` mid-flight. Neutral ground between
    realtime/ (which spots the geometry) and rules/ (which says what it means)."""
    mover: Piece
    blocker: Piece
    at_cell: Position
    step_before: Position          # the cell one step back along the mover's path
    is_first_step: bool            # the blocker sits on the mover's very first step (no room to stop before)
    blocker_protected: bool        # the blocker is jumping/short-resting


@dataclass(frozen=True)
class CrossContext:
    """Two moving pieces meet at the same cell in flight. `mover` is the one being judged."""
    mover: Piece
    other: Piece
    mover_started_first: bool


@dataclass(frozen=True)
class CollisionResolution:
    """What a meeting means: effects to apply now, and how to adjust the judged mover's motion."""
    effects: tuple = ()
    adjustment: str = KEEP
