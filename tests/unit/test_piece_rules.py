# tests/unit/test_piece_rules.py
from model.board import Board
from model.piece import Piece, Color, PieceKind
from model.position import Position
from rules.piece_rules import (
    RookRule, BishopRule, QueenRule, KnightRule, KingRule, PawnRule, rule_for, promotion_kind,
)


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def board_with(width, height, *pieces):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return board


# --- Rook ---
def test_rook_moves_across_empty_row_and_column():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 2, 2)
    board = board_with(5, 5, rook)
    expected = {Position(2, c) for c in (0, 1, 3, 4)} | {Position(r, 2) for r in (0, 1, 3, 4)}
    assert RookRule().legal_destinations(board, rook) == expected


def test_rook_stops_before_a_friendly_blocker():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 2)
    board = board_with(4, 1, rook, friend)  # single row, cols 0..3
    # Reaches (0,1); blocked by the friend at (0,2); cannot reach (0,2) or (0,3).
    assert RookRule().legal_destinations(board, rook) == {Position(0, 1)}


def test_rook_captures_an_enemy_blocker_but_does_not_pass_it():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(4, 1, rook, enemy)
    # (0,1) empty and (0,2) enemy are legal; (0,3) behind the enemy is not.
    assert RookRule().legal_destinations(board, rook) == {Position(0, 1), Position(0, 2)}


# --- Bishop ---
def test_bishop_moves_diagonally_and_not_straight():
    bishop = pc("b", Color.WHITE, PieceKind.BISHOP, 2, 2)
    board = board_with(5, 5, bishop)
    expected = {
        Position(3, 3), Position(4, 4),
        Position(1, 1), Position(0, 0),
        Position(3, 1), Position(4, 0),
        Position(1, 3), Position(0, 4),
    }
    dests = BishopRule().legal_destinations(board, bishop)
    assert dests == expected
    assert Position(2, 3) not in dests  # straight is not a bishop move
    assert Position(3, 2) not in dests


# --- Queen ---
def test_queen_combines_rook_and_bishop_movement():
    queen = pc("q", Color.WHITE, PieceKind.QUEEN, 2, 2)
    board = board_with(5, 5, queen)
    rook_view = pc("q", Color.WHITE, PieceKind.ROOK, 2, 2)
    bishop_view = pc("q", Color.WHITE, PieceKind.BISHOP, 2, 2)
    expected = (RookRule().legal_destinations(board, rook_view)
                | BishopRule().legal_destinations(board, bishop_view))
    assert QueenRule().legal_destinations(board, queen) == expected


# --- Knight ---
def test_knight_jumps_over_blockers():
    knight = pc("n", Color.WHITE, PieceKind.KNIGHT, 2, 2)
    # Surround the knight with friendly blockers on adjacent (non-L) cells.
    around = [(1, 2), (3, 2), (2, 1), (2, 3), (1, 1), (1, 3), (3, 1), (3, 3)]
    blockers = [pc(f"b{i}", Color.WHITE, PieceKind.PAWN, r, c) for i, (r, c) in enumerate(around)]
    board = board_with(5, 5, knight, *blockers)
    expected = {
        Position(0, 1), Position(0, 3), Position(4, 1), Position(4, 3),
        Position(1, 0), Position(3, 0), Position(1, 4), Position(3, 4),
    }
    assert KnightRule().legal_destinations(board, knight) == expected


def test_knight_excludes_friendly_landing_but_allows_enemy():
    knight = pc("n", Color.WHITE, PieceKind.KNIGHT, 2, 2)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 1)   # an L target, friendly -> excluded
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 3)    # an L target, enemy -> allowed
    board = board_with(5, 5, knight, friend, enemy)
    dests = KnightRule().legal_destinations(board, knight)
    assert Position(0, 1) not in dests
    assert Position(0, 3) in dests


# --- King ---
def test_king_moves_one_cell_only():
    king = pc("k", Color.WHITE, PieceKind.KING, 2, 2)
    board = board_with(5, 5, king)
    expected = {Position(r, c) for r in (1, 2, 3) for c in (1, 2, 3)} - {Position(2, 2)}
    assert KingRule().legal_destinations(board, king) == expected


def test_king_is_clipped_at_the_board_edge():
    king = pc("k", Color.WHITE, PieceKind.KING, 0, 0)
    board = board_with(5, 5, king)
    assert KingRule().legal_destinations(board, king) == {Position(0, 1), Position(1, 0), Position(1, 1)}


