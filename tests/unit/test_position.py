# tests/unit/test_position.py
from model.position import Position


def test_positions_with_same_row_and_col_are_equal():
    assert Position(1, 2) == Position(1, 2)


def test_positions_with_different_row_or_col_are_not_equal():
    assert Position(1, 2) != Position(3, 2)
    assert Position(1, 2) != Position(1, 3)


def test_position_has_readable_repr():
    assert repr(Position(1, 2)) == "Position(row=1, col=2)"


def test_position_is_hashable_and_usable_as_a_key():
    cells = {Position(0, 0): "a", Position(1, 1): "b"}
    assert cells[Position(0, 0)] == "a"
