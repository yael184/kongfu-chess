# tests/unit/test_real_time_arbiter.py
from kongfuchess.model.board import Board
from kongfuchess.model.effects import EffectApplier
from kongfuchess.model.piece import Piece, Color, PieceKind, PieceState
from kongfuchess.model.position import Position
from kongfuchess.realtime.real_time_arbiter import RealTimeArbiter
import kongfuchess.config as config
from kongfuchess.rules.rule_factory import build_rule_set


def pc(piece_id, color, kind, row, col):
    return Piece(id=piece_id, color=color, kind=kind, cell=Position(row, col))


def board_with(width, height, *pieces):
    board = Board(width, height)
    for piece in pieces:
        board.add_piece(piece)
    return board


def chess_rules():
    """The real rules, built from config.toml - the same ones the game plays with."""
    return build_rule_set(config.load().pieces)


def make_arbiter(rules=None, ms_per_cell=1000, jump_duration_ms=1000,
                 long_rest_ms=2000, short_rest_ms=500, collision_resolver=None, speed_for=None):
    """The arbiter has no rules of its own: what an arrival means is always injected."""
    return RealTimeArbiter(
        rules=rules if rules is not None else chess_rules(),
        effect_applier=EffectApplier(),
        ms_per_cell=ms_per_cell,
        jump_duration_ms=jump_duration_ms,
        long_rest_ms=long_rest_ms,
        short_rest_ms=short_rest_ms,
        collision_resolver=collision_resolver,
        speed_for=speed_for,
    )


def test_no_motion_active_initially():
    assert make_arbiter().has_active_motion() is False


def test_now_ms_tracks_the_advancing_clock():
    arbiter = make_arbiter()
    assert arbiter.now_ms == 0
    arbiter.advance_time(750)
    arbiter.advance_time(250)
    assert arbiter.now_ms == 1000


def test_a_per_piece_speed_overrides_the_global_travel_time():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    # A slow piece: 3000ms per cell instead of the global 1000. speed_for is a plain piece -> ms
    # function, so the arbiter never learns what kind the piece is.
    arbiter = make_arbiter(ms_per_cell=1000, speed_for=lambda piece: 3000)
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))   # one cell
    arbiter.advance_time(1000)                                    # would have arrived at global speed
    assert board.piece_at(Position(0, 1)) is None                 # but the slow piece is still moving
    arbiter.advance_time(2000)                                    # 3000ms total -> arrives
    assert board.piece_at(Position(0, 1)) is rook


def test_the_global_speed_is_the_default_when_no_override_matches():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter(ms_per_cell=1000)                      # no speed_for -> global for all
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    arbiter.advance_time(1000)
    assert board.piece_at(Position(0, 1)) is rook


def test_start_motion_marks_active_and_keeps_piece_on_source():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    assert arbiter.has_active_motion() is True
    # The logical board is unchanged until arrival.
    assert board.piece_at(Position(0, 0)) is rook
    assert board.piece_at(Position(0, 2)) is None
    assert rook.state == PieceState.MOVING


def test_motion_is_not_resolved_before_arrival():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))  # 2 cells -> 2000ms
    outcome = arbiter.advance_time(1000)  # only halfway
    assert arbiter.has_active_motion() is True
    assert board.piece_at(Position(0, 0)) is rook
    assert board.piece_at(Position(0, 2)) is None
    assert outcome.game_over is False


def test_motion_resolves_on_arrival():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 0)) is None
    assert board.piece_at(Position(0, 2)) is rook
    assert rook.cell == Position(0, 2)
    assert rook.state == PieceState.LONG_REST     # a move is followed by a cooldown
    assert arbiter.has_active_motion() is False
    arbiter.advance_time(2000)                     # long rest elapses
    assert rook.state == PieceState.IDLE


def test_single_square_takes_1000ms_exactly():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    arbiter.advance_time(999)
    assert board.piece_at(Position(0, 0)) is rook  # not yet arrived
    arbiter.advance_time(1)  # total 1000
    assert board.piece_at(Position(0, 1)) is rook


def test_diagonal_uses_cell_step_duration():
    bishop = pc("b", Color.WHITE, PieceKind.BISHOP, 0, 0)
    board = board_with(4, 4, bishop)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(3, 3))  # 3 diagonal cells -> 3000ms
    arbiter.advance_time(2999)
    assert board.piece_at(Position(0, 0)) is bishop
    arbiter.advance_time(1)
    assert board.piece_at(Position(3, 3)) is bishop


def test_arrival_captures_enemy_and_does_not_end_the_game():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    enemy = pc("e", Color.BLACK, PieceKind.PAWN, 0, 2)
    board = board_with(3, 3, rook, enemy)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    outcome = arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 2)) is rook
    assert enemy.state == PieceState.CAPTURED
    assert outcome.game_over is False


def test_capturing_a_king_reports_game_over():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    king = pc("k", Color.BLACK, PieceKind.KING, 0, 2)
    board = board_with(3, 3, rook, king)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))
    outcome = arbiter.advance_time(2000)
    assert outcome.game_over is True
    assert board.piece_at(Position(0, 2)) is rook
    assert king.state == PieceState.CAPTURED