# --- Pawn --- (board_with(3, 5): white start row = 3, black start row = 1; row 2 is neither)
def test_white_pawn_moves_one_row_up_into_empty():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 2, 1)
    board = board_with(3, 5, pawn)  # cols 0..2, rows 0..4
    assert PawnRule().legal_destinations(board, pawn) == {Position(1, 1)}


def test_black_pawn_moves_one_row_down_into_empty():
    pawn = pc("p", Color.BLACK, PieceKind.PAWN, 2, 1)
    board = board_with(3, 5, pawn)
    assert PawnRule().legal_destinations(board, pawn) == {Position(3, 1)}


def test_pawn_cannot_move_forward_into_an_occupied_cell():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 2, 1)
    blocker = pc("b", Color.BLACK, PieceKind.PAWN, 1, 1)  # directly ahead
    board = board_with(3, 5, pawn, blocker)
    assert PawnRule().legal_destinations(board, pawn) == set()


def test_pawn_captures_one_diagonal_step_forward_only_enemies():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 2, 1)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 1, 2)   # diagonal forward-right -> capturable
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 1, 0)  # diagonal forward-left -> not capturable
    board = board_with(3, 5, pawn, enemy, friend)
    assert PawnRule().legal_destinations(board, pawn) == {Position(1, 1), Position(1, 2)}


def test_pawn_does_not_move_diagonally_into_empty():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 2, 1)
    board = board_with(3, 5, pawn)
    dests = PawnRule().legal_destinations(board, pawn)
    assert Position(1, 0) not in dests
    assert Position(1, 2) not in dests


def test_white_pawn_has_a_two_step_move_from_the_start_row():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 3, 1)  # white start row on a height-5 board
    board = board_with(3, 5, pawn)
    assert PawnRule().legal_destinations(board, pawn) == {Position(2, 1), Position(1, 1)}


def test_black_pawn_has_a_two_step_move_from_the_start_row():
    pawn = pc("p", Color.BLACK, PieceKind.PAWN, 1, 1)  # black start row
    board = board_with(3, 5, pawn)
    assert PawnRule().legal_destinations(board, pawn) == {Position(2, 1), Position(3, 1)}


def test_pawn_has_no_two_step_move_off_the_start_row():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 2, 1)  # not the start row (3)
    board = board_with(3, 5, pawn)
    dests = PawnRule().legal_destinations(board, pawn)
    assert dests == {Position(1, 1)}


def test_two_step_move_blocked_by_a_piece_in_the_middle():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 3, 1)   # start row
    blocker = pc("b", Color.BLACK, PieceKind.PAWN, 2, 1)  # the intermediate cell
    board = board_with(3, 5, pawn, blocker)
    assert PawnRule().legal_destinations(board, pawn) == set()


# --- promotion ---
def test_white_pawn_promotes_on_the_last_row():
    board = board_with(3, 3, pc("p", Color.WHITE, PieceKind.PAWN, 0, 1))  # row 0 = last for white
    assert promotion_kind(board.piece_at(Position(0, 1)), board) == PieceKind.QUEEN


def test_black_pawn_promotes_on_the_last_row():
    board = board_with(3, 3, pc("p", Color.BLACK, PieceKind.PAWN, 2, 1))  # row height-1 = last for black
    assert promotion_kind(board.piece_at(Position(2, 1)), board) == PieceKind.QUEEN


def test_pawn_off_the_last_row_does_not_promote():
    board = board_with(3, 3, pc("p", Color.WHITE, PieceKind.PAWN, 1, 1))
    assert promotion_kind(board.piece_at(Position(1, 1)), board) is None


def test_non_pawn_never_promotes():
    board = board_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 1))
    assert promotion_kind(board.piece_at(Position(0, 1)), board) is None


# --- registry ---
def test_rule_for_maps_each_kind_to_its_rule():
    assert isinstance(rule_for(PieceKind.ROOK), RookRule)
    assert isinstance(rule_for(PieceKind.BISHOP), BishopRule)
    assert isinstance(rule_for(PieceKind.QUEEN), QueenRule)
    assert isinstance(rule_for(PieceKind.KNIGHT), KnightRule)
    assert isinstance(rule_for(PieceKind.KING), KingRule)
    assert isinstance(rule_for(PieceKind.PAWN), PawnRule)
