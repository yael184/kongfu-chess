# view/rendering/board_renderer.py
"""Owns the board background and hands out a fresh per-frame canvas — nothing else touches it
(final_plan §7.2a). The background is forced to 4-channel BGRA on load so every piece sprite blends
through its alpha (constraint from final_plan §3 #3), and it is built once per board size and
cached; each frame gets a fresh copy so draws never compound across frames (§3 #5).

The artwork is **tiled, not stretched**. Scaling one 8-cell image to fit whatever board is in play
would make its painted squares drift out of step with the actual cells — on a 4x4 board you would
see eight small squares across four cells, so the piece on a "white" square looks like it is on a
black one. Instead the artwork is scaled so that one *depicted* square is exactly one cell (how many
it depicts is `assets.board_image_cells`), then repeated and cropped to the board. On the standard
8x8 board that is identical to what it did before; on every other size the squares now line up.
"""
import cv2
import numpy as np

from kongfuchess.view.img import Img


class BoardRenderer:
    def __init__(self, board_image, cell_size, image_cells, image_loader=Img):
        self._cell = cell_size
        self._image_cells = image_cells
        background = image_loader().read(board_image)
        if background.img.shape[2] == 3:
            background.img = cv2.cvtColor(background.img, cv2.COLOR_BGR2BGRA)
        self._background = background
        self._tile = None                      # the artwork at exactly one cell per depicted square
        self._boards = {}                      # (w_cells, h_cells) -> background for that board

    def fresh_frame(self, width_cells, height_cells) -> Img:
        key = (width_cells, height_cells)
        if key not in self._boards:
            self._boards[key] = self._background_for(width_cells, height_cells)
        frame = Img()
        frame.img = self._boards[key].copy()
        return frame

    def _background_for(self, width_cells, height_cells):
        """Repeat the tile over the board and crop it to the exact pixel size."""
        tile = self._one_cell_per_square()
        repeats = (_times_to_cover(height_cells, self._image_cells),
                   _times_to_cover(width_cells, self._image_cells), 1)
        covered = np.tile(tile, repeats)
        return covered[:height_cells * self._cell, :width_cells * self._cell].copy()

    def _one_cell_per_square(self):
        if self._tile is None:
            side = self._image_cells * self._cell
            source = self._background.img
            shrinking = source.shape[0] > side
            self._tile = cv2.resize(
                source, (side, side),
                interpolation=cv2.INTER_AREA if shrinking else cv2.INTER_LINEAR)
        return self._tile


def _times_to_cover(cells, per_tile) -> int:
    """How many tiles it takes to cover `cells` cells — the ceiling of the division."""
    return -(-cells // per_tile)
