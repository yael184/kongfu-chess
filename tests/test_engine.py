# tests/test_engine.py
# בדיקות למחלקת GameEngine ולפירוש הפקודות.
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
    assert str(sample_engine.board.grid[0][1]) == "wK"
    assert sample_engine.board.selected_piece is None


# --- wait ---
def test_wait_accumulates_clock(sample_engine):
    sample_engine.execute_command("wait 500")
    assert sample_engine.game_clock_ms == 500
    sample_engine.execute_command("wait 250")
    assert sample_engine.game_clock_ms == 750


# --- print board ---
def test_print_board(sample_engine, capsys):
    sample_engine.execute_command("print board")
    out = capsys.readouterr().out
    assert "wK . bK" in out
