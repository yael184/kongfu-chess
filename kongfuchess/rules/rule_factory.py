# rules/rule_factory.py
"""Builds the rules in play from piece specs (see config.toml's [[pieces]]).

This is the bridge from configuration to strategy objects. A piece spec names a `movement`
pattern; MOVEMENT_BUILDERS turns that name into a PieceRule. So:

  - a new piece using an existing pattern (an archbishop that slides diagonally, a piece that
    leaps two cells sideways) is a [[pieces]] block in config.toml and *no code at all*;
  - a genuinely new pattern is one PieceRule subclass plus one entry in MOVEMENT_BUILDERS, both
    inside rules/, and nothing anywhere else changes.

A spec is read duck-typed (name/symbol/movement/directions/offsets/promotes_to/
victory_on_capture), so rules/ does not import config — it just reads what it is handed.
"""
from kongfuchess.model.piece import PieceKind
from kongfuchess.rules.piece_rules import (
    CombinedRule, LeapingRule, PawnRule, PieceRuleRegistry, SlidingRule, UnknownMovementError,
)
from kongfuchess.rules.rule_set import ChessRuleSet


def _build_sliding(spec):
    return SlidingRule(spec.directions)


def _build_leaping(spec):
    return LeapingRule(spec.offsets)


def _build_pawn(spec):
    promotes_to = PieceKind(spec.promotes_to) if spec.promotes_to else None
    return PawnRule(promotes_to=promotes_to)


def _build_combined(spec):
    """A piece that both slides and leaps (a queen-plus-knight, say) — patterns compose."""
    return CombinedRule([SlidingRule(spec.directions), LeapingRule(spec.offsets)])


# The movement patterns a piece spec may name. Adding a pattern means adding a builder here.
MOVEMENT_BUILDERS = {
    "slide": _build_sliding,
    "leap": _build_leaping,
    "pawn": _build_pawn,
    "combined": _build_combined,
}


def build_rule(spec):
    """Build the movement rule a single piece spec describes."""
    builder = MOVEMENT_BUILDERS.get(spec.movement)
    if builder is None:
        raise UnknownMovementError(spec.movement)
    return builder(spec)


def build_registry(specs) -> PieceRuleRegistry:
    """The kind -> rule registry for every configured piece."""
    return PieceRuleRegistry({PieceKind(spec.name): build_rule(spec) for spec in specs})


def victory_kinds(specs) -> frozenset:
    """The kinds whose capture wins the game — normally just the king, but that is configuration."""
    return frozenset(PieceKind(spec.name) for spec in specs if spec.victory_on_capture)


def build_rule_set(specs) -> ChessRuleSet:
    """The complete rules in play: how each piece moves, and what ends the game."""
    return ChessRuleSet(build_registry(specs), victory_kinds(specs))
