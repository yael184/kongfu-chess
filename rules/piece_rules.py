# rules/piece_rules.py
from model.piece import Color, PieceKind
from model.position import Position

# Sliding directions, reused by the sliding pieces.
_ROOK_DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
_BISHOP_DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
# Knight L-shaped offsets and the eight King neighbors.
_KNIGHT_OFFSETS = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
_KING_OFFSETS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]


def _slide(board, piece, directions):
    """Slide from the piece's cell along each direction until blocked.

    An empty cell is a legal destination and travel continues; a friendly piece blocks and is
    excluded; an enemy piece is a legal (capturable) destination but blocks travel past it.
    """
    destinations = set()
    for row_step, col_step in directions:
        row = piece.cell.row + row_step
        col = piece.cell.col + col_step
        while board.is_within_bounds(Position(row, col)):
            cell = Position(row, col)
            occupant = board.piece_at(cell)
            if occupant is None:
                destinations.add(cell)
            else:
                if occupant.color != piece.color:
                    destinations.add(cell)
                break
            row += row_step
            col += col_step
    return destinations


def _jump(board, piece, offsets):
    """Return in-bounds offset cells that are empty or enemy-occupied (friendly cells excluded)."""
    destinations = set()
    for row_step, col_step in offsets:
        cell = Position(piece.cell.row + row_step, piece.cell.col + col_step)
        if not board.is_within_bounds(cell):
            continue
        occupant = board.piece_at(cell)
        if occupant is None or occupant.color != piece.color:
            destinations.add(cell)
    return destinations


class PieceRule:
    """Interface for a piece type's movement rule. Stateless: it stores no selection, motion,
    elapsed time, or game state — it only computes legal destinations from a board and a piece."""

    def legal_destinations(self, board, piece):
        """Return the set of Positions this piece may move to (captures included, no mutation)."""
        raise NotImplementedError


class RookRule(PieceRule):
    """Horizontal and vertical sliding until blocked."""

    def legal_destinations(self, board, piece):
        return _slide(board, piece, _ROOK_DIRECTIONS)


class BishopRule(PieceRule):
    """Diagonal sliding until blocked."""

    def legal_destinations(self, board, piece):
        return _slide(board, piece, _BISHOP_DIRECTIONS)


class QueenRule(PieceRule):
    """Rook movement plus bishop movement."""

    def __init__(self):
        self._rook = RookRule()
        self._bishop = BishopRule()

    def legal_destinations(self, board, piece):
        return self._rook.legal_destinations(board, piece) | self._bishop.legal_destinations(board, piece)


class KnightRule(PieceRule):
    """L-shaped jumps, ignoring blockers."""

    def legal_destinations(self, board, piece):
        return _jump(board, piece, _KNIGHT_OFFSETS)


class KingRule(PieceRule):
    """One square in any direction."""

    def legal_destinations(self, board, piece):
        return _jump(board, piece, _KING_OFFSETS)


def _pawn_forward(color):
    """Row delta a pawn advances each step: white moves up (-1), black down (+1)."""
    return -1 if color == Color.WHITE else 1


def _pawn_start_row(color, board):
    """The pawn's starting rank (second from its own edge): white = height-2, black = 1."""
    return board.height - 2 if color == Color.WHITE else 1


def promotion_kind(piece, board):
    """The kind a piece promotes to on its current cell, or None. A pawn on its last row -> queen."""
    if piece.kind != PieceKind.PAWN:
        return None
    last_row = 0 if piece.color == Color.WHITE else board.height - 1
    return PieceKind.QUEEN if piece.cell.row == last_row else None


class PawnRule(PieceRule):
    """Pawn movement: one step forward into an empty cell, a two-step first move from the start
    row, and a one-step diagonal capture. White moves up, black down. No en passant.
    """

    def legal_destinations(self, board, piece):
        forward = _pawn_forward(piece.color)
        origin = piece.cell
        row = origin.row + forward
        destinations = set()

        ahead = Position(row, origin.col)
        if board.is_within_bounds(ahead) and board.piece_at(ahead) is None:
            destinations.add(ahead)
            # Two-step first move: only from the start row and only if both cells are empty.
            if origin.row == _pawn_start_row(piece.color, board):
                double = Position(origin.row + 2 * forward, origin.col)
                if board.is_within_bounds(double) and board.piece_at(double) is None:
                    destinations.add(double)

        for col_step in (-1, 1):
            diagonal = Position(row, origin.col + col_step)
            if not board.is_within_bounds(diagonal):
                continue
            occupant = board.piece_at(diagonal)
            if occupant is not None and occupant.color != piece.color:
                destinations.add(diagonal)

        return destinations


# The single rule instance per piece kind (rules are stateless, so instances are shareable).
RULES_BY_KIND = {
    PieceKind.ROOK: RookRule(),
    PieceKind.BISHOP: BishopRule(),
    PieceKind.QUEEN: QueenRule(),
    PieceKind.KNIGHT: KnightRule(),
    PieceKind.KING: KingRule(),
    PieceKind.PAWN: PawnRule(),
}


def rule_for(kind):
    """Return the movement rule for a PieceKind."""
    return RULES_BY_KIND[kind]
