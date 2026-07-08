# tests/test_engine.py
# בדיקות למחלקת GameEngine ולפירוש הפקודות.
from board import Board
from engine import GameEngine
from pieces import King


# --- ניתוב פקודות (execute_command) ---
def test_empty_command_is_noop(sample_engine):
    # מחרוזת ריקה / רווחים בלבד לא אמורה לזרוק חריגה או לשנות מצב
    sample_engine.execute_command("   ")
    assert sample_engine.board.selected_piece is None


def test_unknown_command_prints_error(sample_engine, capsys):
    sample_engine.execute_command("jump 10 20")
    assert "ERROR: Unknown command" in capsys.readouterr().out


def test_click_wrong_arg_count_is_unknown(sample_engine, capsys):
    # click עם מספר ארגומנטים שגוי נופל ל-else (פקודה לא מוכרת)
    sample_engine.execute_command("click 50")
    assert "ERROR: Unknown command" in capsys.readouterr().out


# --- לחיצות (_handle_click) ---
def test_click_outside_bounds_does_nothing(sample_engine):
    sample_engine.execute_command("click 500 500")
    assert sample_engine.board.selected_piece is None


def test_click_empty_cell_no_selection(sample_engine):
    sample_engine.execute_command("click 150 50")  # (0,1) ריק
    assert sample_engine.board.selected_piece is None


def test_click_selects_piece(sample_engine):
    sample_engine.execute_command("click 50 50")  # (0,0) = wK
    assert sample_engine.board.selected_piece == (0, 0)


def test_select_and_legal_move(sample_engine):
    sample_engine.execute_command("click 50 50")   # בחירת (0,0)
    sample_engine.execute_command("click 50 150")  # תנועה חוקית ל-(1,0)
    sample_engine.execute_command("wait 1000")     # המתנה עד הגעת המהלך (תא אחד)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.board.selected_piece is None


def test_switch_selection_same_color(sample_engine):
    sample_engine.execute_command("click 50 50")    # בחירת (0,0) wK
    sample_engine.execute_command("click 150 250")  # (2,1) wK - החלפת בחירה
    assert sample_engine.board.selected_piece == (2, 1)


def test_illegal_move_deselects(sample_engine):
    sample_engine.execute_command("click 50 50")    # בחירת (0,0)
    sample_engine.execute_command("click 250 150")  # יעד רחוק/לא חוקי למלך
    # לא בוצע מהלך, והבחירה בוטלה
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.selected_piece is None


def test_capture_enemy_piece(sample_engine):
    # נשים אויב בטווח צעד אחד ונאכל אותו
    sample_engine.board.grid[0][1] = King("BLACK")
    sample_engine.execute_command("click 50 50")   # בחירת (0,0)
    sample_engine.execute_command("click 150 50")  # אכילת (0,1)
    sample_engine.execute_command("wait 1000")     # המתנה עד הגעת המהלך (תא אחד)
    assert str(sample_engine.board.grid[0][1]) == "wK"
    assert sample_engine.board.selected_piece is None


# --- wait ---
def test_wait_accumulates_clock(sample_engine):
    sample_engine.execute_command("wait 500")
    assert sample_engine.game_clock_ms == 500
    sample_engine.execute_command("wait 250")
    assert sample_engine.game_clock_ms == 750


# --- תנועה לאורך זמן (movement over time) ---
def test_move_stays_at_origin_before_any_wait(sample_engine):
    # מיד לאחר יזום המהלך, לפני שהשעון התקדם, הכלי עדיין במקור והיעד ריק.
    sample_engine.execute_command("click 50 50")   # בחירת (0,0)
    sample_engine.execute_command("click 50 150")  # יעד (1,0), זמן הגעה 1000
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.is_empty(1, 0)
    assert len(sample_engine.pending_moves) == 1


def test_move_still_in_flight_after_partial_wait(sample_engine):
    # המתנה קצרה מזמן ההגעה אינה משלימה את המהלך.
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 50 150")
    sample_engine.execute_command("wait 500")      # פחות מ-1000
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.is_empty(1, 0)


def test_move_completes_after_enough_wait(sample_engine):
    # כשהשעון מגיע לזמן ההגעה, הכלי עובר בפועל ליעד והמקור מתרוקן.
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 50 150")
    sample_engine.execute_command("wait 1000")     # בדיוק זמן ההגעה
    assert sample_engine.board.is_empty(0, 0)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.pending_moves == []


def test_longer_move_takes_proportionally_more_time(make_board):
    # זמן ההגעה גדל עם אורך המסלול: מהלך של שני תאים דורש 2000ms.
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # בחירת הצריח (0,0)
    engine.execute_command("click 50 250")   # יעד (2,0), מרחק 2 -> 2000ms
    engine.execute_command("wait 1000")      # רק חצי מהדרך
    assert str(engine.board.grid[0][0]) == "wR"
    engine.execute_command("wait 1000")      # סה"כ 2000 -> הגיע
    assert str(engine.board.grid[2][0]) == "wR"
    assert engine.board.is_empty(0, 0)


# --- print board ---
def test_print_board(sample_engine, capsys):
    sample_engine.execute_command("print board")
    out = capsys.readouterr().out
    assert "wK . bK" in out
