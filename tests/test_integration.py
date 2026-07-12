# tests/test_integration.py
# בדיקות קצה-לקצה של תרחישי משחק שלמים דרך main (הזרקת קלט).
from io import StringIO

import main


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
        "click 150 150\n"  # מהלך חוקי (אלכסון 1)
        "wait 1000\n"      # המתנה עד הגעת המהלך
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    assert "wK . .\n. . ." in out   # לאחר המהלך הלא חוקי הכלי לא זז
    assert ". . .\n. wK ." in out   # לאחר המהלך החוקי


def test_rook_and_bishop_integration(capsys):
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". bB .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"    # בחירת צריח (0,0)
        "click 50 250\n"   # הזזת צריח ל-(2,0) - קו ישר חוקי (מרחק 2 -> 2000ms)
        "wait 2000\n"      # הצריח מגיע; הלוח משתחרר (אין תנועה במקביל)
        "click 150 150\n"  # בחירת רץ (1,1)
        "click 250 250\n"  # הזזת רץ ל-(2,2) - אלכסון חוקי (מרחק 1 -> 1000ms)
        "wait 1000\n"      # הרץ מגיע
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        ". . .\n"
        ". . .\n"
        "wR . bB"
    )
    assert expected in out


def test_movement_over_time_shows_origin_then_destination(capsys):
    # לפני זמן ההגעה הלוח המודפס עדיין מציג את הכלי במקור; אחרי המתנה מספקת - ביעד.
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"    # בחירת צריח (0,0)
        "click 50 250\n"   # הזזה ל-(2,0), מרחק 2 -> זמן הגעה 2000ms
        "print board\n"    # עדיין בטיסה: הצריח במקור
        "wait 2000\n"      # השלמת המהלך
        "print board\n"    # לאחר ההגעה: הצריח ביעד
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    assert "wR . .\n. . .\n. . ." in out   # לפני ההגעה - במקור
    assert ". . .\n. . .\nwR . ." in out   # אחרי ההגעה - ביעד


def test_opposite_colors_do_not_move_concurrently_in_common_route(capsys):
    # כל עוד מהלך אחד בתהליך, הלוח נעול: הצריח השחור אינו יכול לצאת לדרך
    # במקביל לצריח הלבן, ולכן הוא נשאר במקומו.
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". . .\n"
        "bR . .\n"
        "Commands:\n"
        "click 50 50\n"    # בחירת הצריח הלבן (0,0)
        "click 250 50\n"   # יציאה למהלך ל-(0,2) - הלוח ננעל
        "click 50 250\n"   # ניסיון לבחור צריח שחור (2,0) - מתעלמים בזמן הנעילה
        "click 250 250\n"  # ניסיון להזיזו ל-(2,2) - מתעלמים
        "wait 2000\n"      # הצריח הלבן מגיע
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    out = capsys.readouterr().out
    expected = (
        ". . wR\n"
        ". . .\n"
        "bR . ."
    )
    assert expected in out
