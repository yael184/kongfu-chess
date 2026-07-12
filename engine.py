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
        self.airborne = {}       # (row, col) -> land_ms: כלים שקופצים במקום ומוגנים עד הנחיתה
        self.game_over = False   # נדלק כאשר מלך נאכל; מרגע זה מהלכים מתעלמים

    def execute_command(self, command_str: str):
        parts = command_str.strip().split()
        if not parts:
            return

        command_type = parts[0]

        if command_type == "click" and len(parts) == 3:
            self._handle_click(int(parts[1]), int(parts[2]))
        elif command_type == "jump" and len(parts) == 3:
            self._handle_jump(int(parts[1]), int(parts[2]))
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

    def _handle_jump(self, x: int, y: int):
        # קפיצה במקום (Dodge): הכלי נשאר בתאו ומוגן למשך JUMP_DURATION_MS.
        # אינה כפופה לנעילת-הלוח של מהלכים - כדי שתוכל להתקיים בזמן שאויב בדרך.
        if self.game_over:
            return

        row = y // config.CELL_SIZE
        col = x // config.CELL_SIZE

        if not self.board.is_within_bounds(row, col):
            return
        if self.board.is_empty(row, col):
            return                                   # אין כלי לקפוץ (גם 'כלי שנאכל אינו יכול לקפוץ')
        if self._is_in_flight(row, col):
            return                                   # כלי שנמצא בתנועה אינו יכול לקפוץ
        if (row, col) in self.airborne:
            return                                   # כבר באוויר

        self.airborne[(row, col)] = self.game_clock_ms + config.JUMP_DURATION_MS

    def _is_in_flight(self, row, col) -> bool:
        """האם קיים מהלך תלוי-ועומד שיצא מהתא הזה (כלומר הכלי נמצא בתנועה)."""
        return any(m.from_row == row and m.from_col == col for m in self.pending_moves)

    def _travel_time(self, from_row, from_col, to_row, to_col) -> int:
        """זמן ההגעה נגזר ממספר התאים במסלול (מרחק צ'בישב) כפול MS_PER_CELL."""
        cells = max(abs(to_row - from_row), abs(to_col - from_col))
        return cells * config.MS_PER_CELL

    def _resolve_arrived_moves(self):
        """מבצע בפועל כל מהלך שזמן הגעתו כבר חלף לפי השעון הנוכחי."""
        still_pending = []
        for move in self.pending_moves:
            if move.arrival_ms <= self.game_clock_ms:
                self._resolve_move(move)
            else:
                still_pending.append(move)
        self.pending_moves = still_pending

    def _resolve_move(self, move):
        # התנגשות עם קפיצה: אם ביעד יושב כלי אויב שעדיין באוויר ברגע ההגעה
        # (arrival_ms <= זמן הנחיתה שלו) - הקופץ "נוחת על" המגיע ואוכל אותו:
        # הכלי הקופץ נשאר במקומו, והתוקף המגיע מוסר מהלוח.
        land_ms = self.airborne.get((move.to_row, move.to_col))
        arriving_color = self.board.get_piece_color(move.from_row, move.from_col)
        defender_color = self.board.get_piece_color(move.to_row, move.to_col)
        if (land_ms is not None and move.arrival_ms <= land_ms
                and defender_color is not None and arriving_color is not None
                and defender_color != arriving_color):
            arriving = self.board.get_cell(move.from_row, move.from_col)
            self.board.clear_cell(move.from_row, move.from_col)
            if isinstance(arriving, King):
                self.game_over = True
            return

        # הכרעה רגילה (כולל המקרה שבו הקופץ כבר נחת לפני שהתוקף הגיע):
        # קוראים את תא היעד לפני הדריסה - אם ישב שם מלך, המשחק הוכרע.
        captured = self.board.get_cell(move.to_row, move.to_col)
        self.board.move_piece(move.from_row, move.from_col,
                              move.to_row, move.to_col)
        self._apply_promotion(move.to_row, move.to_col)
        if isinstance(captured, King):
            self.game_over = True

    def _expire_airborne(self):
        """מסיר כלים שכבר נחתו (זמן הנחיתה חלף) מרשימת הקופצים."""
        self.airborne = {cell: land for cell, land in self.airborne.items()
                         if land >= self.game_clock_ms}

    def _apply_promotion(self, row, col):
        """מחליף כלי שהגיע ליעדו בכלי המוכתר שלו (חייל -> מלכה), אם יש."""
        piece = self.board.get_cell(row, col)
        promoted = piece.promoted_piece(row, self.board)
        if promoted is not None:
            self.board.set_cell(row, col, promoted)

    def _handle_wait(self, ms: int):
        self.game_clock_ms += ms
        self._resolve_arrived_moves()
        self._expire_airborne()

    def _handle_print_board(self):
        print(self.board)