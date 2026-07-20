# realtime/real_time_arbiter.py
from dataclasses import dataclass, field

from kongfuchess.model.arrival import ArrivalContext
from kongfuchess.model.piece import PieceState
from kongfuchess.realtime.motion import Motion, MotionView, RestView

# A piece protects its cell while it is jumping or short-resting after a jump.
_PROTECTING_STATES = (PieceState.JUMPING, PieceState.SHORT_REST)


@dataclass(frozen=True)
class AdvanceResult:
    """Outcome of advancing simulated time. `game_over` is the notification GameEngine acts on.

    Deliberately not "king_captured": *what* ends the game is a rules question, and this layer is
    not allowed to have an opinion on it.
    """
    game_over: bool = False


@dataclass
class _Phase:
    """One piece's timed lifecycle after it acts: an ordered list of (state, ends_at_ms) segments
    the piece walks through as the clock advances. A jump is JUMPING then SHORT_REST; a move's
    aftermath is a single LONG_REST. When the last segment ends the piece returns to IDLE.

    This holds *timing only* — no chess. The segment end times are absolute, so one large tick
    settles the whole chain correctly rather than restarting a segment from the current clock.

    `start_ms` and `end_ms` span the *whole* chain and are kept as the segments are consumed, so the
    wait can still be reported as a fraction once segments have been popped. A jump therefore reads
    as one continuous countdown across JUMPING and SHORT_REST rather than two restarting ones.
    """
    piece: object
    segments: list = field(default_factory=list)  # [(PieceState, ends_at_ms), ...]
    start_ms: int = 0
    end_ms: int = 0

    def remaining(self, now_ms) -> float:
        """How much of the wait is left, in [0, 1] — 1.0 as it begins, 0.0 as it ends."""
        span = self.end_ms - self.start_ms
        if span <= 0:
            return 0.0
        return min(1.0, max(0.0, (self.end_ms - now_ms) / span))


