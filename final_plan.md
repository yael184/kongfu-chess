# Kung Fu Chess — UI Build Plan (Final — all design decisions locked)

**Stack:** Python
**Game logic:** `Iteration_12_-_Final` — reviewed in full (all 19 files)
**Graphics base:** `Img` class — reviewed in full, it's a thin OpenCV (`cv2`) wrapper: `read` (loads via `cv2.imread(..., IMREAD_UNCHANGED)`, optional resize), `draw_on` (alpha-blends self onto another `Img` at `x,y`), `put_text` (`cv2.putText` on self), `show` (`cv2.imshow` + **blocking** `cv2.waitKey(0)`).
**Scope:** UI only (rendering, input, animation, moves log/score/names). No chess-rule work.
**Implementation status: nothing has been written yet.** This document is the complete plan prior to any code being started — every phase below is still to be built, in order.

> **Hard constraint from your boss, confirmed:** no PyGame/SFML/LWJGL or any other graphics library — every visual (board, pieces, animations, score panel, moves log, player names, selection highlight, debug cursor markers) is drawn exclusively through the `Img` class. Nothing in this plan uses or ever will use another graphics library. The one thing to be precise about: **`Img` itself has no window-loop or mouse-input API** — its own `show()` method already reaches into `cv2.imshow`/`cv2.waitKey` internally, since that's the only way to put pixels on screen at all. So the plumbing that puts an `Img`'s pixel buffer on screen each frame and reads OS mouse events (Phase 2/3) is the *same* underlying mechanism `Img.show()` itself uses — not a second graphics library layered on top. All actual drawing (compositing sprites, text, highlights) stays 100% inside `Img` calls.
>
> **Updated boss requirement:** `Img` itself is now open to change — new methods can be added, and existing ones modified, whenever the UI work genuinely needs it, without a case-by-case sign-off. The one thing that doesn't change is the constraint above: whatever gets added still has to be a thin, `put_text`-style method that mutates `self.img` via `cv2` calls — it's still "through the `Img` class," never a second graphics library. `draw_rect`/`draw_circle` (originally a locked, individually-approved decision) and `new`/`save` (originally flagged for review) are the first examples of this and remain exactly as designed below; going forward, any further `Img` additions Phases 1-6 turn out to need (e.g. a blank-canvas helper, a resize/crop utility, a text-measurement helper for panel layout) are made directly as part of implementing that phase, and simply listed in that phase's notes rather than raised as a separate decision.

---

## 1. What the engine already gives us (read directly from your code)

This is a genuinely clean, layered engine — a lot of what a UI layer would otherwise have to design itself is already built correctly:

| Concern | Already implemented as |
|---|---|
| Board/piece state | `GameEngine.snapshot()` -> `GameSnapshot(board_width, board_height, pieces=[PieceSnapshot(kind, color, pixel_x, pixel_y, state)], selected, game_over)` -- a read-only DTO, exactly what a renderer should consume. |
| Submitting a move | `GameEngine.request_move(src: Position, dst: Position) -> MoveResult(is_accepted, reason)` |
| Submitting a jump | `GameEngine.request_jump(pos: Position) -> bool` |
| Click interpretation | `Controller.click(x, y)` -- **already takes raw pixel coordinates**, already implements select -> move/jump -> deselect logic, already calls `request_move`/`request_jump` for you. We reuse this unchanged. |
| Pixel -> cell mapping | `BoardMapper.pixel_to_cell(x, y)`, using `config.cell_pixel_size` (default 100px/square). |
| Virtual clock / timing | `GameEngine.advance_clock(ms)` -- advances a virtual clock and settles due motions. Duration per move = `squares_traveled x per_square_ms` (config-driven, default 1000ms/square), already matches spec S10 exactly. |
| Jump-lands-on-piece capture | Already implemented in `RealTimeArbiter.resolve_due`: an arriving move is "swallowed" if it lands on a cell an airborne jumper occupies. This is the special rule the spec calls out as *not* in standard chess libraries -- **it's already done**, we just need to render it. |
| Promotion | `ConditionalPromotionRule` -- already wired to last-rank pawns -> queen. UI just needs to draw whatever `kind` the snapshot reports; no extra logic needed. |
| Game over | `GameEngine.game_over` flips true on king capture. |

## 2. What's genuinely missing (this is the real UI scope)

- No graphics/rendering at all yet -- everything above is headless/text (`main.py` reads a DSL script from stdin, writes board-as-text to stdout).
- No wall-clock game loop -- `advance_clock` exists but nothing currently drives it from real elapsed time.
- No smooth motion exposed yet -- `snapshot()` currently only reports settled (logical) positions. Per the locked decision in §7.5, the engine will gain one small additive field (`PieceSnapshot.motion_progress`) so in-flight interpolation data comes from the same DTO as everything else, rather than a separate query call.
- No sprite/animation system (idle/move/jump/long_rest states, FPS, loop flags) -- that lives in the `Img`/asset files we're still waiting on.
- No moves log, score, or player-name concept anywhere in the engine.
- Settlement events (`SettlementEvent`, which carries `captured_piece`) are currently **swallowed** inside `GameEngine.settle()` -- only used internally for the king-capture check, and not exposed to any external caller. This matters for Phase 5 (see below).

## 3. `Img`-only rendering: what this means concretely for the loop/input plumbing

