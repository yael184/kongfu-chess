# view/sprites/sprite_state.py
"""The State pattern for a piece's animation (final_plan §7.3), adapted to our asset config.json.

`SpriteState` is one playable clip (idle/move/jump/short_rest/long_rest): it owns its frames and its
own playback clock, and which frame shows *now* is a pure function of elapsed time. `AnimatedSprite`
holds exactly one current state and swaps it via the injected `SpriteLibrary` — it never branches on
a state name, so a brand-new state folder is picked up with no code change (Open/Closed).

Authority: the engine's reported piece state drives transitions (checked first every tick); a state's
own `next_state_when_finished` only advances a finished non-looping clip while the engine state is
unchanged.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StateConfig:
    """Playback settings for one state, read from our asset config.json
    (`graphics.frames_per_sec`/`graphics.is_loop`, `physics.next_state_when_finished`)."""
    name: str
    frames_per_sec: float
    is_loop: bool
    next_state_when_finished: str = None

    @staticmethod
    def from_asset(name, data):
        graphics = data.get("graphics", {})
        physics = data.get("physics", {})
        return StateConfig(
            name=name,
            frames_per_sec=float(graphics.get("frames_per_sec", 0)),
            is_loop=bool(graphics.get("is_loop", False)),
            next_state_when_finished=physics.get("next_state_when_finished"),
        )


class SpriteState:
    """One animation state: its frames plus its own frame clock. Knows nothing about any other
    state except the *name* it hands control to when it finishes."""

    def __init__(self, config: StateConfig, frames):
        if not frames:
            raise ValueError(f"SpriteState '{config.name}' has no frames")
        self._config = config
        self._frames = tuple(frames)
        self._elapsed_ms = 0.0

    @property
    def name(self):
        return self._config.name

    @property
    def next_state_when_finished(self):
        return self._config.next_state_when_finished

    def reset(self):
        """Called on every transition into this state."""
        self._elapsed_ms = 0.0

    def advance(self, dt_ms):
        self._elapsed_ms += dt_ms

    @property
    def is_finished(self):
        """A looping clip never finishes; a one-shot finishes once its last frame's window passes."""
        if self._config.is_loop or self._config.frames_per_sec <= 0:
            return False
        total_ms = len(self._frames) * 1000.0 / self._config.frames_per_sec
        return self._elapsed_ms >= total_ms

    @property
    def current_frame(self):
        count = len(self._frames)
        if count == 1 or self._config.frames_per_sec <= 0:
            return self._frames[0]
        index = int(self._elapsed_ms * self._config.frames_per_sec / 1000.0)
        if self._config.is_loop:
            return self._frames[index % count]
        return self._frames[min(index, count - 1)]


class AnimatedSprite:
    """Per-piece driver: holds one current SpriteState and asks the library (Strategy) for
    replacements — it never enumerates state names itself."""

    def __init__(self, library, kind, color, initial_state):
        self._library = library
        self._kind = kind
        self._color = color
        self._current = library.state_for(kind, color, initial_state)
        self._current.reset()

    def update(self, dt_ms, engine_state_name):
        if engine_state_name != self._current.name:
            self._transition_to(engine_state_name)
            return
        self._current.advance(dt_ms)
        if self._current.is_finished and self._current.next_state_when_finished:
            self._transition_to(self._current.next_state_when_finished)

    def _transition_to(self, state_name):
        self._current = self._library.state_for(self._kind, self._color, state_name)
        self._current.reset()

    @property
    def current_frame(self):
        return self._current.current_frame
