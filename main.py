# main.py
import sys
from board import Board
from engine import GameEngine

# סט הכלים החוקיים המותרים בלוח
VALID_PIECES = {".", "wK", "bK","wR"} 
# הערה: אם יש כלים נוספים בשחמט (כמו wQ, bP וכו'), פשוט תוסיפי אותם לסט כאן.

def parse_input(txt: str):
    """מפרק את הקלט ללוח ולרשימת פקודות, כולל ולידציה של הלוח."""
    if "Commands:" not in txt or "Board:" not in txt:
        print("ERROR UNKNOWN_TOKEN")
        sys.exit(0)
        
    board_part, commands_part = txt.split("Commands:")
    board_raw = board_part.replace("Board:", "").strip()
    
    commands = [line.strip() for line in commands_part.strip().split("\n") if line.strip()]
    grid = [line.split() for line in board_raw.split("\n") if line.strip()]
    
    if not grid:
        print("ERROR UNKNOWN_TOKEN")
        sys.exit(0)

    # 1. בדיקה האם הלוח מלבני (כל השורות באותו אורך)
    expected_width = len(grid[0])
    for row in grid:
        if len(row) != expected_width:
            print("ERROR ROW_WIDTH_MISMATCH")
            sys.exit(0)

    # 2. בדיקה האם יש כלים לא מוכרים בלוח
    for row in grid:
        for cell in row:
            if cell not in VALID_PIECES:
                print("ERROR UNKNOWN_TOKEN")
                sys.exit(0)

    return Board(grid), commands


def main(input_stream=None):
    # אם לא הופעל עם זרם מסוים (למשל בריצה רגילה), נשתמש ב-sys.stdin
    if input_stream is None:
        input_stream = sys.stdin
        
    # קריאת כל הקלט מהזרם שהוזרק
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
    