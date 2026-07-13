# tests/unit/test_game_engine.py
import types

from engine.game_engine import (
    GameEngine, MoveResult, GameSnapshot,
    REASON_OK, REASON_GAME_OVER, REASON_MOTION_IN_PROGRESS,
)
from model.board import Board
from model.game_state import GameState
from model.piece import Piece, Color, PieceKind
from model.position import Position
import config
from rules.rule_factory import build_registry
from rules.rule_engine import RuleEngine, REASON_ILLEGAL_PIECE_MOVE, REASON_FRIENDLY_DESTINATION


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def state_with(width, height, *pieces, game_over=False):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return GameState(board=board, game_over=game_over)


class FakeArbiter:
    """Test double for RealTimeArbiter — records interactions and returns a canned outcome."""

    def __init__(self, active=False, game_over=False):
        self._active = active
        self._game_over = game_over
        self.started = []
        self.advanced = None

    def has_active_motion(self):
        return self._active

    def start_motion(self, board, source, destination):
        self.started.append((source, destination))

    def advance_time(self, ms):
        self.advanced = ms
        return types.SimpleNamespace(game_over=self._game_over)


class ExplodingRuleEngine:
    """Fails if consulted — proves the application guards short-circuit before RuleEngine."""

    def validate_move(self, board, source, destination):
        raise AssertionError("RuleEngine must not be called when an application guard rejects")


# --- application-level guards ---
def test_request_move_rejected_when_game_over_without_calling_rules():
    state = state_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 0), game_over=True)
    arbiter = FakeArbiter()
    engine = GameEngine(state, arbiter, ExplodingRuleEngine())
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result == MoveResult(False, REASON_GAME_OVER)
    assert arbiter.started == []


def test_request_move_rejected_when_a_motion_is_in_progress():
    state = state_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 0))
    arbiter = FakeArbiter(active=True)
    engine = GameEngine(state, arbiter, ExplodingRuleEngine())
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result == MoveResult(False, REASON_MOTION_IN_PROGRESS)
    assert arbiter.started == []


def test_game_over_guard_takes_precedence_over_motion_guard():
    state = state_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 0), game_over=True)
    arbiter = FakeArbiter(active=True)
    engine = GameEngine(state, arbiter, ExplodingRuleEngine())
    assert engine.request_move(Position(0, 0), Position(0, 2)).reason == REASON_GAME_OVER


# --- delegation to RuleEngine + starting a motion ---
def test_valid_move_is_accepted_and_starts_a_motion():
    state = state_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 0))
    arbiter = FakeArbiter()
    engine = GameEngine(state, arbiter, RuleEngine(build_registry(config.load().pieces)))
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result == MoveResult(True, REASON_OK)
    assert arbiter.started == [(Position(0, 0), Position(0, 2))]


def test_illegal_move_reason_is_copied_and_no_motion_starts():
    state = state_with(3, 3, pc("r", Color.WHITE, PieceKind.ROOK, 0, 0))
    arbiter = FakeArbiter()
    engine = GameEngine(state, arbiter, RuleEngine(build_registry(config.load().pieces)))
    result = engine.request_move(Position(0, 0), Position(2, 2))  # diagonal, illegal for a rook
    assert result == MoveResult(False, REASON_ILLEGAL_PIECE_MOVE)
    assert arbiter.started == []


def test_friendly_destination_reason_is_copied():
    state = state_with(
        3, 3,
        pc("r", Color.WHITE, PieceKind.ROOK, 0, 0),
        pc("f", Color.WHITE, PieceKind.PAWN, 0, 1),
    )
    engine = GameEngine(state, FakeArbiter(), RuleEngine(build_registry(config.load().pieces)))
    assert engine.request_move(Position(0, 0), Position(0, 1)).reason == REASON_FRIENDLY_DESTINATION


# --- time advance + king capture ---
def test_wait_delegates_to_arbiter_advance_time():
    state = state_with(3, 3)
    arbiter = FakeArbiter()
    GameEngine(state, arbiter, RuleEngine(build_registry(config.load().pieces))).wait(1000)
    assert arbiter.advanced == 1000


def test_arbiter_reporting_game_over_during_wait_sets_game_over():
    state = state_with(3, 3)
    engine = GameEngine(state, FakeArbiter(game_over=True), RuleEngine(build_registry(config.load().pieces)))
    engine.wait(1000)
    assert state.game_over is True


def test_wait_without_a_reported_end_leaves_game_running():
    state = state_with(3, 3)
    engine = GameEngine(state, FakeArbiter(game_over=False), RuleEngine(build_registry(config.load().pieces)))
    engine.wait(1000)
    assert state.game_over is False


# --- snapshot ---
def test_snapshot_exposes_read_only_board_and_flag():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    state = state_with(3, 2, rook)
    snapshot = GameEngine(state, FakeArbiter(), RuleEngine(build_registry(config.load().pieces))).snapshot()
    assert isinstance(snapshot, GameSnapshot)
    assert (snapshot.width, snapshot.height) == (3, 2)
    assert snapshot.piece_at(Position(0, 0)) is rook
    assert snapshot.piece_at(Position(1, 1)) is None
    assert snapshot.game_over is False


def test_snapshot_is_decoupled_from_later_board_changes():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    state = state_with(3, 3, rook)
    snapshot = GameEngine(state, FakeArbiter(), RuleEngine(build_registry(config.load().pieces))).snapshot()
    state.board.remove_piece(rook)
    assert snapshot.piece_at(Position(0, 0)) is rook  # snapshot kept the placement
