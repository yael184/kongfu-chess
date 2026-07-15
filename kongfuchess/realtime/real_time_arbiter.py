# realtime/real_time_arbiter.py
from dataclasses import dataclass

from kongfuchess.model.arrival import ArrivalContext
from kongfuchess.model.piece import PieceState
from kongfuchess.realtime.motion import Motion


@dataclass(frozen=True)
class AdvanceResult:
    """Outcome of advancing simulated time. `game_over` is the notification GameEngine acts on.

    Deliberately not "king_captured": *what* ends the game is a rules question, and this layer is
    not allowed to have an opinion on it.
    """
    game_over: bool = False


class RealTimeArbiter:
    """Owns the active motions and jumps (outside the Board) and resolves them as simulated time
    advances. It is the game's model of *time*, and it knows nothing about chess.

    It receives only already-validated move commands. A moving piece stays logically on its source
    cell until it arrives; the board's occupancy changes only on arrival, so `print board` is
    deterministic. A jump (dodge) keeps a piece on its cell but protected for a window. Time is
    simulated via advance_time(ms) — never real sleep.

    What an arrival *means* is not decided here. This class reports the situation to the injected
    rule set — including the one timing fact only it can know, whether the destination holds a
    piece that is still airborne — and applies whatever effects come back. So it contains no
    capture logic, no promotion, no victory condition, and no notion of a king; swapping the rules
    (or the whole game) leaves this file untouched, and swapping the *time model* is the only
    reason to edit it.

    Collaborators are injected:
      - rules: resolve_arrival(ArrivalContext) -> list of effects
      - effect_applier: apply(board, effects) -> bool (whether the game ended)
    """

    def __init__(self, rules, effect_applier, ms_per_cell: int, jump_duration_ms: int):
        self._rules = rules
        self._applier = effect_applier
        self._ms_per_cell = ms_per_cell
        self._jump_duration_ms = jump_duration_ms
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
        game_over = False
        for motion in arrived:
            if self._resolve_arrival(motion):
                game_over = True

        self._expire_airborne()
        return AdvanceResult(game_over=game_over)

    def _resolve_arrival(self, motion) -> bool:
        """Ask the rules what this arrival means, apply it, and report whether the game ended."""
        context = ArrivalContext(
            board=self._board,
            piece=motion.piece,
            destination=motion.destination,
            destination_is_protected=self._is_protected_on_arrival(motion),
        )
        return self._applier.apply(self._board, self._rules.resolve_arrival(context))

    def _is_protected_on_arrival(self, motion) -> bool:
        """Whether the destination's occupant is still airborne when this motion lands.

        The one fact about an arrival that only the time model can answer — and the only one this
        class passes to the rules.
        """
        land_ms = self._airborne.get(motion.destination)
        return land_ms is not None and motion.arrival_ms <= land_ms

    def _expire_airborne(self):
        """Drop jumps whose land time has passed."""
        self._airborne = {cell: land for cell, land in self._airborne.items()
                          if land >= self._clock_ms}

    def _has_motion_from(self, cell) -> bool:
        return any(motion.source == cell for motion in self._motions)
