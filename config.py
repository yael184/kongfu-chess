# config.py

CELL_SIZE = 100

# Travel speed: how many milliseconds it takes a piece to cross a single cell.
# A move's arrival time = (number of cells on the route) * MS_PER_CELL.
MS_PER_CELL = 1000

# Duration of a "jump in place" (Dodge/Jump) in milliseconds. While airborne a
# piece is protected: an attacker that arrives during this window is eaten by the jumper.
JUMP_DURATION_MS = 1000

# Global color constants
COLOR_WHITE = "WHITE"
COLOR_BLACK = "BLACK"

EMPTY_TOKEN = "."
