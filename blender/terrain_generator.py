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
    step_callback: Optional[Callable] = None,
    post_repair_passes: int = 1,
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
            step_callback("build", (x, y, z), vi)
        if not grid.propagate():
            break

    total = sx * sy * sz
    if post_repair_passes > 0:
        for _ in range(post_repair_passes):
            fixes = 0
            for idx in range(total):
                if grid.collapsed[idx] is None:
                    continue
                x = idx % grid.sx
                y = (idx // grid.sx) % grid.sy
                z = idx // (grid.sx * grid.sy)
                cur = next(iter(grid.cells[idx]))
                allowed = set(range(len(variants)))
                for dir_name, (nx, ny, nz) in grid.neighbors(x, y, z):
                    nidx = grid.index(nx, ny, nz)
                    if grid.collapsed[nidx] is None:
                        continue
                    ncur = next(iter(grid.cells[nidx]))
                    allowed &= adjacency[dir_name][ncur]
                    if not allowed:
                        break
                if allowed and cur not in allowed:
                    options = list(allowed)
                    weights = [variants[o].weight for o in options]
                    if guidance is not None:
                        weights = [w * max(0.0001, float(guidance(x, y, z, o))) for w, o in zip(weights, options)]
                    if sum(weights) <= 0:
                        weights = [1.0 for _ in weights]
                    choice = rng.choices(options, weights=weights, k=1)[0]
                    if choice != cur:
                        grid.cells[idx] = {choice}
                        grid.collapsed[idx] = choice
                        fixes += 1
                        if step_callback:
                            step_callback("repair", (x, y, z), choice)
            if fixes == 0:
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
