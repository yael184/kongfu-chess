# model/game_state.py
from dataclasses import dataclass

from model.board import Board


@dataclass
class GameState:
    """The mutable game state: the board plus the game-over flag.

    A plain data holder — it contains no rules, timing, rendering, or input logic. `game_over`
    is set by GameEngine when a king capture is reported from arrival resolution.
    """
    board: Board
    game_over: bool = False
