# tests/unit/test_board.py
import pytest

from kongfuchess.model.board import Board, DuplicateOccupancyError, OutOfBoundsError, PieceNotFoundError
from kongfuchess.model.piece import Piece, Color, PieceKind
from kongfuchess.model.position import Position


def make_piece(piece_id, cell, kind=PieceKind.PAWN, color=Color.WHITE):
    return Piece(id=piece_id, color=color, kind=kind, cell=cell)


def test_board_dimensions_are_reported():
    board = Board(width=3, height=2)
    assert board.width == 3
    assert board.height == 2


def test_empty_cell_returns_no_piece():
    board = Board(3, 3)
    assert board.piece_at(Position(0, 0)) is None


def test_occupied_cell_returns_the_correct_piece():
    board = Board(3, 3)
    piece = make_piece("p1", Position(1, 1))
    board.add_piece(piece)
    assert board.piece_at(Position(1, 1)) is piece


def test_adding_two_pieces_to_the_same_cell_fails():
    board = Board(3, 3)
    board.add_piece(make_piece("p1", Position(1, 1)))
    with pytest.raises(DuplicateOccupancyError):
        board.add_piece(make_piece("p2", Position(1, 1)))


def test_moving_a_piece_updates_source_and_destination():
    board = Board(3, 3)
    piece = make_piece("p1", Position(0, 0))
    board.add_piece(piece)
    board.move_piece(Position(0, 0), Position(2, 2))
    assert board.piece_at(Position(0, 0)) is None
    assert board.piece_at(Position(2, 2)) is piece
    assert piece.cell == Position(2, 2)


def test_removing_a_piece_clears_its_cell():
    board = Board(3, 3)
    piece = make_piece("p1", Position(1, 2))
    board.add_piece(piece)
    board.remove_piece(piece)
    assert board.piece_at(Position(1, 2)) is None


def test_is_within_bounds_respects_width_and_height():
    board = Board(width=3, height=2)  # rows 0..1, cols 0..2
    assert board.is_within_bounds(Position(0, 0)) is True
    assert board.is_within_bounds(Position(1, 2)) is True
    assert board.is_within_bounds(Position(2, 0)) is False  # row out of range
    assert board.is_within_bounds(Position(0, 3)) is False  # col out of range
    assert board.is_within_bounds(Position(-1, 0)) is False


def test_adding_out_of_bounds_piece_fails():
    board = Board(2, 2)
    with pytest.raises(OutOfBoundsError):
        board.add_piece(make_piece("p1", Position(5, 5)))


def test_removing_a_piece_not_on_the_board_fails():
    board = Board(3, 3)
    with pytest.raises(PieceNotFoundError):
        board.remove_piece(make_piece("ghost", Position(0, 0)))
