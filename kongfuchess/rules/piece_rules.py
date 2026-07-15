# rules/piece_rules.py
from kongfuchess.model.piece import Color
from kongfuchess.model.position import Position


class UnknownPieceKindError(Exception):
    """Raised when a piece's kind has no movement rule registered for it."""


class UnknownMovementError(Exception):
    """Raised when a piece is configured with a movement pattern no builder knows how to make."""


class PieceRule:
    """Interface for a piece type's movement rule. Stateless: it stores no selection, motion,
    elapsed time, or game state — it only answers questions about a board and a piece.

    This is the strategy every piece type plugs into, and it is the whole extension point for new
    pieces: a rule may move a piece by any pattern at all, and may turn it into anything on arrival
    (or nothing), without a single caller changing.
    """

    def legal_destinations(self, board, piece):
        """Return the set of Positions this piece may move to (captures included, no mutation)."""
        raise NotImplementedError

    def kind_after_arrival(self, board, piece, cell):
        """The kind this piece becomes upon arriving at `cell`, or None to stay as it is.

        Promotion is expressed here rather than anywhere downstream, so a variant where a pawn
        reverses direction instead of promoting — or where a rook becomes something on the last
        row — is a change to a rule and to nothing else. Note `cell` is where the piece is
        *arriving*, which is not yet piece.cell: rules are pure and run before the board moves.
        """
        return None


class SlidingRule(PieceRule):
    """Slides along each of its directions until blocked — the rook, bishop and queen pattern.

    The directions are injected, so rook/bishop/queen are not three classes but three
    configurations of this one, and a piece that slides only sideways (or only forwards) needs no
    new code at all.

    An empty cell is a legal destination and travel continues; a friendly piece blocks and is
    excluded; an enemy piece is a legal (capturable) destination but blocks travel past it.
    """

    def __init__(self, directions):
        self._directions = tuple(directions)

    def legal_destinations(self, board, piece):
        destinations = set()
        for row_step, col_step in self._directions:
            row = piece.cell.row + row_step
            col = piece.cell.col + col_step
            while board.is_within_bounds(Position(row, col)):
                cell = Position(row, col)
                occupant = board.piece_at(cell)
                if occupant is None:
                    destinations.add(cell)
                else:
                    if piece.is_enemy_of(occupant):
                        destinations.add(cell)
                    break
                row += row_step
                col += col_step
        return destinations


class LeapingRule(PieceRule):
    """Jumps to fixed offsets, ignoring blockers — the knight and king pattern.

    In-bounds offset cells that are empty or enemy-occupied are legal; friendly cells are not.
    """

    def __init__(self, offsets):
        self._offsets = tuple(offsets)

    def legal_destinations(self, board, piece):
        destinations = set()
        for row_step, col_step in self._offsets:
            cell = Position(piece.cell.row + row_step, piece.cell.col + col_step)
            if not board.is_within_bounds(cell):
                continue
            occupant = board.piece_at(cell)
            if occupant is None or piece.is_enemy_of(occupant):
                destinations.add(cell)
        return destinations


def _pawn_forward(color):
    """Row delta a pawn advances each step: white moves up (-1), black down (+1)."""
    return -1 if color == Color.WHITE else 1


def _pawn_start_row(color, board):
    """The pawn's starting rank (second from its own edge): white = height-2, black = 1."""
    return board.height - 2 if color == Color.WHITE else 1


def _pawn_last_row(color, board):
    """The far edge a pawn promotes on: white = 0, black = height-1."""
    return 0 if color == Color.WHITE else board.height - 1


class PawnRule(PieceRule):
    """Pawn movement: one step forward into an empty cell, a two-step first move from the start
    row, and a one-step diagonal capture. White moves up, black down. No en passant.

    On reaching the far edge the pawn becomes `promotes_to` — injected, so what a pawn turns into
    (or whether it turns into anything at all) is configuration, not a constant buried in a rule.
    """

    def __init__(self, promotes_to=None):
        self._promotes_to = promotes_to

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
            if piece.is_enemy_of(board.piece_at(diagonal)):
                destinations.add(diagonal)

        return destinations

    def kind_after_arrival(self, board, piece, cell):
        """A pawn landing on the far edge promotes."""
        if self._promotes_to is None:
            return None
        return self._promotes_to if cell.row == _pawn_last_row(piece.color, board) else None


class CombinedRule(PieceRule):
    """Every destination of each of several rules — how a queen is a rook plus a bishop.

    It lets configuration compose new pieces out of existing patterns (an archbishop is a bishop
    plus a knight) with no new code.
    """

    def __init__(self, rules):
        self._rules = tuple(rules)

    def legal_destinations(self, board, piece):
        return set().union(*(rule.legal_destinations(board, piece) for rule in self._rules))


class PieceRuleRegistry:
    """The movement rule for each piece kind in play.

    Built at the composition root from configuration and injected, so which pieces exist — and how
    each one moves — is decided outside the code that uses them. Nothing reaches into the mapping
    itself; callers ask rule_for(kind).
    """

    def __init__(self, rules_by_kind):
        self._rules_by_kind = dict(rules_by_kind)

    def rule_for(self, kind):
        """Return the movement rule for a piece kind."""
        rule = self._rules_by_kind.get(kind)
        if rule is None:
            raise UnknownPieceKindError(kind)
        return rule

    def kinds(self):
        """Every piece kind this registry knows how to move."""
        return tuple(self._rules_by_kind)
