import random
from collections import deque
from typing import Callable, List, Dict, Set, Optional
from .tile import OPPOSITE, DIRECTIONS, WFCTileVariant, WFCTile

def build_adjacency(tiles) -> Dict[str, Dict[int, Set[int]]]:
    allowed = {d[0]: {i: set() for i in range(len(tiles))} for d in DIRECTIONS}
    for i, tA in enumerate(tiles):
        for j, tB in enumerate(tiles):
            for dir_name, _, _ in DIRECTIONS:
                opp = OPPOSITE[dir_name]
                # Compare A’s face in dir_name with B’s opposite face
                if WFCTile.sockets_compatible(
                    tA.sockets.get(dir_name, {"*"}),
                    tB.sockets.get(opp, {"*"})
                ):
                    allowed[dir_name][i].add(j)
    return allowed

class WFCGrid:
    def __init__(self, size_x: int, size_y: int, size_z: int, tiles, adjacency, rng: random.Random, guidance: Optional[Callable] = None):
        self.sx, self.sy, self.sz = size_x, size_y, size_z
        self.tiles = tiles
        self.adj = adjacency
        self.rng = rng
        self.guidance: Optional[Callable] = guidance
        ntiles = len(tiles)
        self.cells: List[Set[int]] = [set(range(ntiles)) for _ in range(size_x * size_y * size_z)]
        self.collapsed: List[Optional[int]] = [None] * (size_x * size_y * size_z)

    def index(self, x, y, z) -> int:
        return x + self.sx * (y + self.sy * z)

    def in_bounds(self, x, y, z) -> bool:
        return 0 <= x < self.sx and 0 <= y < self.sy and 0 <= z < self.sz

    def neighbors(self, x, y, z):
        for dir_name, vec, _ in DIRECTIONS:
            dx, dy, dz = vec
            nx, ny, nz = x + dx, y + dy, z + dz
            if self.in_bounds(nx, ny, nz):
                yield dir_name, (nx, ny, nz)

    def entropy_cell_indices(self):
        min_len = None
        candidates = []
        for idx, opts in enumerate(self.cells):
            if self.collapsed[idx] is not None:
                continue
            l = len(opts)
            if l <= 1:
                continue
            if (min_len is None) or (l < min_len):
                min_len = l
                candidates = [idx]
            elif l == min_len:
                candidates.append(idx)
        return candidates

    def collapse_random(self):
        candidates = self.entropy_cell_indices()
        if not candidates:
            candidates = [i for i, opts in enumerate(self.cells) if self.collapsed[i] is None and len(opts) > 1]
            if not candidates:
                return None
        idx = self.rng.choice(candidates)
        options = list(self.cells[idx])
        weights = [self.tiles[o].weight for o in options]
        if self.guidance is not None:
            x = idx % self.sx
            y = (idx // self.sx) % self.sy
            z = idx // (self.sx * self.sy)
            weights = [w * max(0.0001, float(self.guidance(x, y, z, o))) for w, o in zip(weights, options)]
        if sum(weights) <= 0:
            weights = [1.0 for _ in weights]
        choice = self.rng.choices(options, weights=weights, k=1)[0]
        self.cells[idx] = {choice}
        self.collapsed[idx] = choice
        return idx

    def propagate(self) -> bool:
        q = deque()
        for idx, choice in enumerate(self.collapsed):
            if choice is not None:
                q.append(idx)
        while q:
            idx = q.popleft()
            x = idx % self.sx
            y = (idx // self.sx) % self.sy
            z = idx // (self.sx * self.sy)
            for dir_name, (nx, ny, nz) in self.neighbors(x, y, z):
                nidx = self.index(nx, ny, nz)
                before = set(self.cells[nidx])
                if not before:
                    return False
                possible_here = self.cells[idx]
                allowed_for_neighbor = set()
                for th in possible_here:
                    allowed_for_neighbor.update(self.adj[dir_name][th])
                newset = before.intersection(allowed_for_neighbor)
                if not newset:
                    return False
                if newset != before:
                    self.cells[nidx] = newset
                    if len(newset) == 1 and self.collapsed[nidx] is None:
                        only = next(iter(newset))
                        self.collapsed[nidx] = only
                    q.append(nidx)
        return True

    def is_solved(self) -> bool:
        return all(len(opts) == 1 for opts in self.cells)
