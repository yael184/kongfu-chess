# tests/test_board.py
# Tests for the Board class.
from board import Board
from pieces import King, EmptyCell


# --- is_within_bounds ---
def test_within_bounds_inside(sample_board):
    assert sample_board.is_within_bounds(0, 0) is True
    assert sample_board.is_within_bounds(2, 2) is True


def test_within_bounds_outside(sample_board):
    assert sample_board.is_within_bounds(-1, 0) is False
    assert sample_board.is_within_bounds(0, -1) is False
    assert sample_board.is_within_bounds(3, 0) is False
    assert sample_board.is_within_bounds(0, 3) is False


# --- get_cell ---
def test_get_cell_returns_piece(sample_board):
    assert str(sample_board.get_cell(0, 0)) == "wK"
    assert isinstance(sample_board.get_cell(0, 1), EmptyCell)


def test_get_cell_out_of_bounds_returns_empty(sample_board):
    assert isinstance(sample_board.get_cell(99, 99), EmptyCell)


# --- is_empty ---
def test_is_empty(sample_board):
    assert sample_board.is_empty(0, 0) is False
    assert sample_board.is_empty(0, 1) is True


def test_is_empty_out_of_bounds_true(sample_board):
    # Out of bounds returns an EmptyCell, so it counts as empty.
    assert sample_board.is_empty(99, 99) is True


# --- get_piece_color ---
def test_get_piece_color(sample_board):
    assert sample_board.get_piece_color(0, 0) == "WHITE"
    assert sample_board.get_piece_color(0, 2) == "BLACK"
    assert sample_board.get_piece_color(0, 1) is None


def test_get_piece_color_out_of_bounds_none(sample_board):
    assert sample_board.get_piece_color(99, 99) is None


# --- select_piece ---
def test_select_piece(sample_board):
    assert sample_board.selected_piece is None
    sample_board.select_piece(2, 1)
    assert sample_board.selected_piece == (2, 1)


# --- move_piece ---
def test_move_piece_moves_and_clears_source(sample_board):
    sample_board.select_piece(0, 0)
    sample_board.move_piece(0, 0, 1, 0)
    assert str(sample_board.grid[1][0]) == "wK"
    assert isinstance(sample_board.grid[0][0], EmptyCell)
    assert sample_board.selected_piece is None


def test_move_piece_capture_overwrites_target():
    grid = [
        [King("WHITE"), King("BLACK")],
        [EmptyCell(), EmptyCell()],
    ]
    board = Board(grid)
    board.move_piece(0, 0, 0, 1)  # capture
    assert str(board.grid[0][1]) == "wK"
    assert isinstance(board.grid[0][0], EmptyCell)


# --- __str__ ---
def test_board_str_format(sample_board):
    expected = "wK . bK\n. . .\n. wK ."
    assert str(sample_board) == expected