Per your boss's instruction, everything drawn on screen goes through `Img`. The points below aren't a workaround to that rule — they're about the small amount of window/event plumbing that has to exist for *any* image to reach the screen at all, and which `Img.show()` already relies on internally (it calls `cv2.imshow`/`cv2.waitKey` itself). We'll use exactly that same plumbing, directly, from Phase 2 onward, instead of routing every frame through the blocking `show()` method:

1. **`show()` is blocking and unusable per-frame.** It calls `cv2.imshow(...)` then `cv2.waitKey(0)` — which blocks *indefinitely* until a key is pressed. That's fine for a one-off sanity check (Phase 1), but a real-time loop can't call `Img.show()` every frame. From Phase 2 onward we'll drive the same underlying display call ourselves — `cv2.imshow(window_name, canvas.img)` + `cv2.waitKey(1)` (a 1ms non-blocking poll that also pumps the GUI event queue) — displaying an `Img`'s own pixel buffer (`canvas.img`) every frame. This is plumbing, not a second graphics library: every pixel in `canvas.img` gets there exclusively via `Img.read`/`draw_on`/`put_text` calls.
2. **Mouse input isn't built into `Img` at all.** There's no click/move handling in the class. We'll register mouse input the same way `Img.show()`'s own window system supports it — `cv2.setMouseCallback(window_name, our_handler)` on the same window we're drawing to. Again: this reads OS input, it draws nothing — all drawing stays inside `Img` calls.
3. **Transparency only actually blends if *both* images are 4-channel.** `draw_on` converts *self* (the piece) to match the *other* image's channel count before blending — so if the board background loads as plain 3-channel BGR (common for a flat .png/.jpg with no alpha), a transparent piece sprite gets silently flattened to opaque BGR instead of blending, and the "transparency" requirement quietly breaks. **Mitigation:** the board-rendering component will force the loaded background to 4-channel BGRA right after `read()` (`cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)` if it isn't already), so every `draw_on` call is guaranteed to hit the alpha-blend branch.
4. **`draw_on` has no clipping — it raises if the sprite doesn't fully fit at `(x, y)`.** So every piece sprite must be resized to exactly `cell_pixel_size × cell_pixel_size` (100×100 by default) via `read(path, size=(100,100), keep_aspect=True)`, and the canvas must be exactly `cell_pixel_size × ncols` by `cell_pixel_size × nrows` — which is exactly the coordinate space `pixel_x`/`pixel_y` in the engine's snapshot already assumes, so this lines up naturally.
5. **`draw_on` mutates the target image in place.** Since we redraw every frame, we'll keep one pristine background copy in memory and take a fresh `.copy()` of its pixel array each frame to draw pieces onto — rather than reloading from disk or compounding draws onto the same buffer across frames.
6. **Window resizing + mouse coordinates is an open risk, not a solved problem.** OpenCV's `cv2.imshow` windows don't have a built-in "on resize" event, and whether a manually resized window rescales the `(x, y)` your mouse callback receives back to original-image coordinates depends on the OpenCV build/backend (Qt vs. plain) and OS. Phase 3 will test this empirically first thing; if it proves unreliable within reasonable effort, the fallback is a **fixed-size, non-resizable window** (`cv2.WINDOW_AUTOSIZE`, the default) — which sidesteps the whole problem at the cost of not supporting live window resizing. We'll flag this explicitly once it's been tested rather than assume either way.

## 4. Two design decisions — RESOLVED

**A. How should the UI learn "a capture just happened" for scoring/move-log?**
- ~~*Option 1 -- zero engine changes:* the UI diffs `snapshot()` output frame-to-frame itself.~~
- **DECISION (LOCKED): Option 2** -- add an optional observer/callback list to `GameEngine` that gets called with each `SettlementEvent` as `settle()` resolves it. Matches the spec's explicit Observer-pattern recommendation; `SettlementEvent` already has the right shape (`src`, `dst`, `piece`, `captured_piece`), it just needs to reach outside the class. Small, backward-compatible, additive change to `game_engine.py` -- not a redesign. This is exactly the hook §7.6's `EventBus`/`MoveResolvedEvent`/`JumpResolvedEvent` design already assumes.

**B. Starting position source**
- **DECISION (LOCKED): Hardcode.** Standard 8x8 chess layout as a rows list in `kungfu_chess/ui/setup.py`, fed directly into `build_game_engine(rows, config)`. The text DSL (`BoardParser`) is not used to drive the live UI -- it stays exclusively the `texttests/` harness format, per the reasoning in Phase 0 step 4 below.

---

## 5. Phased plan

### Phase 0 -- Wiring skeleton (no rendering yet)
1. New `kungfu_chess/ui/` package so UI code stays cleanly separated from engine code.
2. `build_game_engine(standard_start_rows, GameConfig())` -> get a live `GameEngine`.
3. Instantiate one `Controller(engine, config.cell_pixel_size)` -- reused for the whole session (mirrors how `ClickCommand` caches one per engine).
4. **S4B — DECISION (LOCKED):** hardcode the standard 8x8 starting position as a rows list (`kungfu_chess/ui/setup.py`) and call `build_game_engine(rows, config)` directly, bypassing the text DSL — that format is clearly the `texttests/` harness's format, not something a live GUI should parse on launch.
5. Sprite/animation assets + JSON config format for Phase 4 — still needed. Real board/piece art also still needed for Phase 1 — see note below.