class RealTimeArbiter:
    """Owns the active motions and every piece's timed lifecycle (jump, rest) outside the Board,
    and resolves them as simulated time advances. It is the game's model of *time*, and it knows
    nothing about chess.

    Many motions may be in flight at once (real-time, no turns). A moving piece stays logically on
    its source cell until it arrives, so `print board` is deterministic. After a move a piece rests
    (LONG_REST); a jump is JUMPING then SHORT_REST, and throughout both the piece protects its cell.
    A piece is *busy* (uncommandable) whenever it is not IDLE — that per-piece rule replaces the old
    single-motion lock. Time is simulated via advance_time(ms) — never real sleep.

    What an arrival or a mid-flight collision *means* is not decided here. This class reports the
    situation to the injected rule set — including the one timing fact only it can know, whether the
    destination is protected — and applies whatever effects come back. So it contains no capture
    logic, no promotion, no victory condition, and no notion of a king.

    Collaborators are injected:
      - rules: resolve_arrival(ArrivalContext) -> list of effects
      - effect_applier: apply(board, effects) -> bool (whether the game ended)
      - collision_resolver (optional): resolve(board, motions, clock_ms) -> bool (game ended);
        detects and settles pieces meeting in flight, mutating the motion list in place.
    """

    def __init__(self, rules, effect_applier, ms_per_cell, jump_duration_ms,
                 long_rest_ms, short_rest_ms, collision_resolver=None):
        self._rules = rules
        self._applier = effect_applier
        self._ms_per_cell = ms_per_cell
        self._jump_duration_ms = jump_duration_ms
        self._long_rest_ms = long_rest_ms
        self._short_rest_ms = short_rest_ms
        self._collisions = collision_resolver
        self._clock_ms = 0
        self._motions = []
        self._phases = []                 # active jump/rest lifecycles (one per busy-resting piece)
        self._protected_until = {}        # piece -> absolute ms its cell stops being protected
        self._board = None

    def has_active_motion(self) -> bool:
        """Whether any motion is currently in flight. No longer a lock — many may run at once."""
        return len(self._motions) > 0

    def active_motions(self):
        """Read-only views of the in-flight motions, each sampled at the current clock, for the
        renderer to interpolate. Pure timing data — no chess, no live Motion handed out."""
        return [MotionView(m.piece, m.source, m.destination, m.progress(self._clock_ms))
                for m in self._motions]

    def rest_windows(self):
        """Read-only views of the pieces currently waiting out a cooldown, each sampled at the
        current clock, for the renderer to draw a countdown. Pure timing data, like active_motions:
        a cell and how much of its wait is left. Empty for an arbiter with no cooldowns."""
        return [RestView(phase.piece.cell, phase.remaining(self._clock_ms))
                for phase in self._phases]

    def airborne_cells(self):
        """The cells whose piece is mid-jump right now — for the renderer's jump animation."""
        return frozenset(phase.piece.cell for phase in self._phases
                         if phase.piece.state is PieceState.JUMPING)

    def start_motion(self, board, source, destination):
        """Begin a validated move. The piece is flagged MOVING but stays on its source cell."""
        piece = board.piece_at(source)
        motion = Motion.start(piece, destination, self._clock_ms, self._ms_per_cell)
        piece.state = PieceState.MOVING
        self._board = board
        self._motions.append(motion)
        return motion

    def request_jump(self, board, cell):
        """Make the piece on `cell` jump in place, protected until its short-rest ends.

        Gated only by whether the piece itself is busy (not IDLE) — never by another piece sliding
        toward the same cell. A jump does not lock the board and can coexist with an incoming move.
        """
        piece = board.piece_at(cell)
        if piece is None or piece.state is not PieceState.IDLE:
            return
        self._board = board
        jump_end = self._clock_ms + self._jump_duration_ms
        short_end = jump_end + self._short_rest_ms
        self._protected_until[piece.id] = short_end
        self._begin_phase(piece, [(PieceState.JUMPING, jump_end),
                                  (PieceState.SHORT_REST, short_end)], self._clock_ms)

    def advance_time(self, ms) -> AdvanceResult:
        """Advance the clock, settle mid-flight collisions, resolve arrivals, then age lifecycles."""
        self._clock_ms += ms
        game_over = self._resolve_collisions()
        if self._resolve_arrivals():
            game_over = True
        self._age_phases()
        return AdvanceResult(game_over=game_over)

    def _resolve_collisions(self) -> bool:
        """Let the injected resolver settle pieces meeting in flight, if one is wired in."""
        if self._collisions is None:
            return False
        return self._collisions.resolve(self._board, self._motions, self._clock_ms)

    def _resolve_arrivals(self) -> bool:
        arrived, still_moving = [], []
        for motion in self._motions:
            (arrived if motion.has_arrived(self._clock_ms) else still_moving).append(motion)
        self._motions = still_moving

        arrived.sort(key=lambda motion: motion.arrival_ms)
        game_over = False
        for motion in arrived:
            if self._resolve_arrival(motion):
                game_over = True
        return game_over

    def _resolve_arrival(self, motion) -> bool:
        """Ask the rules what this arrival means, apply it, then rest the piece if it survived."""
        context = ArrivalContext(
            board=self._board,
            piece=motion.piece,
            destination=motion.destination,
            destination_is_protected=self._is_protected_on_arrival(motion),
        )
        ended = self._applier.apply(self._board, self._rules.resolve_arrival(context))
        if motion.piece.state is not PieceState.CAPTURED:
            # The rest is measured from the moment of arrival, not the (possibly larger) tick-end
            # clock, so a single coarse advance settles the cooldown at the right time.
            self._begin_phase(motion.piece,
                              [(PieceState.LONG_REST, motion.arrival_ms + self._long_rest_ms)],
                              motion.arrival_ms)
        return ended

    def _is_protected_on_arrival(self, motion) -> bool:
        """Whether the destination's occupant is protected (jumping/short-resting) when this motion
        lands. The one fact about an arrival only the time model can answer; the rules decide what a
        protected destination does to the arriver.
        """
        occupant = self._board.piece_at(motion.destination)
        if occupant is None:
            return False
        return motion.arrival_ms <= self._protected_until.get(occupant.id, -1)

    def _begin_phase(self, piece, segments, start_ms):
        """Put a piece into the first of an ordered list of timed states (jump/rest).

        `start_ms` is when the wait *began*, which is not always now: a move's cooldown is measured
        from the arrival, so a coarse tick still reports the countdown from the right moment.
        """
        piece.state = segments[0][0]
        self._phases.append(_Phase(piece, list(segments), start_ms, segments[-1][1]))

    def _age_phases(self):
        """Walk each resting/jumping piece to whichever segment the clock now sits in, or IDLE."""
        active = []
        for phase in self._phases:
            if phase.piece.state is PieceState.CAPTURED:
                self._protected_until.pop(phase.piece.id, None)
                continue
            while phase.segments and self._clock_ms >= phase.segments[0][1]:
                phase.segments.pop(0)
            if phase.segments:
                phase.piece.state = phase.segments[0][0]
                active.append(phase)
            else:
                phase.piece.state = PieceState.IDLE
                self._protected_until.pop(phase.piece.id, None)
        self._phases = active
