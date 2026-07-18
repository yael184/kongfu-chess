"""The sprite State pattern: frame selection over time, and engine-driven transitions.
Pure logic, no OpenCV and no disk."""
from kongfuchess.view.sprites.sprite_state import AnimatedSprite, SpriteState, StateConfig


def state(name, fps, loop, nxt=None, frames=("a", "b", "c")):
    return SpriteState(StateConfig(name, fps, loop, nxt), frames)


def test_from_asset_reads_our_config_json_keys():
    cfg = StateConfig.from_asset("move", {
        "graphics": {"frames_per_sec": 8, "is_loop": False},
        "physics": {"next_state_when_finished": "long_rest"},
    })
    assert cfg.name == "move"
    assert cfg.frames_per_sec == 8 and cfg.is_loop is False
    assert cfg.next_state_when_finished == "long_rest"


def test_looping_clip_wraps_through_its_frames():
    clip = state("idle", 4, True)
    assert clip.current_frame == "a"
    clip.advance(250)
    assert clip.current_frame == "b"
    clip.advance(500)                     # 750ms total -> index 3 wraps to 0
    assert clip.current_frame == "a"
    assert clip.is_finished is False      # a loop never finishes


def test_one_shot_clip_holds_last_frame_and_finishes():
    clip = state("move", 4, False, nxt="idle")
    clip.advance(1000)                    # past the 3-frame / 4fps = 750ms window
    assert clip.is_finished is True
    assert clip.current_frame == "c"


def test_zero_fps_and_single_frame_are_stills():
    assert state("x", 0, False, frames=("a", "b")).current_frame == "a"
    solo = state("x", 8, True, frames=("solo",))
    solo.advance(9999)
    assert solo.current_frame == "solo"


class FakeLibrary:
    """Records requested states; hands back a fresh SpriteState per request."""

    def __init__(self):
        self.requested = []

    def state_for(self, kind, color, name):
        self.requested.append(name)
        loop = name in ("idle", "long_rest")
        nxt = {"move": "idle", "jump": "short_rest"}.get(name)
        return SpriteState(StateConfig(name, 8, loop, nxt), ("a", "b"))


def test_a_change_in_engine_state_transitions_the_sprite():
    library = FakeLibrary()
    sprite = AnimatedSprite(library, "knight", "white", "idle")
    sprite.update(100, "move")            # the engine now reports move
    assert library.requested[-1] == "move"


def test_a_finished_one_shot_advances_to_its_next_state():
    library = FakeLibrary()
    sprite = AnimatedSprite(library, "knight", "white", "jump")   # jump: one-shot, next short_rest
    sprite.update(2000, "jump")           # engine still says jump; the jump clip has finished
    assert library.requested[-1] == "short_rest"
