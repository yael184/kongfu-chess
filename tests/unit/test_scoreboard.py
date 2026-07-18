"""The side-panel Observer pipeline: the bus, the score/moves-log observers, and the snapshot-diff
detector that feeds them. Pure logic, no window."""
from dataclasses import dataclass

from kongfuchess.model.piece import Color, Piece, PieceKind
from kongfuchess.model.position import Position
from kongfuchess.view.events.event_bus import EventBus
from kongfuchess.view.events.events import CaptureResolved, MoveResolved
from kongfuchess.view.events.observers.moves_log_observer import MovesLogObserver
from kongfuchess.view.events.observers.score_observer import ScoreObserver
from kongfuchess.view.events.settlement_detector import SettlementDetector

VALUES = {"pawn": 1, "knight": 3, "bishop": 3, "rook": 5, "queen": 9, "king": 0}


# --- EventBus ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class _A:
    v: int = 0


@dataclass(frozen=True)
class _B:
    v: int = 0


def test_bus_dispatches_only_to_subscribers_of_that_event_type():
    bus, got = EventBus(), []
    bus.subscribe(_A, got.append)
    bus.publish(_A(1))
    bus.publish(_B(2))          # no _B subscriber
    bus.publish(_A(3))
    assert got == [_A(1), _A(3)]


def test_bus_calls_every_handler_for_a_type():
    bus, first, second = EventBus(), [], []
    bus.subscribe(_A, first.append)
    bus.subscribe(_A, second.append)
    bus.publish(_A(1))
    assert first == [_A(1)] and second == [_A(1)]


# --- ScoreObserver -----------------------------------------------------------------------------
def test_capturing_black_credits_white_by_the_piece_value():
    score = ScoreObserver(VALUES)
    score.on_capture(CaptureResolved("black", "rook"))
    assert score.score == {"white": 5, "black": 0}


def test_capturing_white_credits_black():
    score = ScoreObserver(VALUES)
    score.on_capture(CaptureResolved("white", "queen"))
    assert score.score["black"] == 9


def test_an_unknown_kind_scores_nothing():
    score = ScoreObserver(VALUES)
    score.on_capture(CaptureResolved("black", "dragon"))
    assert score.score["white"] == 0


# --- MovesLogObserver --------------------------------------------------------------------------
def test_moves_are_logged_in_order():
    log = MovesLogObserver()
    log.on_move(MoveResolved("white", "N b1-c3"))
    log.on_move(MoveResolved("black", "P e7-e5"))
    assert log.entries == [("white", "N b1-c3"), ("black", "P e7-e5")]


def test_the_log_is_bounded_to_its_limit():
    log = MovesLogObserver(limit=3)
    for i in range(5):
        log.on_move(MoveResolved("white", f"m{i}"))
    assert [t for _, t in log.entries] == ["m2", "m3", "m4"]


# --- SettlementDetector (snapshot diff) --------------------------------------------------------
class FakeSnapshot:
    def __init__(self, pieces, height=8):
        self._pieces = pieces
        self.height = height

    def pieces(self):
        return self._pieces


def piece(piece_id, kind, color, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def _collecting_bus():
    bus, events = EventBus(), []
    bus.subscribe(MoveResolved, events.append)
    bus.subscribe(CaptureResolved, events.append)
    return bus, events


def test_a_moved_piece_publishes_a_move_with_algebraic_text():
    bus, events = _collecting_bus()
    detector = SettlementDetector(bus, {"knight": "N"})
    knight = piece("n", PieceKind.KNIGHT, Color.WHITE, 7, 1)   # b1 on an 8-high board
    detector.observe(FakeSnapshot([knight]))
    knight.cell = Position(5, 2)                               # -> c3
    detector.observe(FakeSnapshot([knight]))
    assert events == [MoveResolved("white", "N b1-c3")]


def test_a_vanished_piece_publishes_a_capture():
    bus, events = _collecting_bus()
    detector = SettlementDetector(bus, {})
    rook = piece("r", PieceKind.ROOK, Color.WHITE, 0, 0)
    pawn = piece("p", PieceKind.PAWN, Color.BLACK, 3, 0)
    detector.observe(FakeSnapshot([rook, pawn]))
    detector.observe(FakeSnapshot([rook]))                    # pawn taken off the board
    assert events == [CaptureResolved("black", "pawn")]


def test_the_first_observation_publishes_nothing():
    bus, events = _collecting_bus()
    SettlementDetector(bus, {}).observe(FakeSnapshot([piece("r", PieceKind.ROOK, Color.WHITE, 0, 0)]))
    assert events == []
