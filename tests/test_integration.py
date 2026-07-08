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
        "click 50 250\n"   # הזזת צריח ל-(2,0) - קו ישר חוקי
        "click 150 150\n"  # בחירת רץ (1,1)
        "click 250 250\n"  # הזזת רץ ל-(2,2) - אלכסון חוקי
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
