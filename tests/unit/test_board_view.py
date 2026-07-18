"""BoardView is a coordinator: it draws nothing itself, only delegates to its three renderers in
order. Fakes stand in for all three, so this runs with no window and no assets."""
from kongfuchess.view.rendering.board_view import BoardView


class FakeBoardRenderer:
    def __init__(self):
        self.calls = 0

    def fresh_frame(self, width, height):
        self.calls += 1
        self.size = (width, height)
        return "FRAME"


class FakePieceRenderer:
    def __init__(self):
        self.calls = 0

    def draw(self, frame, snapshot, motions, dt_ms):
        self.calls += 1
        self.frame = frame


class FakeOverlayRenderer:
    def __init__(self):
        self.calls = 0

    def draw(self, frame, snapshot, selected):
        self.calls += 1


class FakeSnapshot:
    width = 8
    height = 8
    game_over = False


def test_render_delegates_to_all_three_and_returns_the_board_frame():
    board, pieces, overlay = FakeBoardRenderer(), FakePieceRenderer(), FakeOverlayRenderer()
    view = BoardView(board, pieces, overlay)

    frame = view.render(FakeSnapshot(), motions=[], selected=None, dt_ms=16)

    assert frame == "FRAME"
    assert (board.calls, pieces.calls, overlay.calls) == (1, 1, 1)
    assert board.size == (8, 8)
    assert pieces.frame == "FRAME"          # pieces drew onto the board's fresh frame
