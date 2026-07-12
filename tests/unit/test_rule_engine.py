# tests/unit/test_rule_engine.py
from model.board import Board
from model.piece import Piece, Color, PieceKind
from model.position import Position
from rules.rule_engine import (
    RuleEngine, MoveValidation,
    REASON_OK, REASON_OUTSIDE_BOARD, REASON_EMPTY_SOURCE,
    REASON_FRIENDLY_DESTINATION, REASON_ILLEGAL_PIECE_MOVE,
)


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def board_with(width, height, *pieces):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return board


def test_valid_move_is_ok():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    result = RuleEngine().validate_move(board, Position(0, 0), Position(0, 2))
    assert result == MoveValidation(True, REASON_OK)


def test_destination_outside_board_is_rejected():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    result = RuleEngine().validate_move(board, Position(0, 0), Position(0, 5))
    assert result.is_valid is False
    assert result.reason == REASON_OUTSIDE_BOARD


def test_source_outside_board_is_rejected():
    board = board_with(3, 3)
    result = RuleEngine().validate_move(board, Position(9, 9), Position(0, 0))
    assert result.reason == REASON_OUTSIDE_BOARD


def test_empty_source_is_rejected():
    board = board_with(3, 3)
    result = RuleEngine().validate_move(board, Position(0, 0), Position(0, 1))
    assert result.is_valid is False
    assert result.reason == REASON_EMPTY_SOURCE


def test_friendly_destination_is_rejected():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 1)
    board = board_with(3, 3, rook, friend)
    result = RuleEngine().validate_move(board, Position(0, 0), Position(0, 1))
    assert result.reason == REASON_FRIENDLY_DESTINATION


def test_illegal_piece_move_is_rejected():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    # A diagonal is not a rook move.
    result = RuleEngine().validate_move(board, Position(0, 0), Position(2, 2))
    assert result.reason == REASON_ILLEGAL_PIECE_MOVE


def test_capturing_an_enemy_destination_is_a_valid_move():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, enemy)
    result = RuleEngine().validate_move(board, Position(0, 0), Position(0, 2))
    assert result.is_valid is True
    assert result.reason == REASON_OK


def test_rule_engine_does_not_mutate_the_board():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, enemy)
    RuleEngine().validate_move(board, Position(0, 0), Position(0, 2))
    assert board.piece_at(Position(0, 0)) is rook
    assert board.piece_at(Position(0, 2)) is enemy
    assert rook.cell == Position(0, 0)