**Exit criteria:** engine boots, `engine.snapshot()` returns the starting position (32 pieces), no window yet.

### Phase 1 -- Static render
1. `BoardView` class wrapping `Img`, acting as a thin **coordinator** rather than doing all the drawing itself (see §7.2a — this boundary is set from the start so it doesn't need retrofitting later): it owns a `BoardRenderer` (background/board only) and a `PieceRenderer` (piece compositing). `BoardRenderer` loads the board background via `read()`, immediately forces it to 4-channel BGRA (constraint #3 above) — this becomes the pristine "template" kept in memory.
2. `PieceRenderer` loads one static sprite per `(color, kind)` present in the snapshot, each via `read(path, size=(cell_pixel_size, cell_pixel_size), keep_aspect=True)` so every sprite exactly matches a board square (constraint #4).
3. Each render: take a fresh copy of the template's pixel buffer from `BoardRenderer`, hand it to `PieceRenderer` to `draw_on` each piece at `pixel_x, pixel_y` from the snapshot (no coordinate math needed here — the engine hands us pixels directly), then display with `cv2.imshow`.
4. For this phase only, a single `Img.show()` call (or one `cv2.imshow` + `cv2.waitKey(0)`) is fine since it's a one-off static check.

**No real board/piece art has been supplied yet**, so a small offline script (`scripts/generate_placeholder_assets.py`) will generate a placeholder checkerboard + circular lettered piece sprites — built entirely through `Img`'s own `new`/`draw_rect`/`draw_circle`/`put_text`/`save`. `new` (blank canvas) and `save` (write to disk) are two more small additions to `Img`, needed just to be able to build/persist a canvas at all — under the updated boss requirement above, these ship as part of Phase 1 without a separate review step. Swapping in real assets later is a one-line path change in `PieceRenderer`'s asset root, nothing structural.

**Exit criteria:** starting position renders correctly, pieces sit exactly on their squares, transparency actually blends.

### Phase 2 -- Real-time loop
1. Own loop (not `Img.show()` — see constraint #1): `cv2.namedWindow(...)`, then each iteration: measure real elapsed ms since last frame -> `engine.advance_clock(dt_ms)` -> `engine.snapshot()` -> rebuild frame via `BoardView` -> `cv2.imshow(...)` -> `cv2.waitKey(1)` to poll events and cap frame rate.
2. At this stage, moves/jumps requested (e.g. via a temporary hardcoded test call) will "pop" instantly into place once their virtual duration elapses -- expected and correct, since smooth interpolation is Phase 4.

**Exit criteria:** clock visibly advances in real time; a scheduled test move settles onto the board after the right real-world delay (e.g. a 1-square pawn move settles ~1000ms later); window stays responsive (doesn't freeze waiting on a keypress).

### Phase 3 -- Mouse input
1. `cv2.setMouseCallback(window_name, handler)` on the same window we're drawing to (constraint #2 — nothing built into `Img` for this).
2. **First step of this phase, before anything else:** empirically test what coordinates the callback reports when the window is resized (constraint #6). Decide then whether we support live resizing with a translated scale factor, or lock the window to a fixed size (`cv2.WINDOW_AUTOSIZE`) as the safe fallback.
3. If resizing is supported: translate reported coordinates -> logical canvas coordinates (`cell_pixel_size x ncols` by `cell_pixel_size x nrows`) via the measured scale factor. If not: coordinates are already 1:1 with the canvas.
4. Either way, feed the resulting `(x, y)` straight into `Controller.click(x, y)` unchanged — it already does everything past that point.
5. **This is where a third `BoardView` collaborator, `OverlayRenderer`, is introduced** (see §7.2a) rather than adding this drawing directly into `BoardRenderer`/`PieceRenderer`: a debug marker at the translated cursor position every frame, and a different marker on click, so any scaling bug is visually obvious immediately — drawn via `Img.draw_circle`/`draw_rect` (locked decision, see intro above), no pre-made marker sprite needed.
6. Draw the selection highlight from `controller.selected` (already tracked for us) via the same `OverlayRenderer` — keeps `BoardView` from starting to accumulate ad hoc drawing responsibilities right from the first overlay it needs.

**Exit criteria:** you can click a piece, click a destination, and it eventually settles there -- full loop closed, coordinate mapping verified correct (fixed-size or resizable, whichever we land on).

### Phase 4 -- Smooth motion + sprite animation
1. **Engine-driven interpolation, not client-recomputed** (per the locked §7.5 decision): each `PieceSnapshot` returned by `engine.snapshot()` carries its own `motion_progress: float` (0.0 = just started, 1.0 = settled) whenever that piece is mid-move or mid-jump. `PieceRenderer` reads this value directly off the snapshot every frame to place the sprite — there's no separate duration bookkeeping or per-piece query call on the UI side, and no risk of the UI's notion of duration drifting from the engine's, since the UI never computes a duration at all.
2. Each frame: `PieceRenderer` positions the sprite using `motion_progress` for as long as it's less than 1.0; once it reaches 1.0, the settled `pixel_x`/`pixel_y` from the snapshot is already correct and needs no special-casing.
3. Layer the sprite/state-machine system from the spec on top, once sprite assets + JSON configs are available: states `idle`, `move`, `jump`, `long_rest`; each with FPS, loop flag, and `next_state_when_finished`; `move`/`jump` non-looping and driven by the interpolation above, `idle`/`long_rest` looping independently.
4. Render the jump-capture "swallow" from S1 -- no engine work needed beyond the `motion_progress` field, just make sure the swallowed piece disappears/animates out correctly when it happens.

**Exit criteria:** pieces glide between squares instead of popping, breathe when idle, and the jump-lands-on-enemy capture is visibly obvious.

### Phase 5 -- Moves log, score, player names (Observer)
1. Implement per the locked S4A decision (Option 2, engine-side `SettlementEvent` hook).
2. `MoveLogObserver`: appends `(time, move_text)` per side whenever a move settles.
3. `ScoreObserver`: standard piece-value table (P=1, N/B=3, R=5, Q=9) applied to `captured_piece.kind` whenever a capture is detected; running per-side total.
4. Static player-name labels (per spec: fine for now, multiplayer wiring is a later concern).
5. **Side panels render through their own component** — a `PanelRenderer` (or reusing `OverlayRenderer`, whichever ends up cleaner once it's written), not folded into `BoardView`/`PieceRenderer` — drawn via `Img.put_text` on its own redraw cadence, explicitly decoupled from the animation hot path (spec is explicit: panel lag is fine, blocking piece movement to update the panel is not). Keeping this as a separate collaborator is what keeps `BoardView` a coordinator instead of a class that does board rendering *and* animation *and* panels.

**Exit criteria:** full board + live-updating side panels, panel updates never visibly stall piece animation.

### Phase 6 -- Polish (only after 1-5 are solid, one at a time)
1. Show `MoveResult`/jump-rejection reasons to the player (e.g. a flash/tooltip on `"motion_in_progress"`, `"illegal_piece_move"`) -- the engine already gives you the exact reason string, just needs a UI touch, likely routed through `OverlayRenderer`.
2. Full resize polish for the whole layout (board + side panels together), not just the mouse math from Phase 3.
3. Additional sprite sets as they land.
4. Sound hooks (move/capture/jump) -- not in the written spec, natural next step.
5. Real player-name source once multiplayer exists.

---

## 6. Open items before Phase 1 coding starts

1. **Sprite/animation assets + JSON config format** -- still needed for Phase 4 (the `Img` class itself is understood now, but not the actual sprite folders yet). Board background image path also needed for Phase 1. **This is the only remaining blocker.**
2. ~~S4A decision~~ — **CONFIRMED (Option 2):** additive `SettlementEvent` callback hook in `GameEngine`.
3. ~~S4B decision~~ — **CONFIRMED:** hardcode standard starting position in `ui/setup.py`.
4. ~~Confirm the piece-value table for scoring~~ — **CONFIRMED:** standard table (P=1, N/B=3, R=5, Q=9) approved.
5. ~~Shape-drawing for highlights/markers~~ — **RESOLVED:** `draw_rect`/`draw_circle` added directly to `Img`, mirroring `put_text`'s implementation style. Under the updated boss requirement (see intro), this category of question — "does a given `Img` addition need approval?" — no longer applies going forward: further `Img` methods are added as each phase needs them, no separate sign-off required.
6. **`PieceSnapshot.motion_progress` field** — a small additive change to the engine's snapshot DTO (§7.5), same category/weight as the S4A hook. Needs the same one-line sign-off as S4A/S4B before Phase 4 can start, though it doesn't block Phases 0-3.
7. Not something that needs a decision right now, just flagging: the resizable-window-vs-mouse-coordinates behavior (constraint in §3) will be tested empirically at the start of Phase 3, and may change whether the window is resizable at all.

**All open design decisions (items 2-5) are confirmed and locked.** **Nothing has been implemented yet** — the plan is blocked solely on real board/piece assets and sprite/animation JSON configs (item 1), plus the small `motion_progress` sign-off (item 6). `Img` itself is no longer a source of blocking questions (item 5) — its surface can grow freely as implementation needs it. Once items 1 and 6 land, Phase 0 coding can begin immediately with no remaining design conversation, since §7's architecture blueprint (State/Strategy/Observer/DI, plus the renderer split in §7.2a) already accounts for every decision above.

---

## 7. Architecture Spec v3 — State / Strategy / Observer / DI hardening (design only, nothing built yet)

**Status note:** this section is the detailed design blueprint for Phases 2-5 -- worked out now so that once assets arrive, implementation is fast and low-risk instead of a design conversation. Nothing in this section has been written to disk or executed.

It formalizes the informal designs sketched in §3/§5 (sprite state machine, Observer, renderer responsibilities) into concrete patterns, and adds two requirements that weren't explicit before: Strategy-based asset loading, and DI-first construction.

### 7.1 Directory structure

```
kungfu_chess/
├── engine/                         # untouched — existing engine package
│   ├── game_engine.py
│   ├── board_mapper.py
│   ├── controller.py
│   └── ...
├── ui/
│   ├── __init__.py
│   ├── img.py                      # Img class (+ draw_rect/draw_circle/new/save)
│   ├── setup.py                    # standard-start rows (Phase 0)
│   │
│   ├── rendering/
│   │   ├── __init__.py
│   │   ├── board_view.py           # BoardView — thin coordinator only, DI-constructed
│   │   ├── board_renderer.py       # BoardRenderer — background/template only (Phase 1)
│   │   ├── piece_renderer.py       # PieceRenderer — piece compositing + motion_progress interpolation (Phase 1/4)
│   │   ├── overlay_renderer.py     # OverlayRenderer — selection highlight, debug markers, side panels (Phase 3/5)
│   │   ├── renderer.py             # thin Protocol/ABC: draw_frame(img), poll_events()
│   │   └── cv2_renderer.py         # concrete cv2 window+mouse impl (Phase 2/3 plumbing)
│   │
│   ├── sprites/
│   │   ├── __init__.py
│   │   ├── sprite_library.py       # SpriteLibrary — Strategy: asset-loading
│   │   ├── sprite_state.py         # SpriteState — State pattern (per §7.2)
│   │   ├── animated_sprite.py      # AnimatedSprite — owns current SpriteState, advances it
│   │   └── assets/
│   │       ├── placeholder/        # placeholder set (Phase 1)
│   │       │   └── white_pawn/
│   │       │       ├── idle/
│   │       │       │   ├── config.json
│   │       │       │   └── frame_0.png ...
│   │       │       ├── move/
│   │       │       ├── jump/
│   │       │       └── long_rest/
│   │       └── official/           # real asset drop-in target (future — same shape)
│   │
│   ├── events/
│   │   ├── __init__.py
│   │   ├── event_bus.py            # EventBus — Observer/pub-sub core
│   │   ├── events.py               # MoveResolvedEvent, CaptureEvent, JumpResolvedEvent, ...
│   │   └── observers/
│   │       ├── __init__.py
│   │       ├── moves_log_observer.py
│   │       └── score_observer.py   # uses CONFIRMED table: P=1, N/B=3, R=5, Q=9
│   │
│   ├── input/
│   │   ├── __init__.py
│   │   └── mouse_router.py         # translates raw (x,y) -> Controller.click, DI'd Controller
│   │
│   └── app.py                      # composition root: builds every collaborator, wires DI, runs loop
│
├── tests/
│   ├── ui/
│   │   ├── test_sprite_state.py         # pure unit tests, no cv2 window ever opened
│   │   ├── test_sprite_library.py       # loads from a tmp_path fixture, not real assets/
│   │   ├── test_event_bus.py
│   │   ├── test_moves_log_observer.py
│   │   ├── test_score_observer.py
│   │   └── test_board_view.py           # constructed with mock Renderer/SpriteLibrary/EventBus
│   └── fixtures/
│       └── mock_renderer.py             # in-memory Renderer stub for tests
│
└── scripts/
    └── generate_placeholder_assets.py   # Phase 1
```

Nothing under `engine/` changes for this spec beyond the two locked additive hooks (S4A's `SettlementEvent` callback and §7.5's `PieceSnapshot.motion_progress` field) — both are small, backward-compatible additions to existing classes, not redesigns.

### 7.2a `BoardView` as coordinator, not a god object

This is a deliberate guardrail, not a reaction to a problem that already exists: as Phases 3 and 5 add overlays, debug markers, and side panels on top of Phase 1's board+piece rendering, it would be easy to let all of that accumulate inside one `render()` method on `BoardView`. To avoid that, `BoardView` never draws anything itself — it only holds references to three focused collaborators and calls them in order each frame:

- **`BoardRenderer`** — owns the pristine background template, hands out a fresh per-frame copy. Nothing else touches the background.
- **`PieceRenderer`** — composites each piece sprite onto that copy, using `pixel_x`/`pixel_y` (and, from Phase 4, `motion_progress`) from the snapshot. Nothing else touches piece sprites.
- **`OverlayRenderer`** — draws everything that isn't "the board" or "a piece": selection highlight, debug cursor markers (Phase 3), and side panels/moves-log/score/names (Phase 5).

```python
# ui/rendering/board_view.py — coordinator only, no drawing logic of its own
class BoardView:
    def __init__(self, board_renderer: "BoardRenderer", piece_renderer: "PieceRenderer",
                 overlay_renderer: "OverlayRenderer"):
        self._board = board_renderer
        self._pieces = piece_renderer
        self._overlay = overlay_renderer

    def render(self, snapshot: "GameSnapshot", input_state: "InputState") -> Img:
        frame = self._board.fresh_frame()
        self._pieces.draw(frame, snapshot)
        self._overlay.draw(frame, snapshot, input_state)
        return frame
```

Each of `BoardRenderer`/`PieceRenderer`/`OverlayRenderer` is independently unit-testable (same pattern as §7.7's DI/testability approach) and independently extensible — a new overlay (e.g. a rejection-reason tooltip in Phase 6) is a change to `OverlayRenderer` only, never to `BoardView` or `PieceRenderer`.

### 7.2 How State, Strategy, and Observer interact in the real-time loop

One frame tick, in order:

1. **Clock / engine (unchanged):** `engine.advance_clock(dt_ms)` settles any due motions; `engine.snapshot()` returns current `PieceSnapshot`s, each still reporting `state` (`idle`/`move`/`jump`/`long_rest`) per the existing engine contract, plus (per §7.5) `motion_progress` for in-flight ones — all on the same DTO, no extra query call.
2. **State Pattern — per piece:** each piece on the UI side owns one `AnimatedSprite`, which owns one *current* `SpriteState` object. Every tick, `AnimatedSprite.update(dt_ms, engine_state)` does two things:
   - If `engine_state` (from the snapshot) differs from the sprite's current logical state name, the sprite transitions: it asks `SpriteLibrary` (Strategy) for the `SpriteState` matching the new state name, and swaps it in.
   - Otherwise, it advances the *current* `SpriteState`'s internal frame clock using that state's own `frames_per_sec`/`is_loop` from its `config.json`. If a non-looping state (`move`, `jump`) finishes its frame sequence, the `SpriteState` itself reports its configured `next_state_when_finished` — the `AnimatedSprite` transitions to that, again via `SpriteLibrary`, with zero `if/else` chains in `AnimatedSprite` itself. This is the Open/Closed win: `AnimatedSprite`'s code never enumerates state names; a brand-new `celebrate/` folder + `config.json` is picked up automatically the next time `SpriteLibrary` is asked for it.
3. **Strategy Pattern — asset resolution:** `SpriteLibrary(pieces_root: Path)` is the single place that knows the on-disk shape (`{root}/{color}_{kind}/{state}/config.json` + numbered frame files). `AnimatedSprite` and `PieceRenderer` never touch `Path`/`os` directly — they ask `SpriteLibrary.get_state(color, kind, state_name) -> SpriteState`. Swapping `pieces_root` from `assets/placeholder` to `assets/official` (once real art is uploaded) is a one-argument change in the composition root (`app.py`), nothing else in the codebase moves.
4. **Rendering:** `BoardView.render(snapshot, input_state) -> Img` delegates, per §7.2a, to `BoardRenderer` for the background, `PieceRenderer` for piece compositing (each piece's current frame `Img` comes from its `AnimatedSprite`'s current `SpriteState`, positioned using `motion_progress`), and `OverlayRenderer` for everything else. No single class does all three.
5. **Observer Pattern — side effects, off the hot path:** *separately*, whenever `engine.settle()` resolves a motion (per the locked S4A/Option 2 hook), an event (`MoveResolvedEvent`/`CaptureEvent`) is published to the `EventBus`. `MovesLogObserver` and `ScoreObserver` are subscribed once at startup and react synchronously but *outside* the render/animation call stack — publishing is a fire-and-forget loop over subscriber callbacks, so a slow observer can't block frame N+1's `draw_on` calls. (True async decoupling — a queue + separate consumption cadence — is a possible Phase 6 hardening step if an observer ever turns out slow; not needed at current scope since these are just log-append/dict-increment.)

So: **State** governs *which frame a single piece shows right now*, **Strategy** governs *where that frame's pixels come from on disk*, **Observer** governs *what happens elsewhere in the UI when something notable settles*, and the **`BoardView`/`BoardRenderer`/`PieceRenderer`/`OverlayRenderer` split** governs *who's allowed to draw what* — four orthogonal concerns, none of which know about each other's internals, all wired together only in `app.py`.

### 7.3 `SpriteState` — code blueprint (State Pattern)

```python
# ui/sprites/sprite_state.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

from ui.img import Img


@dataclass(frozen=True)
class StateConfig:
    """Parsed straight from a state folder's config.json. Immutable — a fresh
    SpriteState is built on transition, never mutated in place."""
    name: str
    frames_per_sec: float
    is_loop: bool
    next_state_when_finished: str | None  # None is valid for looping states

    @staticmethod
    def from_json(path: Path) -> "StateConfig":
        data = json.loads(path.read_text())
        return StateConfig(
            name=data["name"],
            frames_per_sec=float(data["frames_per_sec"]),
            is_loop=bool(data["is_loop"]),
            next_state_when_finished=data.get("next_state_when_finished"),
        )


class SpriteState:
    """One playable animation state (idle/move/jump/long_rest/...).
    Owns its own frame list + playback clock. Knows nothing about any
    other state except the *name* it should hand control to when done —
    it never imports or references another SpriteState class."""

    def __init__(self, config: StateConfig, frames: list[Img]):
        if not frames:
            raise ValueError(f"SpriteState '{config.name}' has no frames")
        self._config = config
        self._frames = frames
        self._elapsed_ms = 0.0

    @property
    def name(self) -> str:
        return self._config.name

    def reset(self) -> None:
        """Called on every transition INTO this state."""
        self._elapsed_ms = 0.0

    def advance(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms

    @property
    def current_frame(self) -> Img:
        idx = int(self._elapsed_ms * self._config.frames_per_sec / 1000.0)
        if self._config.is_loop:
            idx %= len(self._frames)
        else:
            idx = min(idx, len(self._frames) - 1)
        return self._frames[idx]

    @property
    def is_finished(self) -> bool:
        """Non-looping states finish once the clock passes the last frame's
        display window; looping states never finish on their own."""
        if self._config.is_loop:
            return False
        total_duration_ms = len(self._frames) * 1000.0 / self._config.frames_per_sec
        return self._elapsed_ms >= total_duration_ms

    @property
    def next_state_when_finished(self) -> str | None:
        return self._config.next_state_when_finished


class AnimatedSprite:
    """Per-piece driver. Holds exactly one 'current' SpriteState and asks
    the SpriteLibrary (Strategy) for replacements — never branches on
    state name itself."""

    def __init__(self, library: "SpriteLibrary", color: str, kind: str, initial_state: str = "idle"):
        self._library = library
        self._color = color
        self._kind = kind
        self._current: SpriteState = library.get_state(color, kind, initial_state)
        self._current.reset()

    def update(self, dt_ms: float, engine_reported_state: str) -> None:
        if engine_reported_state != self._current.name:
            self._transition_to(engine_reported_state)
            return
        self._current.advance(dt_ms)
        if self._current.is_finished and self._current.next_state_when_finished:
            self._transition_to(self._current.next_state_when_finished)

    def _transition_to(self, state_name: str) -> None:
        self._current = self._library.get_state(self._color, self._kind, state_name)
        self._current.reset()

    @property
    def current_frame(self) -> Img:
        return self._current.current_frame
```

Matching `config.json` shape (one per state folder — this is the "add a folder, not code" contract from the OCP requirement):

```json
{
  "name": "move",
  "frames_per_sec": 12,
  "is_loop": false,
  "next_state_when_finished": "idle"
}
```

### 7.4 `SpriteLibrary` — code blueprint (Strategy Pattern)

```python
# ui/sprites/sprite_library.py
from __future__ import annotations
from pathlib import Path

from ui.img import Img
from ui.sprites.sprite_state import SpriteState, StateConfig


class SpriteLibrary:
    """Strategy: encapsulates on-disk asset layout so nothing else in the
    codebase knows a Path exists. Swap pieces_root to retarget the entire
    UI to a different art set at runtime — one constructor arg."""

    def __init__(self, pieces_root: Path, cell_pixel_size: int = 100):
        self._root = Path(pieces_root)
        self._cell_pixel_size = cell_pixel_size
        self._cache: dict[tuple[str, str, str], SpriteState] = {}

    def get_state(self, color: str, kind: str, state_name: str) -> SpriteState:
        key = (color, kind, state_name)
        if key not in self._cache:
            self._cache[key] = self._load_state(color, kind, state_name)
        return self._cache[key]

    def _load_state(self, color: str, kind: str, state_name: str) -> SpriteState:
        state_dir = self._root / f"{color}_{kind}" / state_name
        config = StateConfig.from_json(state_dir / "config.json")
        frame_paths = sorted(state_dir.glob("frame_*.png"))
        if not frame_paths:
            raise FileNotFoundError(f"No frames found in {state_dir}")
        size = (self._cell_pixel_size, self._cell_pixel_size)
        frames = [Img().read(str(p), size=size, keep_aspect=True) for p in frame_paths]
        return SpriteState(config, frames)
```

### 7.5 `motion_progress` — now a `PieceSnapshot` field, not a separate engine method

**Applied change (per code review):** the earlier design proposed a standalone query method, `engine.motion_progress(row, col) -> float`, called once per piece per frame from outside the snapshot. That broke the "snapshot is the single read-only source of truth" principle the engine already establishes for everything else. Instead, `motion_progress` is now a field directly on `PieceSnapshot`, computed by the engine at the same time as the rest of the snapshot:

```python
# engine side — PieceSnapshot gains one field, computed alongside the rest of the snapshot
@dataclass(frozen=True)
class PieceSnapshot:
    kind: str
    color: str
    pixel_x: int
    pixel_y: int
    state: str  # "idle" / "move" / "jump" / "long_rest"
    motion_progress: float = 1.0
    """0.0 (motion just started) .. 1.0 (settled). Always 1.0 for a piece
    that isn't currently in flight. Read-only, part of the same immutable
    snapshot as everything else — no separate query call needed."""
```

This is a strict simplification versus the earlier design: `PieceRenderer` now depends on exactly one thing per frame (`engine.snapshot()`) instead of one snapshot call plus N per-piece `motion_progress` queries, and there's no separate "is this API in sync with the snapshot" concern to reason about. It fully replaces the client-side-recomputed-duration interpolation from the original v2 plan (§3 Phase 4, old point 1) — the UI no longer computes move/jump duration itself at all, it just reads the engine's own authoritative progress value off the snapshot.

Same weight/category as the S4A hook: small, additive, backward-compatible (defaults to `1.0`, so any code not yet using it is unaffected).

### 7.6 `EventBus` — code blueprint (Observer Pattern)

```python
# ui/events/event_bus.py
from __future__ import annotations
from collections import defaultdict
from typing import Callable, TypeVar, Type

E = TypeVar("E")
Handler = Callable[[E], None]


class EventBus:
    """Minimal synchronous pub/sub. No threading, no queue — deliberately
    simple, matching current scope (log-append/dict-increment observers).
    Publishing is O(subscribers) and happens outside the render call stack,
    so it never blocks piece-animation frame timing (§7.2 step 5)."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: Type[E], handler: Handler[E]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: E) -> None:
        for handler in self._handlers[type(event)]:
            handler(event)
```

```python
# ui/events/events.py
from dataclasses import dataclass


@dataclass(frozen=True)
class MoveResolvedEvent:
    src: tuple[int, int]
    dst: tuple[int, int]
    piece_kind: str
    piece_color: str
    captured_piece_kind: str | None  # None if no capture


@dataclass(frozen=True)
class JumpResolvedEvent:
    pos: tuple[int, int]
    piece_kind: str
    piece_color: str
    captured_piece_kind: str | None
```

```python
# ui/events/observers/score_observer.py
from ui.events.events import MoveResolvedEvent, JumpResolvedEvent

PIECE_VALUES = {"pawn": 1, "knight": 3, "bishop": 3, "rook": 5, "queen": 9}  # CONFIRMED table


class ScoreObserver:
    """Subscribed once in app.py. Pure side-effect object — constructor
    takes no engine/renderer reference, only what it needs to track score,
    so it's trivially unit-testable without any UI machinery running."""

    def __init__(self) -> None:
        self.score = {"white": 0, "black": 0}

    def on_move_resolved(self, event: MoveResolvedEvent) -> None:
        self._apply_capture(event.captured_piece_kind, capturing_color=event.piece_color)

    def on_jump_resolved(self, event: JumpResolvedEvent) -> None:
        self._apply_capture(event.captured_piece_kind, capturing_color=event.piece_color)

    def _apply_capture(self, captured_kind: str | None, capturing_color: str) -> None:
        if captured_kind is None:
            return
        self.score[capturing_color] += PIECE_VALUES.get(captured_kind, 0)
```

Wiring (composition root, illustrative only — not run yet):

```python
# ui/app.py (excerpt)
bus = EventBus()
score_observer = ScoreObserver()
bus.subscribe(MoveResolvedEvent, score_observer.on_move_resolved)
bus.subscribe(JumpResolvedEvent, score_observer.on_jump_resolved)

library = SpriteLibrary(pieces_root=Path("ui/sprites/assets/placeholder"), cell_pixel_size=config.cell_pixel_size)
renderer: Renderer = Cv2Renderer(window_name="kungfu_chess")  # concrete Strategy impl of Renderer

board_view = BoardView(
    board_renderer=BoardRenderer(...),
    piece_renderer=PieceRenderer(sprite_library=library),
    overlay_renderer=OverlayRenderer(event_bus=bus),
)  # pure DI, per §7.2a
```

### 7.7 Dependency Injection & testability

`BoardView` and each of its collaborators (`BoardRenderer`, `PieceRenderer`, `OverlayRenderer`, and every other collaborator-holding class above) take their dependencies as constructor arguments typed against small `Protocol`/ABC interfaces (`Renderer`, not `Cv2Renderer`), never reaching for a module-level singleton or importing `cv2` directly. Concretely:

```python
# ui/rendering/renderer.py
from typing import Protocol
from ui.img import Img

class Renderer(Protocol):
    def draw_frame(self, frame: Img) -> None: ...
    def poll_events(self) -> list["InputEvent"]: ...
```

```python
# tests/ui/test_board_view.py (illustrative)
def test_render_composites_all_pieces_without_opening_a_window():
    fake_board = FakeBoardRenderer()         # in-memory, returns a blank template
    fake_pieces = FakePieceRenderer()        # records draw calls, no disk I/O
    fake_overlay = FakeOverlayRenderer()      # records draw calls, no disk I/O

    board_view = BoardView(board_renderer=fake_board, piece_renderer=fake_pieces, overlay_renderer=fake_overlay)
    frame = board_view.render(fake_snapshot_with_two_pieces(), fake_input_state())

    assert fake_pieces.draw_call_count == 1
    assert fake_overlay.draw_call_count == 1
```

No `cv2.imshow`, no real window, no monkeypatching `cv2` globals — every test in `tests/ui/` can run in CI headless, which was the explicit testability goal in requirement 4. Testing `BoardRenderer`/`PieceRenderer`/`OverlayRenderer` in isolation (rather than only through `BoardView`) is also now possible precisely because §7.2a keeps them as separate, independently constructable classes.

### 7.8 What this changes vs. what it doesn't

- **Doesn't touch:** the engine package beyond the two locked additive hooks (S4A's `SettlementEvent` callback, §7.5's `PieceSnapshot.motion_progress` field), the confirmed piece-value table.
- **Formalizes:** the Phase 4 sprite/state-machine sketch and the Phase 5 Observer sketch from §3/§5 — same intent, now a named pattern with a concrete class shape instead of prose.
- **Changes versus the previous draft of this section:** `motion_progress` moved from a standalone engine method to a `PieceSnapshot` field (§7.5); `BoardView` was split into a coordinator plus three focused collaborators — `BoardRenderer`/`PieceRenderer`/`OverlayRenderer` (§7.2a) — to keep it from accumulating responsibility as Phases 3 and 5 add overlays and panels; and `Img` is now open for the implementer to extend as needed (see updated boss requirement in the intro) — `draw_rect`/`draw_circle`/`new`/`save` are the first additions under that policy, not a closed, individually-approved list.
- **Remaining ask before Phase 4 can start:** sign-off that `PieceSnapshot` gaining a `motion_progress: float = 1.0` field (§7.5) is acceptable — same category as the already-approved S4A hook, and just as backward-compatible.
- Confirmation that `config.json` per state folder should live exactly as shown in §7.3 (`name`/`frames_per_sec`/`is_loop`/`next_state_when_finished`) is a nice-to-have, not blocking — if a real asset drop uses different key names, `StateConfig.from_json` is the only place that needs updating.

**Nothing in this document has been implemented yet.** This is the complete, decisions-locked blueprint for Phases 0 through 6; coding starts at Phase 0 once board/piece assets and sprite JSON configs are available.
