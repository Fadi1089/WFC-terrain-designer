from typing import Callable, Dict, List, Optional, Tuple
import random
from .tile import WFCTile
from .wfc_algorithm import WFCGrid, build_adjacency

def generate(
    tiles: List[WFCTile],
    size: Tuple[int, int, int],
    rng: random.Random,
    guidance: Optional[Callable] = None,
    step_callback: Optional[Callable] = None
) -> Dict:
    # size is the size of the terrain in tiles
    sx, sy, sz = size
    # adjacency is the adjacency matrix of the tiles (the possible connections between tiles)
    adjacency = build_adjacency(tiles)
    # Creates a WFC grid initialized with all possible tiles in every cell
    grid = WFCGrid(sx, sy, sz, tiles, adjacency, rng, guidance)

    # While the grid is not solved, collapse a random cell 
    # And use the step_callback to update the view layer
    while not grid.is_solved():
        # Collapse a random cell and get the index of the tile that was collapsed
        idx = grid.collapse_random()
        # If the collapse fails, break the loop
        if idx is None:
            break

        # If the step_callback is provided, 
        # call it with the position of the tile that was collapsed
        # and its index in the tile list provided to the generate function
        if step_callback:
            x = idx % grid.sx 
            y = (idx // grid.sx) % grid.sy
            z = idx // (grid.sx * grid.sy)
            tile_idx = next(iter(grid.possible_tiles_for_cells[idx]))
            step_callback((x, y, z), tile_idx)

        # If the propagation fails, break the loop
        if not grid.propagate():
            break

    # Get the placements of the tiles that were collapsed in the grid
    placements = []
    for z in range(sz):
        for y in range(sy):
            for x in range(sx):
                idx = grid.index_of_cell(x, y, z)
                if grid.collapsed[idx] is None or len(grid.possible_tiles_for_cells[idx]) != 1:
                    continue
                tile_idx = next(iter(grid.possible_tiles_for_cells[idx]))
                placements.append((x, y, z, tile_idx))

    # Return the placements of the tiles that were collapsed in the grid
    # plus the original tiles list and the size of the terrain
    return {
        "placements": placements,
        "tiles": tiles,
        "size": (sx, sy, sz),
    }
