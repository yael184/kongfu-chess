# realtime/real_time_arbiter.py
from dataclasses import dataclass

import config
from model.piece import PieceKind, PieceState
from rules.piece_rules import promotion_kind
from realtime.motion import Motion


@dataclass(frozen=True)
class AdvanceResult:
    """Outcome of advancing simulated time. `king_captured` is the notification GameEngine acts on."""
    king_captured: bool = False


class RealTimeArbiter:
    """Owns the active motions and jumps (outside the Board) and resolves them as simulated time
    advances.

    It receives only already-validated move commands. A moving piece stays logically on its
    source cell until it arrives; the board's occupancy changes only on arrival, so `print board`
    is deterministic. A jump (dodge) keeps a piece on its cell but protected for a window: an enemy
    that arrives while it is still airborne is eaten by the jumper. Time is simulated via
    advance_time(ms) — never real sleep.
    """

    def __init__(self, ms_per_cell=None, jump_duration_ms=None):
        self._ms_per_cell = ms_per_cell if ms_per_cell is not None else config.MS_PER_CELL
        self._jump_duration_ms = jump_duration_ms if jump_duration_ms is not None else config.JUMP_DURATION_MS
        self._clock_ms = 0
        self._motions = []
        self._airborne = {}  # Position -> land_ms: pieces jumping in place, protected until they land
        self._board = None

    def has_active_motion(self) -> bool:
        """Whether any motion is currently in flight (the common-route one-active-motion fact)."""
        return len(self._motions) > 0

    def start_motion(self, board, source, destination):
        """Begin a validated move. The piece is flagged MOVING but stays on its source cell."""
        piece = board.piece_at(source)
        motion = Motion.start(piece, destination, self._clock_ms, self._ms_per_cell)
        piece.state = PieceState.MOVING
        self._board = board
        self._motions.append(motion)
        return motion

    def request_jump(self, board, cell):
        """Make the piece on `cell` jump in place, protected until it lands.

        Ignored if the cell is empty, the piece is already in flight, or it is already airborne.
        A jump does not lock the board and can coexist with an incoming enemy move.
        """
        if board.piece_at(cell) is None:
            return
        if self._has_motion_from(cell):
            return
        if cell in self._airborne:
            return
        self._board = board
        self._airborne[cell] = self._clock_ms + self._jump_duration_ms

    def advance_time(self, ms) -> AdvanceResult:
        """Advance the clock, atomically resolve arrived motions, then drop landed jumps."""
        self._clock_ms += ms

        arrived, still_moving = [], []
        for motion in self._motions:
            (arrived if motion.has_arrived(self._clock_ms) else still_moving).append(motion)
        self._motions = still_moving

        arrived.sort(key=lambda motion: motion.arrival_ms)
        king_captured = False
        for motion in arrived:
            if self._resolve_arrival(motion):
                king_captured = True

        self._expire_airborne()
        return AdvanceResult(king_captured=king_captured)

    def _resolve_arrival(self, motion) -> bool:
        """Atomically land a motion; returns True if a king was captured.

        Jump collision: if an enemy is still airborne on the destination when the mover arrives
        (arrival <= its land time), the jumper eats the arriving attacker (the attacker is removed
        from its origin, the jumper stays put). Otherwise it is a normal capture-and-move, with
        pawn promotion applied on arrival.
        """
        board = self._board
        destination = motion.destination
        arriver = motion.piece
        occupant = board.piece_at(destination)
        land_ms = self._airborne.get(destination)

        if (land_ms is not None and motion.arrival_ms <= land_ms
                and occupant is not None and occupant.color != arriver.color):
            board.remove_piece(arriver)
            arriver.state = PieceState.CAPTURED
            return arriver.kind == PieceKind.KING

        king_captured = False
        if occupant is not None:
            king_captured = occupant.kind == PieceKind.KING
            board.remove_piece(occupant)
            occupant.state = PieceState.CAPTURED

        board.move_piece(motion.source, destination)
        arriver.state = PieceState.IDLE
        self._apply_promotion(arriver)
        return king_captured

    def _apply_promotion(self, piece):
        new_kind = promotion_kind(piece, self._board)
        if new_kind is not None:
            piece.kind = new_kind

    def _expire_airborne(self):
        """Drop jumps whose land time has passed."""
        self._airborne = {cell: land for cell, land in self._airborne.items()
                          if land >= self._clock_ms}

    def _has_motion_from(self, cell) -> bool:
        return any(motion.source == cell for motion in self._motions)
