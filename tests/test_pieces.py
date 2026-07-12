# tests/test_pieces.py
# Unit tests for move legality and piece representation.
import pytest

from board import Board
from pieces import (
    Piece,
    EmptyCell,
    King,
    Rook,
    Bishop,
    Queen,
    Knight,
    Pawn,
)


@pytest.fixture
def empty_board():
    """A completely empty 6x6 board for free-movement tests (no blockers)."""
    grid = [[EmptyCell() for _ in range(6)] for _ in range(6)]
    return Board(grid)


# --- Piece (base class) ---
def test_base_piece_is_valid_move_not_implemented(empty_board):
    base = Piece("WHITE", "?")
    with pytest.raises(NotImplementedError):
        base.is_valid_move(0, 0, 1, 1, empty_board)


def test_piece_str_white_black_and_none():
    assert str(King("WHITE")) == "wK"
    assert str(King("BLACK")) == "bK"
    assert str(EmptyCell()) == "."


# --- EmptyCell ---
def test_empty_cell_defaults():
    empty = EmptyCell()
    assert empty.color is None
    assert empty.symbol == "."
    assert str(empty) == "."


def test_empty_cell_never_valid(empty_board):
    assert EmptyCell().is_valid_move(0, 0, 1, 1, empty_board) is False


# --- King ---
@pytest.mark.parametrize(
    "to_row,to_col",
    [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)],  # all 8 neighbors one step away
)
def test_king_single_step_is_valid(empty_board, to_row, to_col):
    king = King("WHITE")
    assert king.is_valid_move(1, 1, to_row, to_col, empty_board) is True


@pytest.mark.parametrize(
    "to_row,to_col",
    [(1, 1), (3, 1), (1, 3), (3, 3)],  # distance 0 or 2 - illegal
)
def test_king_non_single_step_is_invalid(empty_board, to_row, to_col):
    king = King("WHITE")
    assert king.is_valid_move(1, 1, to_row, to_col, empty_board) is False


# --- Rook ---
def test_rook_straight_moves_valid(empty_board):
    rook = Rook("WHITE")
    assert rook.is_valid_move(0, 0, 0, 5, empty_board) is True   # horizontal
    assert rook.is_valid_move(0, 0, 5, 0, empty_board) is True   # vertical


def test_rook_diagonal_invalid(empty_board):
    assert Rook("WHITE").is_valid_move(0, 0, 3, 3, empty_board) is False


def test_rook_blocked_path_invalid():
    grid = [
        [Rook("WHITE"), King("BLACK"), EmptyCell()],  # blocker at (0,1)
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [EmptyCell(), EmptyCell(), EmptyCell()],
    ]
    board = Board(grid)
    assert Rook("WHITE").is_valid_move(0, 0, 0, 2, board) is False


# --- Bishop ---
def test_bishop_perfect_diagonal_valid(empty_board):
    assert Bishop("BLACK").is_valid_move(2, 2, 5, 5, empty_board) is True


def test_bishop_straight_invalid(empty_board):
    assert Bishop("BLACK").is_valid_move(2, 2, 2, 4, empty_board) is False


def test_bishop_blocked_path_invalid():
    grid = [
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [EmptyCell(), King("WHITE"), EmptyCell()],  # blocker at (1,1)
        [EmptyCell(), EmptyCell(), EmptyCell()],
    ]
    board = Board(grid)
    # From (0,0) to (2,2) passes through the blocked (1,1).
    assert Bishop("WHITE").is_valid_move(0, 0, 2, 2, board) is False


# --- Queen ---
def test_queen_diagonal_and_straight_valid(empty_board):
    queen = Queen("WHITE")
    assert queen.is_valid_move(0, 0, 3, 3, empty_board) is True   # diagonal
    assert queen.is_valid_move(0, 0, 0, 4, empty_board) is True   # horizontal
    assert queen.is_valid_move(0, 0, 4, 0, empty_board) is True   # vertical


def test_queen_knight_shape_invalid(empty_board):
    assert Queen("WHITE").is_valid_move(0, 0, 2, 1, empty_board) is False


def test_queen_blocked_path_invalid():
    grid = [
        [Queen("WHITE"), EmptyCell(), EmptyCell()],
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [King("BLACK"), EmptyCell(), EmptyCell()],
    ]
    # Place a blocker on the vertical path.
    grid[1][0] = King("WHITE")
    board = Board(grid)
    assert Queen("WHITE").is_valid_move(0, 0, 2, 0, board) is False


