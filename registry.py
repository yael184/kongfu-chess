# registry.py
import config
from pieces import King, Rook, Bishop, Queen, Knight, Pawn, EmptyCell

# Maps a piece token (symbol) to its corresponding class.
PIECE_CLASSES = {
    "K": King,
    "R": Rook,
    "B": Bishop,
    "Q": Queen,
    "N": Knight,
    "P": Pawn
}

def create_piece_from_token(token: str):
    """Factory that dynamically converts an input token into a piece object, keeping parsing decoupled from the piece classes."""
    if token == config.EMPTY_TOKEN:
        return EmptyCell()

    if len(token) != 2:
        return None

    color_prefix, symbol_char = token[0], token[1]

    if color_prefix == "w":
        color = config.COLOR_WHITE
    elif color_prefix == "b":
        color = config.COLOR_BLACK
    else:
        return None

    if symbol_char in PIECE_CLASSES:
        return PIECE_CLASSES[symbol_char](color)
        
    return None