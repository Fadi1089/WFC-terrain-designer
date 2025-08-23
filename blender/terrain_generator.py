from typing import Callable, Dict, List, Optional, Tuple
import random
from .tile import WFCTile, WFCTileVariant
from .wfc_algorithm import WFCGrid, build_adjacency

def create_variants(bases: List[WFCTile]) -> List[WFCTileVariant]:
    # Identity mapping: each base becomes a single variant with rot=0.
    # Your pre-rotated/duplicated objects are separate bases already.
    return [WFCTileVariant(b, 0) for b in bases]

def generate(
    bases: List[WFCTile],
    size: Tuple[int, int, int],
    rng: random.Random,
    guidance: Optional[Callable] = None,
    step_callback: Optional[Callable] = None
) -> Dict:
    sx, sy, sz = size
    variants = create_variants(bases)
    adjacency = build_adjacency(variants)
    grid = WFCGrid(sx, sy, sz, variants, adjacency, rng, guidance)

    while not grid.is_solved():
        idx = grid.collapse_random()
        if idx is None:
            break
        if step_callback:
            x = idx % grid.sx
            y = (idx // grid.sx) % grid.sy
            z = idx // (grid.sx * grid.sy)
            vi = next(iter(grid.cells[idx]))
            step_callback((x, y, z), vi)
        if not grid.propagate():
            break

    placements = []
    for z in range(sz):
        for y in range(sy):
            for x in range(sx):
                idx = grid.index(x, y, z)
                if grid.collapsed[idx] is None or len(grid.cells[idx]) != 1:
                    continue
                vi = next(iter(grid.cells[idx]))
                placements.append((x, y, z, vi))
    return {
        "placements": placements,
        "variants": variants,
        "size": (sx, sy, sz),
    }
