# model/arrival.py
from dataclasses import dataclass

from model.board_view import BoardView
from model.piece import Piece
from model.position import Position


@dataclass(frozen=True)
class ArrivalContext:
    """A piece has reached a cell — everything a rule needs to decide what that means.

    This is the *question* half of the contract between the layer that owns time and the layer
    that owns rules; model/effects.py is the *answer* half. Both live here in the model, neutral
    ground, so that neither layer has to import the other: realtime/ describes an arrival, rules/
    replies with effects, and neither knows the other exists.

    `destination_is_protected` is the one fact only the time model can supply — an enemy is
    mid-dodge on the destination and has not landed yet. It states a situation, not an outcome;
    what a protected destination *does* to an arriving piece is entirely a rules decision.
    """
    board: BoardView
    piece: Piece
    destination: Position
    destination_is_protected: bool = False
