# main.py
import sys
from board import Board
from engine import GameEngine
from registry import create_piece_from_token

def parse_input(txt: str):
    """Parse a board+commands document into a Board and a list of command strings."""
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

    # Ensure the board is rectangular (all rows share the same width).
    expected_width = len(raw_grid[0])
    for row in raw_grid:
        if len(row) != expected_width:
            print("ERROR ROW_WIDTH_MISMATCH")
            sys.exit(0)

    # Convert each token via the registry factory.
    grid = []
    for row in raw_grid:
        grid_row = []
        for cell in row:
            piece = create_piece_from_token(cell)
            if piece is None:
                print("ERROR UNKNOWN_TOKEN")
                sys.exit(0)
            grid_row.append(piece)
        grid.append(grid_row)

    return Board(grid), commands

def main(input_stream=None):
    """Read a document from input_stream (defaults to stdin), build the engine, and run every command."""
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