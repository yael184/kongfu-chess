# test_game.py
import pytest
from io import StringIO
from board import Board
from engine import GameEngine
from pieces import King, Rook, Bishop, Queen, Knight,EmptyCell
import main

# --- פיקסטורות (Fixtures) ---
@pytest.fixture
def valid_grid():
    return [
        [King("WHITE"), EmptyCell(), King("BLACK")],
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [EmptyCell(), King("WHITE"), EmptyCell()]
    ]

@pytest.fixture
def sample_board(valid_grid):
    return Board(valid_grid)

@pytest.fixture
def sample_engine(sample_board):
    return GameEngine(sample_board)


# --- בדיקות Board ---
def test_board_bounds(sample_board):
    assert sample_board.is_within_bounds(0, 0) is True
    assert sample_board.is_within_bounds(-1, 0) is False

def test_board_get_cell(sample_board):
    assert str(sample_board.get_cell(0, 0)) == "wK"
    assert isinstance(sample_board.get_cell(0, 1), EmptyCell)

def test_board_is_empty(sample_board):
    assert sample_board.is_empty(0, 0) is False
    assert sample_board.is_empty(0, 1) is True

def test_board_get_piece_color(sample_board):
    assert sample_board.get_piece_color(0, 0) == "WHITE"
    assert sample_board.get_piece_color(0, 2) == "BLACK"
    assert sample_board.get_piece_color(0, 1) is None 


# --- בדיקות GameEngine ---
def test_engine_click_outside_bounds(sample_engine):
    sample_engine.execute_command("click 500 500")
    assert sample_engine.board.selected_piece is None

def test_engine_click_empty_no_selection(sample_engine):
    sample_engine.execute_command("click 150 50")
    assert sample_engine.board.selected_piece is None

def test_engine_select_and_move(sample_engine):
    sample_engine.execute_command("click 50 50")  # בחירת wK ב-(0,0)
    assert sample_engine.board.selected_piece == (0, 0)
    sample_engine.execute_command("click 50 150") # תנועה חוקית ל-(1,0)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.board.selected_piece is None

def test_engine_switch_selection(sample_engine):
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 150 250") # לחיצה על ה-wK השני ב-(2,1)
    assert sample_engine.board.selected_piece == (2, 1)

def test_engine_capture_piece(sample_engine):
    sample_engine.execute_command("click 50 50")   # בחירת wK ב-(0,0)
    sample_engine.execute_command("click 250 50")  # אכילת bK ב-(0,2) - מהלך חוקיות מלך (מרחק 2) ייבדק פה כמותר לצורך הטסט הישן, או שהמלך זז צעד אחד
    # שימי לב: בגרסה הקודמת המלך זז מ-(0,0) ל-(0,2) שזה 2 צעדים. כעת המנוע חוסם את זה!
    # כדי לבדוק אכילה חוקית, נזיז את הכלי ליעד חוקי שמכיל אויב:
    
    # נשים אויב בטווח צעד אחד (0,1)
    sample_engine.board.grid[0][1] = King("BLACK")
    sample_engine.execute_command("click 50 50")   # בחירת (0,0)
    sample_engine.execute_command("click 150 50")  # אכילת האויב ב-(0,1)
    assert str(sample_engine.board.grid[0][1]) == "wK"

def test_engine_wait_and_print(sample_engine, capsys):
    sample_engine.execute_command("wait 500")
    assert sample_engine.game_clock_ms == 500
    sample_engine.execute_command("print board")
    captured = capsys.readouterr()
    assert "wK . bK" in captured.out

def test_engine_invalid_or_empty_command(sample_engine, capsys):
    sample_engine.execute_command("jump 10 20")
    captured = capsys.readouterr()
    assert "ERROR: Unknown command" in captured.out


# --- בדיקות מנגנון ה-Parsing ---
def test_parse_input_valid():
    input_text = "Board:\nwK .\n. bK\nCommands:\nprint board"
    board, commands = main.parse_input(input_text)
    assert str(board.grid[0][0]) == "wK"
    assert isinstance(board.grid[0][1], EmptyCell)

