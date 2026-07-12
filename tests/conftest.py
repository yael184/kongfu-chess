# tests/conftest.py
# Shared fixtures for all test files under tests/.
import pytest

from board import Board
from engine import GameEngine
from pieces import King, EmptyCell


@pytest.fixture
def valid_grid():
    """A valid 3x3 board with two white kings and one black king."""
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
    Factory that builds a board from a matrix of tokens, e.g.:
        make_board([["wR", ".", "bB"],
                    [".",  ".", "."]])
    Makes it easy to set up specific scenarios in tests.
    """
    from registry import create_piece_from_token

    def _build(token_grid):
        grid = [[create_piece_from_token(tok) for tok in row] for row in token_grid]
        return Board(grid)

    return _build
