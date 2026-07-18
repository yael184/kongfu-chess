"""SpriteLibrary (Strategy) loads our on-disk layout from a temp asset tree, with a fake image
loader so no real cv2 decode happens. Verifies fresh instances per request (own clocks)."""
import json

from kongfuchess.view.sprites.sprite_library import SpriteLibrary


class FakeImg:
    """Stand-in for Img: records what it was asked to read, decodes nothing."""

    def read(self, path, size=None):
        self.path = path
        self.size = size
        return self


def _make_state_folder(base, state_name, frames, config):
    sprite_dir = base / "states" / state_name / "sprites"
    sprite_dir.mkdir(parents=True)
    (base / "states" / state_name / "config.json").write_text(json.dumps(config))
    for name in frames:
        (sprite_dir / name).write_bytes(b"")


def test_library_loads_a_state_and_returns_fresh_instances(tmp_path):
    base = tmp_path / "NW"
    _make_state_folder(base, "idle", ["1.png", "2.png"],
                       {"graphics": {"frames_per_sec": 4, "is_loop": True}})
    library = SpriteLibrary({("knight", "white"): base}, cell_size=100, image_loader=FakeImg)

    first = library.state_for("knight", "white", "idle")
    second = library.state_for("knight", "white", "idle")
    assert first.name == "idle"
    assert first is not second                 # a fresh clip each time, so clocks never collide


def test_frames_are_scaled_to_the_cell_size(tmp_path):
    base = tmp_path / "NW"
    _make_state_folder(base, "idle", ["1.png"], {"graphics": {"frames_per_sec": 1, "is_loop": True}})
    library = SpriteLibrary({("knight", "white"): base}, cell_size=64, image_loader=FakeImg)
    clip = library.state_for("knight", "white", "idle")
    assert clip.current_frame.size == (64, 64)