def test_parse_input_row_width_mismatch():
    input_text = "Board:\nwK .\n. bK .\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)

def test_parse_input_unknown_token_in_board():
    input_text = "Board:\nwK wQ\n. bK\nCommands:\nprint board"
    # בגלל שעידכנו את VALID_PIECES/PIECE_MAP לכלול את wQ, הטסט הזה צריך כלי שבאמת לא קיים, למשל wX
    input_text = "Board:\nwK wX\n. bK\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)

def test_main_execution_flow(capsys):
    input_data = (
        "Board:\n"
        "wK . bK\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"
        "click 150 50\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out
    assert ". wK bK\n. . ." in captured

def test_main_execution_error_flow():
    fake_stream = StringIO("Just random text")
    
    # וידוא שהקוד קורס בצורה מבוקרת עם קלט לא מתאים
    with pytest.raises(SystemExit):
        main.main(input_stream=fake_stream)


# בדיקות ישירות לחוקיות התנועה של הכלים (Unit Tests מבודדים)
def test_pieces_movement_logic():
    # לוח ריק אמיתי (6x6) שישמש לבדיקות המסלול של הצריח/רץ
    empty_board = Board([[EmptyCell() for _ in range(6)] for _ in range(6)])

    king = King("WHITE")
    assert king.is_valid_move(0, 0, 1, 1, empty_board) is True   # צעד אחד באלכסון
    assert king.is_valid_move(0, 0, 2, 0, empty_board) is False  # שני צעדים (לא חוקי)

    rook = Rook("WHITE")
    assert rook.is_valid_move(0, 0, 0, 5, empty_board) is True   # תנועה אופקית
    assert rook.is_valid_move(0, 0, 3, 3, empty_board) is False  # אלכסון (לא חוקי)

    bishop = Bishop("BLACK")
    assert bishop.is_valid_move(2, 2, 5, 5, empty_board) is True  # אלכסון מושלם
    assert bishop.is_valid_move(2, 2, 2, 4, empty_board) is False # ישר (לא חוקי)

    knight = Knight("WHITE")
    assert knight.is_valid_move(0, 0, 2, 1, empty_board) is True  # צורת L
    assert knight.is_valid_move(0, 0, 2, 2, empty_board) is False # לא L


# בדיקות אינטגרציה דרך ה-main ולוח המשחק באמצעות הזרקה (Dependency Injection)

def test_king_legal_and_illegal_commands(capsys):
    input_data = (
        "Board:\n"
        "wK . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"   # בחירת המלך ב-(0,0)
        "click 250 50\n"  # מהלך לא חוקי (מרחק 2) - יתעלם
        "print board\n"
        "click 50 50\n"   # בחירה מחדש
        "click 150 150\n" # מהלך חוקי (אלכסון 1)
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out
    assert "wK . .\n. . ." in captured
    assert ". . .\n. wK ." in captured


def test_rook_and_bishop_integration(capsys):
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". bB .\n"
        ". . .\n"  # הוספנו שורה שלישית (שורה אינדקס 2) כדי שהלוח יהיה בגודל 3x3
        "Commands:\n"
        "click 50 50\n"   # בוחר צריח ב-(0,0)
        "click 50 250\n"  # מזיז צריח ל-(2,0) - חוקי קו ישר
        "click 150 150\n" # בוחר רץ ב-(1,1)
        "click 250 250\n" # מזיז רץ ל-(2,2) - חוקי אלכסון
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out
    

    
    expected_output = (
        ". . .\n"
        ". . .\n"
        "wR . bB"
    )
    assert expected_output in captured

    
def test_empty_cell_behavior():
    empty_board = Board([[EmptyCell() for _ in range(3)] for _ in range(3)])
    empty = EmptyCell()
    assert str(empty) == "."
    assert empty.color is None
    assert empty.is_valid_move(0, 0, 1, 1, empty_board) is False