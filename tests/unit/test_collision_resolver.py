"""The collision model from the spec — the arrival table (§1), mid-path blocks (§2) and two movers
meeting (§3). The decision logic is tested directly on the rule set (deterministic, no timing), and
the detection is tested through the arbiter with a wired-in CollisionResolver.
"""
import kongfuchess.config as config
from kongfuchess.model.arrival import ArrivalContext
from kongfuchess.model.board import Board
from kongfuchess.model.collision import (
    CANCEL, KEEP, STOP_BEFORE, STOP_ON, BlockContext, CrossContext,
)
from kongfuchess.model.effects import EffectApplier, MovePiece, RemovePiece
from kongfuchess.model.piece import Color, Piece, PieceKind, PieceState
from kongfuchess.model.position import Position
from kongfuchess.realtime.collision_resolver import CollisionResolver
from kongfuchess.realtime.real_time_arbiter import RealTimeArbiter
from kongfuchess.rules.rule_factory import build_rule_set


def pc(piece_id, color, kind, row, col, state=PieceState.IDLE):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col), state=state)


def board_with(width, height, *pieces):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return board


def rules():
    return build_rule_set(config.load().pieces)


def _kinds(effects):
    return [type(e).__name__ for e in effects]


# --- §1: arrival table (ChessRuleSet.resolve_arrival) ------------------------------------------
def test_arrival_on_empty_cell_just_moves():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    effects = rules().resolve_arrival(ArrivalContext(board, rook, Position(0, 2)))
    assert _kinds(effects) == ["MovePiece"]


def test_arrival_on_enemy_captures_then_moves():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, enemy)
    effects = rules().resolve_arrival(ArrivalContext(board, rook, Position(0, 2)))
    assert _kinds(effects) == ["RemovePiece", "MovePiece"]
    assert effects[0].piece is enemy


def test_arrival_on_a_friend_fails_silently():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, friend)
    effects = rules().resolve_arrival(ArrivalContext(board, rook, Position(0, 2)))
    assert effects == []                       # nobody moves, nothing captured


def test_a_knight_is_the_one_piece_that_may_take_a_friend():
    knight = pc("n", Color.WHITE, PieceKind.KNIGHT, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, knight, friend)
    effects = rules().resolve_arrival(ArrivalContext(board, knight, Position(0, 2)))
    assert _kinds(effects) == ["RemovePiece", "MovePiece"]
    assert effects[0].piece is friend


def test_a_protected_destination_eats_the_arriver_friend_or_foe():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, friend)
    effects = rules().resolve_arrival(
        ArrivalContext(board, rook, Position(0, 2), destination_is_protected=True))
    assert _kinds(effects) == ["RemovePiece"]
    assert effects[0].piece is rook            # the arriver, not the protected occupant


# --- §2: mid-path block decision (ChessRuleSet.resolve_block) -----------------------------------
def _block(mover, blocker, at, step_before, first=False, protected=False):
    return BlockContext(mover, blocker, Position(*at), Position(*step_before),
                        is_first_step=first, blocker_protected=protected)


def test_block_by_stationary_enemy_captures_and_stops_on_it():
    mover = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    res = rules().resolve_block(_block(mover, enemy, (0, 2), (0, 1)))
    assert res.adjustment == STOP_ON
    assert _kinds(res.effects) == ["RemovePiece"] and res.effects[0].piece is enemy


def test_block_by_stationary_friend_stops_one_cell_before():
    mover = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 2)
    res = rules().resolve_block(_block(mover, friend, (0, 2), (0, 1)))
    assert res.adjustment == STOP_BEFORE and res.effects == ()


def test_block_by_a_friend_on_the_first_step_cancels_the_move():
    mover = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 1)
    res = rules().resolve_block(_block(mover, friend, (0, 1), (0, 0), first=True))
    assert res.adjustment == CANCEL and res.effects == ()


def test_block_by_a_protected_piece_redirects_onto_it():
    mover = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    jumper = pc("j", Color.WHITE, PieceKind.PAWN, 0, 2, state=PieceState.JUMPING)
    res = rules().resolve_block(_block(mover, jumper, (0, 2), (0, 1), protected=True))
    assert res.adjustment == STOP_ON and res.effects == ()   # arrival's protection eats the mover


# --- §3: two movers meeting (ChessRuleSet.resolve_cross) ----------------------------------------
def test_cross_the_first_mover_is_untouched():
    a = pc("a", Color.WHITE, PieceKind.ROOK, 0, 0)
    b = pc("b", Color.BLACK, PieceKind.ROOK, 0, 4)
    res = rules().resolve_cross(CrossContext(a, b, mover_started_first=True))
    assert res.adjustment == KEEP and res.effects == ()


def test_cross_two_enemies_the_later_one_is_captured():
    a = pc("a", Color.WHITE, PieceKind.ROOK, 0, 0)
    b = pc("b", Color.BLACK, PieceKind.ROOK, 0, 4)
    res = rules().resolve_cross(CrossContext(a, b, mover_started_first=False))
    assert _kinds(res.effects) == ["RemovePiece"] and res.effects[0].piece is a


def test_cross_two_friends_the_later_one_stops():
    a = pc("a", Color.WHITE, PieceKind.ROOK, 0, 0)
    b = pc("b", Color.WHITE, PieceKind.ROOK, 0, 4)
    res = rules().resolve_cross(CrossContext(a, b, mover_started_first=False))
    assert res.adjustment == CANCEL and res.effects == ()


def test_the_knight_flies_over_collisions():
    assert rules().flies_over(pc("n", Color.WHITE, PieceKind.KNIGHT, 0, 0)) is True
    assert rules().flies_over(pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)) is False


# --- detection through the arbiter (resolver + arbiter together) --------------------------------
def make_arbiter():
    rule_set = rules()
    return RealTimeArbiter(
        rules=rule_set, effect_applier=EffectApplier(),
        ms_per_cell=1000, jump_duration_ms=1000, long_rest_ms=2000, short_rest_ms=500,
        collision_resolver=CollisionResolver(rule_set, EffectApplier()),
    )


def test_slide_into_a_stationary_friend_stops_one_cell_before_it():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    friend = pc("f", Color.WHITE, PieceKind.PAWN, 0, 3)
    board = board_with(5, 1, rook, friend)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 4))  # path runs through the friend
    arbiter.advance_time(3000)                                   # reaches the friend's cell (0,3)
    assert board.piece_at(Position(0, 2)) is rook                # stopped one cell before
    assert board.piece_at(Position(0, 3)) is friend              # friend untouched


def test_slide_into_a_stationary_enemy_captures_and_stops_on_it():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 3)
    board = board_with(5, 1, rook, enemy)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 4))
    arbiter.advance_time(3000)
    assert board.piece_at(Position(0, 3)) is rook                # captured and took the cell
    assert enemy.state == PieceState.CAPTURED


def test_a_knight_in_flight_ignores_a_piece_in_its_path():
    knight = pc("n", Color.WHITE, PieceKind.KNIGHT, 0, 0)
    blocker = pc("b", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(5, 1, knight, blocker)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 4))  # flies over (0,2)
    arbiter.advance_time(4000)
    assert board.piece_at(Position(0, 4)) is knight              # arrived, unaffected
    assert blocker.state != PieceState.CAPTURED                  # blocker untouched