def test_pawn_promotes_to_queen_on_arrival():
    pawn = pc("p", Color.WHITE, PieceKind.PAWN, 1, 0)
    board = board_with(3, 3, pawn)
    arbiter = make_arbiter()
    arbiter.start_motion(board, Position(1, 0), Position(0, 0))  # reaches white's last row
    arbiter.advance_time(1000)
    assert board.piece_at(Position(0, 0)).kind == PieceKind.QUEEN


# --- jump / dodge ---
def test_airborne_piece_eats_an_attacker_arriving_during_the_jump():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 0)
    rook = pc("r", Color.BLACK, PieceKind.ROOK, 1, 1)
    board = board_with(3, 3, king, rook)
    arbiter = make_arbiter()
    arbiter.request_jump(board, Position(1, 0))                 # king jumps, lands at 1000
    arbiter.start_motion(board, Position(1, 1), Position(1, 0))  # rook attacks, arrives at 1000
    arbiter.advance_time(1000)
    assert board.piece_at(Position(1, 0)) is king   # king survived
    assert board.piece_at(Position(1, 1)) is None   # attacker removed from its origin
    assert rook.state == PieceState.CAPTURED


def test_attacker_arriving_after_landing_captures_normally():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 0)
    rook = pc("r", Color.BLACK, PieceKind.ROOK, 1, 3)
    board = board_with(4, 3, king, rook)
    arbiter = make_arbiter()
    arbiter.request_jump(board, Position(1, 0))     # jump lands at 1000
    arbiter.advance_time(1000)                       # king lands
    arbiter.start_motion(board, Position(1, 3), Position(1, 0))  # arrives at 1000 + 3000 = 4000
    arbiter.advance_time(3000)
    assert board.piece_at(Position(1, 0)) is rook   # normal capture
    assert king.state == PieceState.CAPTURED


def test_jump_runs_through_short_rest_back_to_idle():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 1)
    board = board_with(3, 3, king)
    arbiter = make_arbiter()                        # jump 1000ms, short_rest 500ms
    arbiter.request_jump(board, Position(1, 1))
    assert king.state == PieceState.JUMPING
    arbiter.advance_time(1100)                      # past the 1000ms jump
    assert king.state == PieceState.SHORT_REST
    arbiter.advance_time(500)                       # past the 500ms short rest (total 1600)
    assert king.state == PieceState.IDLE
    assert board.piece_at(Position(1, 1)) is king


def test_a_resting_piece_cannot_jump_again():
    king = pc("k", Color.WHITE, PieceKind.KING, 1, 1)
    board = board_with(3, 3, king)
    arbiter = make_arbiter()
    arbiter.request_jump(board, Position(1, 1))      # now JUMPING
    arbiter.request_jump(board, Position(1, 1))      # busy -> ignored, no second jump scheduled
    arbiter.advance_time(1100)
    assert king.state == PieceState.SHORT_REST       # still just the one jump's aftermath


def test_cannot_jump_a_moving_piece_or_an_empty_cell():
    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter()
    arbiter.request_jump(board, Position(2, 2))                 # empty cell -> ignored
    arbiter.start_motion(board, Position(0, 0), Position(0, 2))  # rook now in flight
    arbiter.request_jump(board, Position(0, 0))                 # in flight -> ignored
    arbiter.advance_time(2000)
    assert board.piece_at(Position(0, 2)) is rook   # the move completed normally


# --- the arbiter has no rules of its own ---
def test_the_arbiter_applies_whatever_the_rules_return():
    """It owns time, not chess: hand it a rule set with invented rules and it obeys them.

    Here an arrival deletes the *arriving* piece and ends the game — nothing like chess. The
    arbiter cannot tell the difference, which is the point: changing the game never touches it.
    """
    from kongfuchess.model.effects import EndGame, RemovePiece

    class NonsenseRules:
        def resolve_arrival(self, context):
            return [RemovePiece(context.piece), EndGame()]

    rook = pc("r", Color.WHITE, PieceKind.ROOK, 0, 0)
    board = board_with(3, 3, rook)
    arbiter = make_arbiter(rules=NonsenseRules())
    arbiter.start_motion(board, Position(0, 0), Position(0, 1))
    outcome = arbiter.advance_time(1000)

    assert board.piece_at(Position(0, 1)) is None   # it never landed
    assert board.piece_at(Position(0, 0)) is None   # it was removed instead
    assert rook.state == PieceState.CAPTURED
    assert outcome.game_over is True


def test_the_arbiter_reports_protection_but_does_not_interpret_it():
    """The one timing fact it supplies is `destination_is_protected`; the rules decide its meaning."""
    seen = []

    class RecordingRules:
        def resolve_arrival(self, context):
            seen.append(context.destination_is_protected)
            return []

    king = pc("k", Color.WHITE, PieceKind.KING, 1, 0)
    rook = pc("r", Color.BLACK, PieceKind.ROOK, 1, 1)
    board = board_with(3, 3, king, rook)
    arbiter = make_arbiter(rules=RecordingRules())
    arbiter.request_jump(board, Position(1, 0))                  # dodger lands at 1000
    arbiter.start_motion(board, Position(1, 1), Position(1, 0))  # attacker arrives at 1000
    arbiter.advance_time(1000)

    assert seen == [True]
