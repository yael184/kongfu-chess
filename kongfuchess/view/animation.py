# view/animation.py
"""A single piece-state animation: a list of frames plus how fast to play them.

Frames are pre-loaded, alpha-preserving Img sprites already scaled to a board cell. Which frame to
draw at a given moment is a pure function of elapsed time, `frames_per_sec` and whether the clip
loops — so the renderer stays stateless and just asks for `frame_at(now_ms)`.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Animation:
    frames: tuple            # tuple[Img], at least one, scaled to the cell
    frames_per_sec: float
    is_loop: bool

    def frame_at(self, now_ms: int):
        """The Img to draw at simulated time `now_ms` (measured from the clip's start).

        A looping clip wraps; a one-shot clip holds on its final frame. A zero fps clip (a still)
        shows its first frame.
        """
        count = len(self.frames)
        if count == 1 or self.frames_per_sec <= 0:
            return self.frames[0]
        index = int(now_ms * self.frames_per_sec / 1000)
        if self.is_loop:
            return self.frames[index % count]
        return self.frames[min(index, count - 1)]
