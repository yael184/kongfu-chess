# registry.py
import config
from pieces import King, Rook, Bishop, Queen, Knight, Pawn, EmptyCell

# מילון הממפה את תו הכלי (Symbol) למחלקה (Class) המתאימה לו
PIECE_CLASSES = {
    "K": King,
    "R": Rook,
    "B": Bishop,
    "Q": Queen,
    "N": Knight,
    "P": Pawn
}

def create_piece_from_token(token: str):
    """מפעל (Factory) שממיר מחרוזת קלט לאובייקט כלי בצורה דינמית ומבודדת."""
    if token == config.EMPTY_TOKEN:
        return EmptyCell()
        
    if len(token) != 2:
        return None
        
    color_prefix, symbol_char = token[0], token[1]
    
    # קביעת הצבע
    if color_prefix == "w":
        color = config.COLOR_WHITE
    elif color_prefix == "b":
        color = config.COLOR_BLACK
    else:
        return None
        
    # שליפת המחלקה המתאימה ויצירת האובייקט
    if symbol_char in PIECE_CLASSES:
        return PIECE_CLASSES[symbol_char](color)
        
    return None