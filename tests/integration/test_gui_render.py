"""End-to-end render of the OpenCV surface, headless (no window, no waitKey).

Exercises the real assets and the real wiring: parse the standard board, build the renderer through
the composition root, and draw actual frames. It asserts the frame geometry and that a move in
flight is reported as a gliding motion — the renderer path a window would show.
"""
import kongfuchess.config as config
from kongfuchess.composition import app_factory
from kongfuchess.model.position import Position


def _engine_and_renderer():
    cfg = config.load()
    board = app_factory.build_board_parser(cfg).parse(cfg.assets.default_board.read_text(encoding="utf-8"))
    engine = app_factory.build_engine(board, cfg)
    return cfg, engine, app_factory.build_renderer(cfg)


def _frame(engine, renderer, now_ms=0, selected=None):
    return renderer.render(engine.snapshot(), engine.active_motions(),
                           engine.airborne_cells(), selected, now_ms)


def test_idle_frame_matches_the_board_geometry():
    cfg, engine, renderer = _engine_and_renderer()
    frame = _frame(engine, renderer)
    snap = engine.snapshot()
    assert frame.img.shape == (snap.height * cfg.cell_size, snap.width * cfg.cell_size, 4)


def test_move_in_flight_renders_as_a_gliding_motion():
    cfg, engine, renderer = _engine_and_renderer()
    # White knight b1 -> c3 (two cells away => 2000 ms at the default speed).
    assert engine.request_move(Position(7, 1), Position(5, 2)).is_accepted

    engine.wait(500)                                   # a quarter of the way there
    motions = engine.active_motions()
    assert len(motions) == 1
    assert 0.0 < motions[0].progress < 1.0

    frame = _frame(engine, renderer, now_ms=500)       # gliding piece is drawn, no exception
    assert frame.img.shape[2] == 4


def test_jumping_piece_is_reported_airborne_and_renders():
    cfg, engine, renderer = _engine_and_renderer()
    engine.request_jump(Position(7, 1))
    assert Position(7, 1) in engine.airborne_cells()
    assert _frame(engine, renderer).img is not None


def test_selection_highlight_renders_without_error():
    cfg, engine, renderer = _engine_and_renderer()
    assert _frame(engine, renderer, selected=Position(7, 1)).img is not None
