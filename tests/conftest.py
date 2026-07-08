# tests/conftest.py
# פיקסטורות משותפות לכל קבצי הבדיקה שבתיקיית tests/
import pytest

from board import Board
from engine import GameEngine
from pieces import King, EmptyCell


@pytest.fixture
def valid_grid():
    """לוח 3x3 תקין עם שני מלכים לבנים ומלך שחור."""
    return [
        [King("WHITE"), EmptyCell(), King("BLACK")],
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [EmptyCell(), King("WHITE"), EmptyCell()],
    ]


@pytest.fixture
def sample_board(valid_grid):
    return Board(valid_grid)


@pytest.fixture
def sample_engine(sample_board):
    return GameEngine(sample_board)


@pytest.fixture
def make_board():
    """
    מפעל (factory) לבניית לוח מתוך מטריצה של תווים, למשל:
        make_board([["wR", ".", "bB"],
                    [".",  ".", "."]])
    מקל על בניית תרחישים ספציפיים בבדיקות.
    """
    from registry import create_piece_from_token

    def _build(token_grid):
        grid = [[create_piece_from_token(tok) for tok in row] for row in token_grid]
        return Board(grid)

    return _build
