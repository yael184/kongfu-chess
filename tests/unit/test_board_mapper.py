# tests/unit/test_board_mapper.py
from input.board_mapper import BoardMapper
from model.position import Position


def test_maps_pixels_to_cells():
    mapper = BoardMapper(cell_size=100)
    assert mapper.to_cell(50, 50) == Position(0, 0)
    assert mapper.to_cell(150, 50) == Position(0, 1)
    assert mapper.to_cell(50, 150) == Position(1, 0)
    assert mapper.to_cell(250, 250) == Position(2, 2)


def test_x_maps_to_col_and_y_maps_to_row():
    mapper = BoardMapper(cell_size=100)
    assert mapper.to_cell(299, 100) == Position(1, 2)  # x=299 -> col 2, y=100 -> row 1


def test_cell_size_is_injected_not_global():
    # The mapper has no ambient default: a different cell size is simply a different mapper.
    assert BoardMapper(cell_size=50).to_cell(120, 60) == Position(1, 2)


def test_negative_pixels_map_to_negative_cells():
    # Out-of-board cells are fine here; bounds are the Board's concern, not the mapper's.
    assert BoardMapper(cell_size=100).to_cell(-1, -1) == Position(-1, -1)
