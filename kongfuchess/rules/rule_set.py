# rules/rule_set.py
from kongfuchess.model.effects import EndGame, MovePiece, RemovePiece, TransformPiece
from kongfuchess.rules.rule_engine import RuleEngine


class ChessRuleSet:
    """The single object that answers every rules question for the game in play.

    It is the only place that knows what chess *is*: how each piece moves, that a piece arriving on
    an enemy captures it, that a dodging piece beats the attacker that lands on it, that a pawn
    promotes, and that taking a king wins. Every one of those answers is returned as data — a
    MoveValidation, or a list of effects — so no other layer ever has to encode a rule to act on it.

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

    def resolve_arrival(self, context) -> list:
        """A piece has reached its destination: return the effects that follow, changing nothing.

        Three outcomes, in order:
          - the destination holds an enemy who is still airborne (a successful dodge): the dodger
            eats the attacker, who is removed instead;
          - the destination holds an enemy who is not protected: it is captured and the piece lands;
          - otherwise the piece simply lands.
        A landing piece may then be transformed by its own rule (a pawn promoting).
        """
        occupant = context.board.piece_at(context.destination)

        if context.destination_is_protected and context.piece.is_enemy_of(occupant):
            return self._capture(context.piece)

        effects = []
        if context.piece.is_enemy_of(occupant):
            effects.extend(self._capture(occupant))
        effects.append(MovePiece(context.piece, context.destination))
        effects.extend(self._transformation(context))
        return effects

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
