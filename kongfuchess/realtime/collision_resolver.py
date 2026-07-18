# realtime/collision_resolver.py
from kongfuchess.model.collision import (
    CANCEL, KEEP, STOP_BEFORE, STOP_ON, BlockContext, CrossContext,
)
from kongfuchess.model.piece import PieceState
from kongfuchess.model.position import Position

_PROTECTING_STATES = (PieceState.JUMPING, PieceState.SHORT_REST)


def _sign(value):
    return (value > 0) - (value < 0)


class CollisionResolver:
    """Detects pieces meeting in flight each tick and settles them through the injected rules.

    It owns only the *geometry and timing* of a real-time board — where each moving piece is right
    now, which pieces are stationary, and which motion started first — and nothing about chess. What
    a meeting *means* (capture, stop, be eaten, who survives) it asks the rule set, exactly as the
    arbiter asks about an arrival. Each collision is settled by retargeting the loser's Motion to
    arrive *now* on a chosen cell, so the arbiter's ordinary arrival handling performs the landing,
    capture and rest — a collision opens no second mutation path.

    Collaborators injected: the rule set (`flies_over`, `resolve_block`, `resolve_cross`) and an
    effect applier.
    """

    def __init__(self, rules, effect_applier):
        self._rules = rules
        self._applier = effect_applier

    def resolve(self, board, motions, clock_ms) -> bool:
        if board is None or not motions:
            return False
        game_over = False
        # A flies-over piece (knight) is exempt from every collision — never judged, never a mover.
        movers = [m for m in motions if not self._rules.flies_over(m.piece)]
        game_over |= self._resolve_crossings(board, movers, clock_ms)
        game_over |= self._resolve_blocks(board, motions, movers, clock_ms)
        # Motions whose piece was captured in a collision are done — drop them before arrivals run.
        motions[:] = [m for m in motions if m.piece.state is not PieceState.CAPTURED]
        return game_over

    # --- §3: two pieces moving at once ---------------------------------------------------------
    def _resolve_crossings(self, board, movers, clock_ms) -> bool:
        game_over = False
        for i, first in enumerate(movers):
            for second in movers[i + 1:]:
                if PieceState.CAPTURED in (first.piece.state, second.piece.state):
                    continue
                if self._current_cell(first, clock_ms) != self._current_cell(second, clock_ms):
                    continue
                started_first = _started_first(first, second)
                game_over |= self._judge_cross(board, first, second, started_first, clock_ms)
                if first.piece.state is not PieceState.CAPTURED:
                    game_over |= self._judge_cross(board, second, first, not started_first, clock_ms)
        return game_over

    def _judge_cross(self, board, mover, other, mover_started_first, clock_ms) -> bool:
        context = CrossContext(mover.piece, other.piece, mover_started_first)
        resolution = self._rules.resolve_cross(context)
        ended = self._applier.apply(board, resolution.effects)
        if resolution.adjustment == CANCEL:
            self._retarget(mover, mover.source, clock_ms)   # stop: settle back on its own cell
        return ended

    # --- §2: a mover meets a stationary piece mid-path -----------------------------------------
    def _resolve_blocks(self, board, motions, movers, clock_ms) -> bool:
        game_over = False
        moving_ids = {id(m.piece) for m in motions}
        for motion in movers:
            if motion.piece.state is PieceState.CAPTURED:
                continue
            cell = self._current_cell(motion, clock_ms)
            if cell == motion.source or cell == motion.destination:
                continue                                    # at the start, or at the final cell (arrival's job)
            occupant = board.piece_at(cell)
            if occupant is None or id(occupant) in moving_ids:
                continue                                    # empty, or another mover (a crossing, not a block)
            step_before = self._step_before(motion, cell)
            context = BlockContext(
                mover=motion.piece, blocker=occupant, at_cell=cell, step_before=step_before,
                is_first_step=(step_before == motion.source),
                blocker_protected=occupant.state in _PROTECTING_STATES,
            )
            resolution = self._rules.resolve_block(context)
            if self._applier.apply(board, resolution.effects):
                game_over = True
            self._apply_block_adjustment(motion, resolution.adjustment, cell, step_before, clock_ms)
        return game_over

    def _apply_block_adjustment(self, motion, adjustment, at_cell, step_before, clock_ms):
        if adjustment == KEEP:
            return
        target = {STOP_ON: at_cell, STOP_BEFORE: step_before, CANCEL: motion.source}[adjustment]
        self._retarget(motion, target, clock_ms)

    # --- geometry helpers ----------------------------------------------------------------------
    def _current_cell(self, motion, clock_ms) -> Position:
        progress = motion.progress(clock_ms)
        row = round(motion.source.row + (motion.destination.row - motion.source.row) * progress)
        col = round(motion.source.col + (motion.destination.col - motion.source.col) * progress)
        return Position(row, col)

    def _step_before(self, motion, cell) -> Position:
        row_step = _sign(motion.destination.row - motion.source.row)
        col_step = _sign(motion.destination.col - motion.source.col)
        return Position(cell.row - row_step, cell.col - col_step)

    def _retarget(self, motion, cell, clock_ms):
        """Truncate a motion so it arrives on `cell` this very tick; arrival then does the rest."""
        motion.destination = cell
        motion.arrival_ms = clock_ms


def _started_first(a, b) -> bool:
    """A deterministic 'who moved first': earlier start wins; ties broken by identity so exactly one
    of the pair is the first-mover (never both, never neither)."""
    if a.start_ms != b.start_ms:
        return a.start_ms < b.start_ms
    return id(a) < id(b)
