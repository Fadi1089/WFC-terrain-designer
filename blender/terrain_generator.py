from typing import Callable, Dict, List, Optional, Tuple
import random
from .tile import WFCTile
from .wfc_algorithm import WFCGrid, build_adjacency

def generate(
    bases: List[WFCTile],
    size: Tuple[int, int, int],
    rng: random.Random,
    guidance: Optional[Callable] = None,
    step_callback: Optional[Callable] = None
) -> Dict:
    sx, sy, sz = size
    adjacency = build_adjacency(bases)
    grid = WFCGrid(sx, sy, sz, bases, adjacency, rng, guidance)

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
        "bases": bases,
        "size": (sx, sy, sz),
    }
