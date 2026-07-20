"""End-to-end render of the OpenCV surface, headless (no window, no waitKey).

Exercises the real assets and the real wiring: parse the standard board, build the BoardView through
the composition root, and draw actual frames. Asserts the frame geometry and that a move in flight
is reported as a gliding motion — the renderer path a window would show.
"""
import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.model.position import Position
from kongfuchess.view.rendering.view_state import ViewState


def _engine_and_view():
    cfg = config.load()
    board = app_factory.build_board_parser(cfg).parse(cfg.assets.default_board.read_text(encoding="utf-8"))
    engine = app_factory.build_engine(board, cfg)
    return cfg, engine, app_factory.build_board_view(cfg)


def _frame(engine, view, dt_ms=0, selected=None):
    state = ViewState(
        snapshot=engine.snapshot(),
        motions=tuple(engine.active_motions()),
        rests=tuple(engine.rest_windows()),
        selected=selected,
        targets=tuple(engine.legal_destinations(selected)),
    )
    return view.render(state, dt_ms)


def test_idle_frame_matches_the_board_geometry():
    cfg, engine, view = _engine_and_view()
    frame = _frame(engine, view)
    snap = engine.snapshot()
    assert frame.img.shape == (snap.height * cfg.cell_size, snap.width * cfg.cell_size, 4)


def test_move_in_flight_renders_as_a_gliding_motion():
    cfg, engine, view = _engine_and_view()
    assert engine.request_move(Position(7, 1), Position(5, 2)).is_accepted   # white knight b1 -> c3
    engine.wait(500)
    motions = engine.active_motions()
    assert len(motions) == 1 and 0.0 < motions[0].progress < 1.0
    assert _frame(engine, view, dt_ms=500).img.shape[2] == 4                 # gliding sprite drawn


def test_jumping_and_resting_pieces_render_across_their_states():
    cfg, engine, view = _engine_and_view()
    engine.request_jump(Position(7, 1))
    _frame(engine, view)                                   # jumping animation
    engine.wait(1200)                                      # -> short rest
    assert _frame(engine, view, dt_ms=1200).img is not None


def test_selection_highlight_renders_without_error():
    cfg, engine, view = _engine_and_view()
    assert _frame(engine, view, selected=Position(7, 1)).img is not None
