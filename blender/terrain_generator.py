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

    # While the grid is not solved, collapse a random cell and propagate the information
    # If the propagation fails, break the loop
    while not grid.is_solved():
        idx = grid.collapse_random()
        if idx is None:
            break
        if step_callback:
            x = idx % grid.sx 
            y = (idx // grid.sx) % grid.sy
            z = idx // (grid.sx * grid.sy)
            tile_idx = next(iter(grid.cells[idx]))
            step_callback((x, y, z), tile_idx)
        if not grid.propagate():
            break

    placements = []
    for z in range(sz):
        for y in range(sy):
            for x in range(sx):
                idx = grid.index(x, y, z)
                if grid.collapsed[idx] is None or len(grid.cells[idx]) != 1:
                    continue
                tile_idx = next(iter(grid.cells[idx]))
                placements.append((x, y, z, tile_idx))
    return {
        "placements": placements,
        "tiles": tiles,
        "size": (sx, sy, sz),
    }
