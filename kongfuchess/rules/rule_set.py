# rules/rule_set.py
from kongfuchess.model.collision import (
    CANCEL, KEEP, STOP_BEFORE, STOP_ON, CollisionResolution,
)
from kongfuchess.model.effects import EndGame, MovePiece, RemovePiece, TransformPiece
from kongfuchess.rules.rule_engine import RuleEngine


class ChessRuleSet:
    """The single object that answers every rules question for the game in play.

    It is the only place that knows what chess *is*: how each piece moves, that a piece arriving on
    an enemy captures it, that a dodging (protected) piece beats whoever lands on it, that a knight
    alone may take a friend, that a pawn promotes, and that taking a king wins. Every one of those
    answers is returned as data — a MoveValidation, a list of effects, or a CollisionResolution — so
    no other layer ever has to encode a rule to act on it.

    Changing the game (a variant, a custom ruleset, plain non-real-time chess) means constructing a
    different rule set. Nothing outside rules/ changes.
    """

    def __init__(self, rules, victory_kinds):
        self._rules = rules                        # PieceRuleRegistry
        self._victory_kinds = frozenset(victory_kinds)  # capturing one of these wins the game
        self._validator = RuleEngine(rules)

    def legal_destinations(self, board, piece):
        """Every cell `piece` may move to right now."""
        return self._rules.rule_for(piece.kind).legal_destinations(board, piece)

    def validate_move(self, board, source, destination):
        """Is this move legal? Read-only — it changes nothing."""
        return self._validator.validate_move(board, source, destination)

    def flies_over(self, piece) -> bool:
        """Whether this piece ignores collisions (the knight) — exempt from mid-flight meetings and
        the only piece that may capture a friend. A configured property, not a kind check here."""
        return self._rules.rule_for(piece.kind).flies_over

    def resolve_arrival(self, context) -> list:
        """A piece has reached its destination: return the effects that follow, changing nothing.

        Following the collision rules' arrival table:
          - a protected destination (occupant jumping/short-resting, any colour) eats the arriver;
          - an empty cell: the piece lands (and may promote);
          - an enemy: captured, the piece lands;
          - a friend: nobody moves and nothing is captured — *unless* the arriver flies over (a
            knight), the one piece that may take a friend, in which case it captures and lands.
        A piece that fails silently onto a friend simply stays; the arbiter still rests it.
        """
        occupant = context.board.piece_at(context.destination)
        piece = context.piece

        if context.destination_is_protected:
            return self._capture(piece)

        if occupant is None:
            return self._land(context)

        if piece.is_enemy_of(occupant) or self.flies_over(piece):
            return self._capture(occupant) + self._land(context)

        return []  # a friend holds the cell and the arriver does not fly over: stay put

    def resolve_block(self, context) -> CollisionResolution:
        """A mover met a stationary piece on `at_cell` (collision rules §2).

        A protected blocker: redirect onto it so the arrival rule's protection eats the mover. An
        enemy: capture it and stop on its cell. A friend: stop one cell before it, or cancel the
        move if the friend is already on the mover's first step.
        """
        if context.blocker_protected:
            return CollisionResolution(adjustment=STOP_ON)
        if context.mover.is_enemy_of(context.blocker):
            return CollisionResolution(effects=tuple(self._capture(context.blocker)),
                                       adjustment=STOP_ON)
        return CollisionResolution(adjustment=CANCEL if context.is_first_step else STOP_BEFORE)

    def resolve_cross(self, context) -> CollisionResolution:
        """Two movers met at the same cell (collision rules §3), judging `context.mover`.

        Two enemies: the later starter is captured (so if the judged mover started later, it dies).
        Two friends: the later starter stops (cancels). The earlier starter, and any pairing the
        caller has already exempted, is left untouched.
        """
        if context.mover_started_first:
            return CollisionResolution(adjustment=KEEP)
        if context.mover.is_enemy_of(context.other):
            return CollisionResolution(effects=tuple(self._capture(context.mover)))
        return CollisionResolution(adjustment=CANCEL)

    def _land(self, context):
        """The piece moves to the destination and its rule may then transform it (promotion)."""
        return [MovePiece(context.piece, context.destination)] + self._transformation(context)

    def _capture(self, piece):
        """Removing this piece — and, if it is a piece the game is won by taking, ending the game."""
        effects = [RemovePiece(piece)]
        if piece.kind in self._victory_kinds:
            effects.append(EndGame())
        return effects

    def _transformation(self, context):
        """The piece's own rule decides what it becomes on landing (promotion), if anything."""
        rule = self._rules.rule_for(context.piece.kind)
        new_kind = rule.kind_after_arrival(context.board, context.piece, context.destination)
        return [] if new_kind is None else [TransformPiece(context.piece, new_kind)]
