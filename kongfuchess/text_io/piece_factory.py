# text_io/piece_factory.py
from kongfuchess.model.piece import Piece


class PieceFactory:
    """Creates model pieces, assigning a unique, stable id at creation time.

    Ids are handed out in creation order, so identical input produces identical ids and no two
    pieces ever share an id. Tokens are not its business — that is TokenCodec's — so this class has
    exactly one job.
    """

    def __init__(self):
        self._next_id = 0

    def create(self, color, kind, cell):
        """Create a Piece of the given color/kind at `cell` with a fresh unique id."""
        self._next_id += 1
        return Piece(id=self._next_id, color=color, kind=kind, cell=cell)
