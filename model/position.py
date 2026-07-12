# model/position.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """A board cell (row, col) — a pure value object.

    It represents a logical cell, not pixels. It knows nothing about board size, rendering,
    movement rules, or input coordinates: board bounds belong to Board. Being a frozen
    dataclass it is immutable, compares by value, is hashable (usable as a dict key), and has
    a readable repr for clear assertion failures.
    """
    row: int
    col: int
