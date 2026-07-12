# engine.py
from board import Board
from pieces import Piece, King
import config


class PendingMove:
    """מהלך שיצא לדרך ועדיין 'בטיסה'. הכלי נשאר בתא המקור עד arrival_ms."""
    def __init__(self, from_row, from_col, to_row, to_col, arrival_ms):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.arrival_ms = arrival_ms


class GameEngine:
    def __init__(self, board: Board):
        self.board = board
        self.game_clock_ms = 0
        self.pending_moves = []  # מהלכים שבתהליך תנועה, ממתינים לזמן הגעתם
        self.game_over = False   # נדלק כאשר מלך נאכל; מרגע זה מהלכים מתעלמים

    def execute_command(self, command_str: str):
        parts = command_str.strip().split()
        if not parts:
            return

        command_type = parts[0]

        if command_type == "click" and len(parts) == 3:
            self._handle_click(int(parts[1]), int(parts[2]))
        elif command_type == "wait" and len(parts) == 2:
            self._handle_wait(int(parts[1]))
        elif command_str.strip() == "print board":
            self._handle_print_board()
        else:
            print(f"ERROR: Unknown command '{command_str}'")

    def _handle_click(self, x: int, y: int):
        # המשחק הסתיים (מלך נאכל): כל פקודת מהלך מתעלמת מכאן ואילך.
        if self.game_over:
            return

        # נעילת קלט בזמן תנועה: כל עוד יש מהלך בתהליך (piece "on the common route"),
        # הלוח נעול ולחיצות מתעלמות. כך שני כלים לעולם אינם נעים במקביל, כולל צבעים
        # מנוגדים, וגם אי אפשר לנתב-מחדש כלי שכבר בדרך. הנעילה משתחררת עם הגעת המהלך.
        if self.pending_moves:
            return

        row = y // config.CELL_SIZE
        col = x // config.CELL_SIZE

        if not self.board.is_within_bounds(row, col):
            return

        # מקרה א': אין כלי נבחר כרגע
        if self.board.selected_piece is None:
            if not self.board.is_empty(row, col):
                self.board.select_piece(row, col)
            return

        # מקרה ב': יש כלי נבחר, בודקים יעד
        sel_row, sel_col = self.board.selected_piece
        
        # 1. בדיקת צבע - אם לחצו על כלי אחר באותו צבע, מחליפים בחירה
        current_color = self.board.get_piece_color(sel_row, sel_col)
        target_color = self.board.get_piece_color(row, col)
        
        if current_color is not None and current_color == target_color:
            self.board.select_piece(row, col)
            return

        # 2. בדיקת חוקיות התנועה (כולל חוסמים ומסלול)
        moving_piece = self.board.get_cell(sel_row, sel_col)
        if isinstance(moving_piece, Piece):
            if not moving_piece.is_valid_move(sel_row, sel_col, row, col, self.board):
                self.board.selected_piece = None
                return

        # 3. יציאה לדרך: המהלך אינו מיידי אלא נמשך זמן פיזי לפי אורך המסלול.
        #    הכלי נשאר בתא המקור ויוזז רק בהגעתו (בעת קידום השעון). מרגע זה הלוח
        #    נעול (ראו הבדיקה בראש הפונקציה) עד שהמהלך יגיע ליעדו.
        arrival_ms = self.game_clock_ms + self._travel_time(sel_row, sel_col, row, col)
        self.pending_moves.append(PendingMove(sel_row, sel_col, row, col, arrival_ms))
        self.board.selected_piece = None

    def _travel_time(self, from_row, from_col, to_row, to_col) -> int:
        """זמן ההגעה נגזר ממספר התאים במסלול (מרחק צ'בישב) כפול MS_PER_CELL."""
        cells = max(abs(to_row - from_row), abs(to_col - from_col))
        return cells * config.MS_PER_CELL

    def _resolve_arrived_moves(self):
        """מבצע בפועל כל מהלך שזמן הגעתו כבר חלף לפי השעון הנוכחי."""
        still_pending = []
        for move in self.pending_moves:
            if move.arrival_ms <= self.game_clock_ms:
                # קוראים את תא היעד לפני הדריסה: אם ישב שם מלך - המשחק הוכרע.
                captured = self.board.get_cell(move.to_row, move.to_col)
                self.board.move_piece(move.from_row, move.from_col,
                                      move.to_row, move.to_col)
                if isinstance(captured, King):
                    self.game_over = True
            else:
                still_pending.append(move)
        self.pending_moves = still_pending

    def _handle_wait(self, ms: int):
        self.game_clock_ms += ms
        self._resolve_arrived_moves()

    def _handle_print_board(self):
        print(self.board)