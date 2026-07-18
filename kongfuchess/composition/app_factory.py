# composition/app_factory.py
"""The composition root: the one place that names concrete classes and wires them together.

Every other module depends only on the abstractions it is handed. That is what makes the layers
swappable — to run a different rule set, a different time model, a different board representation
or a different surface, you change the wiring here and nothing else. If classes from two different
layers appear in an import list anywhere outside this package, the decoupling has sprung a leak
(tests/test_layer_boundaries.py guards that).

Note what is *not* here: any list of pieces. Which pieces exist, how they move, how they are
spelled and what wins the game all come from the config, so adding a piece reaches neither this
file nor any other.
"""
from kongfuchess.engine.game_engine import GameEngine
from kongfuchess.input.board_mapper import BoardMapper
from kongfuchess.input.controller import Controller
from kongfuchess.model.effects import EffectApplier
from kongfuchess.model.game_state import GameState
from kongfuchess.model.piece import Color, PieceKind, PieceState
from kongfuchess.realtime.collision_resolver import CollisionResolver
from kongfuchess.realtime.real_time_arbiter import RealTimeArbiter
from kongfuchess.rules.rule_factory import build_rule_set
from kongfuchess.text_io.board_parser import BoardParser
from kongfuchess.text_io.board_printer import BoardPrinter
from kongfuchess.text_io.piece_factory import PieceFactory
from kongfuchess.text_io.token_codec import codec_for
from kongfuchess.texttests.commands import duration_command, pixel_command, print_board_command
from kongfuchess.texttests.script_runner import ScriptRunner
from kongfuchess.view.game_loop import GameLoop
from kongfuchess.view.img import Img
from kongfuchess.view.rendering.board_renderer import BoardRenderer
from kongfuchess.view.rendering.board_view import BoardView
from kongfuchess.view.rendering.cv2_renderer import Cv2Renderer
from kongfuchess.view.rendering.overlay_renderer import OverlayRenderer
from kongfuchess.view.rendering.piece_renderer import PieceRenderer
from kongfuchess.view.sprites.sprite_library import SpriteLibrary


def build_codec(cfg):
    """The token <-> piece codec for the configured pieces and empty cell."""
    return codec_for(cfg.pieces, cfg.empty_token)


def build_board_parser(cfg) -> BoardParser:
    """The text -> model.Board converter for the configured text format."""
    return BoardParser(PieceFactory(), build_codec(cfg))


def build_printer(cfg) -> BoardPrinter:
    """The model -> text renderer for the configured text format."""
    return BoardPrinter(build_codec(cfg))


def build_rules(cfg):
    """The rules in play — how each piece moves, what an arrival does, and what wins.

    This is the swap point for a different game: a variant, a custom ruleset, or plain
    non-real-time chess is a different rule set built here, and no other layer notices.
    """
    return build_rule_set(cfg.pieces)


def build_engine(board, cfg, rules=None) -> GameEngine:
    """The game itself: state + the real-time model + the rules.

    The arbiter is handed the same rule set, because it must ask what an arrival means; that is the
    only thing it ever asks about chess.
    """
    rules = rules if rules is not None else build_rules(cfg)
    arbiter = RealTimeArbiter(
        rules=rules,
        effect_applier=EffectApplier(),
        ms_per_cell=cfg.ms_per_cell,
        jump_duration_ms=cfg.jump_duration_ms,
        long_rest_ms=cfg.long_rest_ms,
        short_rest_ms=cfg.short_rest_ms,
        collision_resolver=CollisionResolver(rules, EffectApplier()),
    )
    return GameEngine(GameState(board=board), arbiter, rules)


def build_controller(engine, cfg) -> Controller:
    """The click -> command surface."""
    return Controller(engine, BoardMapper(cfg.cell_size))


def build_command_table(engine, controller, printer):
    """The text-surface command vocabulary. A new command is a new entry here."""
    return {
        "click": pixel_command(controller.handle_click),
        "jump": pixel_command(controller.handle_jump),
        "wait": duration_command(engine.wait),
        "print": print_board_command(engine, printer),
    }


def build_script_runner(board, cfg, rules=None) -> ScriptRunner:
    """The full text surface, wired end to end around an already-parsed board."""
    engine = build_engine(board, cfg, rules)
    controller = build_controller(engine, cfg)
    return ScriptRunner(build_command_table(engine, controller, build_printer(cfg)))


def build_piece_folders(cfg):
    """Map each (kind, color) to its sprite folder, from the configured symbols and color suffixes.

    This is the one place the on-disk piece naming (<symbol><suffix>, e.g. QW/KB) is spelled out;
    the view is handed resolved folders and never names a piece or a color.
    """
    assets = cfg.assets
    folders = {}
    for spec in cfg.pieces:
        kind = PieceKind(spec.name)
        folders[(kind, Color.WHITE)] = assets.pieces_dir / f"{spec.symbol}{assets.white_suffix}"
        folders[(kind, Color.BLACK)] = assets.pieces_dir / f"{spec.symbol}{assets.black_suffix}"
    return folders


def build_state_folders(cfg):
    """Map each engine PieceState to the sprite-state folder it animates as (config-driven)."""
    assets = cfg.assets
    return {
        PieceState.IDLE: assets.idle_state,
        PieceState.MOVING: assets.move_state,
        PieceState.JUMPING: assets.jump_state,
        PieceState.SHORT_REST: assets.short_rest_state,
        PieceState.LONG_REST: assets.long_rest_state,
    }


def build_board_view(cfg) -> BoardView:
    """The frame coordinator: background + animated piece sprites + overlays, DI-assembled."""
    assets = cfg.assets
    library = SpriteLibrary(build_piece_folders(cfg), cfg.cell_size, image_loader=Img)
    return BoardView(
        BoardRenderer(assets.board_image, cfg.cell_size),
        PieceRenderer(library, cfg.cell_size, build_state_folders(cfg)),
        OverlayRenderer(cfg.cell_size),
    )


def build_gui_app(board, cfg, window_title, rules=None) -> GameLoop:
    """The full real-time OpenCV surface, wired end to end around an already-parsed board.

    The swap point for the graphical surface, exactly as build_script_runner is for the text one:
    same engine, same controller, a different way in (mouse) and out (pixels).
    """
    engine = build_engine(board, cfg, rules)
    controller = build_controller(engine, cfg)
    return GameLoop(engine, controller, build_board_view(cfg), Cv2Renderer(window_title))