# --- Knight ---
@pytest.mark.parametrize(
    "to_row,to_col",
    [(2, 1), (1, 2), (2, 3), (3, 2), (0, 1)],
)
def test_knight_l_shapes(empty_board, to_row, to_col):
    knight = Knight("WHITE")
    row_diff = abs(to_row - 2)
    col_diff = abs(to_col - 2)
    is_l = (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)
    assert knight.is_valid_move(2, 2, to_row, to_col, empty_board) is is_l


def test_knight_non_l_invalid(empty_board):
    assert Knight("WHITE").is_valid_move(0, 0, 2, 2, empty_board) is False


# --- Pawn ---
def test_pawn_white_moves_up_into_empty(empty_board):
    pawn = Pawn("WHITE")
    assert pawn.is_valid_move(3, 3, 2, 3, empty_board) is True   # one step up


def test_pawn_black_moves_down_into_empty(empty_board):
    pawn = Pawn("BLACK")
    assert pawn.is_valid_move(1, 3, 2, 3, empty_board) is True   # one step down


def test_pawn_cannot_move_forward_into_occupied():
    grid = [[EmptyCell() for _ in range(3)] for _ in range(3)]
    grid[1][1] = King("BLACK")  # blocks the forward square
    board = Board(grid)
    assert Pawn("WHITE").is_valid_move(2, 1, 1, 1, board) is False


def test_pawn_diagonal_capture_valid():
    grid = [[EmptyCell() for _ in range(3)] for _ in range(3)]
    grid[1][2] = King("BLACK")  # enemy on the diagonal
    board = Board(grid)
    assert Pawn("WHITE").is_valid_move(2, 1, 1, 2, board) is True


def test_pawn_diagonal_into_empty_invalid(empty_board):
    assert Pawn("WHITE").is_valid_move(2, 1, 1, 2, empty_board) is False


def test_pawn_two_squares_from_non_start_row_invalid(empty_board):
    # 6x6 board: white's start row is 5; a two-cell move from row 4 is illegal.
    assert Pawn("WHITE").is_valid_move(4, 1, 2, 1, empty_board) is False


# --- Pawn: two-cell first move from the start row ---
def test_pawn_white_two_squares_from_start_row_valid(empty_board):
    # 6x6 board -> white's start row is 5 (the last row).
    assert Pawn("WHITE").is_valid_move(5, 2, 3, 2, empty_board) is True


def test_pawn_black_two_squares_from_start_row_valid(empty_board):
    # Black's start row is 0 (the first row).
    assert Pawn("BLACK").is_valid_move(0, 2, 2, 2, empty_board) is True


def test_pawn_two_squares_blocked_in_middle_invalid():
    grid = [[EmptyCell() for _ in range(6)] for _ in range(6)]
    grid[4][2] = King("BLACK")  # blocks the middle cell (5 -> 4 -> 3)
    board = Board(grid)
    assert Pawn("WHITE").is_valid_move(5, 2, 3, 2, board) is False


def test_pawn_two_squares_blocked_at_destination_invalid():
    grid = [[EmptyCell() for _ in range(6)] for _ in range(6)]
    grid[3][2] = King("BLACK")  # blocks the destination (5 -> 4 -> 3)
    board = Board(grid)
    assert Pawn("WHITE").is_valid_move(5, 2, 3, 2, board) is False


# --- Pawn: promotion to queen ---
def test_pawn_white_promotes_on_last_row(empty_board):
    promoted = Pawn("WHITE").promoted_piece(0, empty_board)   # row 0 = last row for white
    assert isinstance(promoted, Queen)
    assert promoted.color == "WHITE"


def test_pawn_black_promotes_on_last_row(empty_board):
    promoted = Pawn("BLACK").promoted_piece(5, empty_board)   # row 5 = last row for black on 6x6
    assert isinstance(promoted, Queen)
    assert promoted.color == "BLACK"


def test_pawn_no_promotion_on_middle_row(empty_board):
    assert Pawn("WHITE").promoted_piece(3, empty_board) is None


def test_pawn_sideways_invalid(empty_board):
    assert Pawn("WHITE").is_valid_move(2, 1, 2, 2, empty_board) is False


def test_pawn_backward_invalid(empty_board):
    # White moves up; moving down is illegal.
    assert Pawn("WHITE").is_valid_move(2, 1, 3, 1, empty_board) is False
