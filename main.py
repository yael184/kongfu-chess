# main.py
import sys
from board import Board
from engine import GameEngine
from pieces import King, Rook, Bishop, Queen, Knight,EmptyCell

# מיפוי המחרוזות מהקלט לאובייקטים חוקיים
PIECE_MAP = {
    "wK": King("WHITE"), "bK": King("BLACK"),
    "wR": Rook("WHITE"), "bR": Rook("BLACK"),
    "wB": Bishop("WHITE"), "bB": Bishop("BLACK"),
    "wQ": Queen("WHITE"), "bQ": Queen("BLACK"),
    "wN": Knight("WHITE"), "bN": Knight("BLACK")
}

def parse_input(txt: str):
    if "Commands:" not in txt or "Board:" not in txt:
        print("ERROR UNKNOWN_TOKEN")
        sys.exit(0)
        
    board_part, commands_part = txt.split("Commands:")
    board_raw = board_part.replace("Board:", "").strip()
    
    commands = [line.strip() for line in commands_part.strip().split("\n") if line.strip()]
    raw_grid = [line.split() for line in board_raw.split("\n") if line.strip()]
    
    if not raw_grid:
        print("ERROR UNKNOWN_TOKEN")
        sys.exit(0)

    # 1. בדיקת לוח מלבני
    expected_width = len(raw_grid[0])
    for row in raw_grid:
        if len(row) != expected_width:
            print("ERROR ROW_WIDTH_MISMATCH")
            sys.exit(0)

    # 2. המרה לאובייקטים חוקיים ובדיקת כלים לא מוכרים
    grid = []
    for row in raw_grid:
        grid_row = []
        for cell in row:
            if cell == '.':
                grid_row.append(EmptyCell())
                continue
            if cell in PIECE_MAP:
                # יצירת אובייקט חדש מאותו סוג כדי שלא ישתפו הפניה
                cls = PIECE_MAP[cell].__class__
                color = PIECE_MAP[cell].color
                grid_row.append(cls(color))
            else:
                print("ERROR UNKNOWN_TOKEN")
                sys.exit(0)
        grid.append(grid_row)

    return Board(grid), commands


def main(input_stream=None):
    if input_stream is None:
        input_stream = sys.stdin
        
    txt = input_stream.read()
    board, commands = parse_input(txt)
    
    if not board or not commands:
        print("ERROR UNKNOWN_TOKEN")
        return
        
    engine = GameEngine(board)
    for command in commands:
        engine.execute_command(command)

if __name__ == "__main__":
    main()