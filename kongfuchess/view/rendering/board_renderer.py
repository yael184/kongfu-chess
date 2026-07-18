# view/rendering/board_renderer.py
"""Owns the board background and hands out a fresh per-frame canvas — nothing else touches it
(final_plan §7.2a). The background is forced to 4-channel BGRA on load so every piece sprite blends
through its alpha (constraint from final_plan §3 #3), and it is scaled once per board size and
cached; each frame gets a fresh copy so draws never compound across frames (§3 #5).
"""
import cv2

from kongfuchess.view.img import Img


class BoardRenderer:
    def __init__(self, board_image, cell_size, image_loader=Img):
        self._cell = cell_size
        background = image_loader().read(board_image)
        if background.img.shape[2] == 3:
            background.img = cv2.cvtColor(background.img, cv2.COLOR_BGR2BGRA)
        self._background = background
        self._scaled = {}                      # (w_cells, h_cells) -> scaled BGRA array

    def fresh_frame(self, width_cells, height_cells) -> Img:
        key = (width_cells, height_cells)
        if key not in self._scaled:
            target = (width_cells * self._cell, height_cells * self._cell)
            self._scaled[key] = cv2.resize(self._background.img, target,
                                           interpolation=cv2.INTER_AREA)
        frame = Img()
        frame.img = self._scaled[key].copy()
        return frame
