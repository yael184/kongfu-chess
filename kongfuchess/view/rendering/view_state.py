"""Everything one frame needs to know, gathered into a single value object.

The view reads several independent facts each tick — the board, what is in flight, what is cooling
down, what the user selected and where it may go — and they arrive from different places (the
snapshot, the arbiter's render windows, the controller). Passing them as one frozen value keeps the
renderers' signatures stable: a new kind of overlay adds a field here instead of another positional
argument threaded through GameLoop, BoardView and every fake in the tests.

It is plain data with no behaviour and no chess: `targets` is whatever the rules answered, and
`rests` are timing views the arbiter already sampled.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ViewState:
    snapshot: object                       # the read-only board + game_over
    motions: tuple = ()                    # in-flight moves, for gliding pieces
    rests: tuple = ()                      # cooldowns running now, for the countdown overlay
    selected: object = None                # the selected cell, or None
    targets: tuple = ()                    # cells the selected piece may move to
