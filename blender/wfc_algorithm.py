import random
from collections import deque
from typing import Callable, List, Dict, Set, Optional, Generator, Tuple
from .tile import OPPOSITE, DIRECTIONS, WFCTile

def build_adjacency(tiles: List[WFCTile]) -> Dict[str, Dict[int, Set[int]]]:
    allowed = {d[0]: {i: set() for i in range(len(tiles))} for d in DIRECTIONS}
    for i, tile_A in enumerate(tiles):            # for each source tile
        for j, tile_B in enumerate(tiles):        # for each neighbor tile
            for direction, _, _ in DIRECTIONS: # for each direction
                opposite_direction = OPPOSITE[direction]      # get the opposite direction
                
                # Get socket tokens for both tiles
                socket_a = tile_A.sockets.get(direction, {"*"})
                socket_b = tile_B.sockets.get(opposite_direction, {"*"})
                
                # If the tiles are not allowed to connect, skip them
                if "NA" in socket_a or "NA" in socket_b:
                    continue

                # Check if tiles are compatible for this direction
                if WFCTile.sockets_compatible(socket_a, socket_b):
                    allowed[direction][i].add(j)
    return allowed

class WFCGrid:
    def __init__(self, size_x: int, size_y: int, size_z: int, tiles, adjacency, rng: random.Random, guidance: Optional[Callable] = None):
        self.sx, self.sy, self.sz = size_x, size_y, size_z
        self.tiles = tiles
        self.adj = adjacency
        self.rng = rng
        self.guidance: Optional[Callable] = guidance
        ntiles = len(tiles)

        # makes a list of sets of all the tiles for each cell in the grid 
        # (each cell is a set of all the possible tiles that can be placed in that cell)
        # there are size_x * size_y * size_z cells in the grid (represented by the for loop)
        self.possible_tiles_for_cells: List[Set[int]] = [set(range(ntiles)) for _ in range(size_x * size_y * size_z)]

        # makes a list of None for each cell in the grid (represented by the for loop)
        # (each cell is a None if it has not been collapsed yet... think schrodinger's cat ^^)
        self.collapsed: List[Optional[int]] = [None] * (size_x * size_y * size_z)

    def index_of_cell(self, x, y, z) -> int:
        '''
        Returns the index of the cell in a given x, y, z position in the grid
        '''
        return x + self.sx * (y + self.sy * z)

    def in_bounds(self, x, y, z) -> bool:
        '''
        Returns True if the given x, y, z position is within the bounds of the grid
        '''
        return 0 <= x < self.sx and 0 <= y < self.sy and 0 <= z < self.sz

    def neighbors(self, x, y, z) -> Generator[Tuple[str, Tuple[int, int, int]], None, None]:
        '''
        Returns a generator of the neighbors of the given x, y, z position in the grid
        '''
        for direction, vector, _ in DIRECTIONS:
            dx, dy, dz = vector
            nx, ny, nz = x + dx, y + dy, z + dz
            if self.in_bounds(nx, ny, nz):
                yield direction, (nx, ny, nz)

    # Finds all cells with the lowest entropy (fewest possible tile options)
    # Returns a list of cell indices that have the minimum number of choices
    # This helps the WFC algorithm choose the easiest cells to collapse next
    # (like in a sudoku puzzle, you want to fill in the cells with the least possible options first)
    def _entropy_cell_indices(self) -> List[int]:
        '''
        Returns a list of the indices of the cells with the lowest entropy
        '''
        # min_len is the length of the smallest set of propable tiles
        min_len = None

        # candidates is a list of the indices of the cells with the smallest set of propable tiles
        candidates = []

        # for each cell in the grid:
        # if the cell is not collapsed, AND the number of propable tiles is greater than 1,
        # Add the index of the cell to the candidates list.
        # If the number of propable tiles is equal to the current min_len, add the index of the cell to the candidates list.
        # If the number of propable tiles is less than the current min_len, update min_len and reset the candidates list to only include the current cell.
        for idx, propable_tiles in enumerate(self.cells):
            # get the number of propable tiles for the current cell
            num_of_propable_tiles = len(propable_tiles)

            # if the cell is collapsed, skip it
            if self.collapsed[idx] is not None:
                continue

            # if the number of propable tiles is less than or equal to 1, skip it (it's already collapsed)
            if num_of_propable_tiles <= 1:
                continue

            # if the number of propable tiles is less than the current min_len
            # Update min_len and reset the candidates list to only include the current cell.
            if (min_len is None) or (num_of_propable_tiles < min_len):
                min_len = num_of_propable_tiles
                candidates = [idx]

            # if the number of propable tiles is equal to the current min_len
            # add the index of the cell to the candidates list
            elif num_of_propable_tiles == min_len:
                candidates.append(idx)

        # return the list of candidates
        return candidates

    def collapse_random(self) -> Optional[int]:
        '''
        Collapses a random cell in the grid into one of its possible tiles
        '''
        # get the list of cells with the lowest entropy
        candidates = self._entropy_cell_indices()

        # if there are no cells with the lowest entropy,
        # then get the list of all cells that are not collapsed and have more than one possible tile
        if not candidates:
            candidates = [i for i, propable_tiles in enumerate(self.cells) if self.collapsed[i] is None and len(propable_tiles) > 1]

            # if there are STILL no cells with the lowest entropy,
            # then return None
            if not candidates:
                return None

        # choose a random cell from the list of candidates
        idx = self.rng.choice(candidates)

        # get the list of possible tiles for the chosen cell
        options = list(self.possible_tiles_for_cells[idx])

        # get the weights for each possible tile
        weights = [self.tiles[o].weight for o in options]

        # if there is guidance, adjust the weights based on the guidance
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

        # return the index of the tile (that's been chosen based on the weights) for the randdomly chosen cell
        return idx

    def propagate(self) -> bool:
        '''
        Propagates the information from the collapsed cells to the neighboring cells in order to collapse more cells accordingly
        This is done by checking if the possible tiles for the neighbor are compatible with the possible tiles for the current cell
        The process is repeated until all cells are collapsed or the grid is not solvable
        This is a form of constraint propagation
        '''
        # q is a queue of the indices of the cells that have been collapsed
        q = deque()

        # for each cell in the grid, if the cell is collapsed, add the index of the cell to the queue
        for idx, choice in enumerate(self.collapsed):
            if choice is not None:
                q.append(idx)

        # while there are cells in the queue,
        while q:
            # pop the first cell off the queue
            idx = q.popleft()

            # get the x, y, z coordinates of the cell
            x = idx % self.sx
            y = (idx // self.sx) % self.sy
            z = idx // (self.sx * self.sy)

            # for each neighbor of the cell
            for direction, (nx, ny, nz) in self.neighbors(x, y, z):
                # get the index of the neighbor
                neighbor_idx = self.index_of_cell(nx, ny, nz)

                # get the set of possible tiles for the neighbor
                possible_tiles_for_neighbor_cell = set(self.possible_tiles_for_cells[neighbor_idx])

                # if the neighbor has no possible tiles, return False; the grid is not solvable
                if not possible_tiles_for_neighbor_cell:
                    return False

                # get the set of possible tiles for the current cell
                possible_tiles_for_cell = self.possible_tiles_for_cells[idx]

                # create an empty set for allowed tiles for the neighbor
                allowed_for_neighbor = set()

                # for each possible tile for the current cell,
                for th in possible_tiles_for_cell:
                    # add the set of allowed tiles for the neighbor to the allowed_for_neighbor set
                    allowed_for_neighbor.update(self.adj[direction][th])

                # get the intersection of the possible tiles for the neighbor and the allowed tiles for the neighbor
                tiles_in_common = possible_tiles_for_neighbor_cell.intersection(allowed_for_neighbor)

                # if the intersection is empty, return False; the grid is not solvable
                if not tiles_in_common:
                    return False

                # if the intersection is not equal to the set of possible tiles for the neighbor,
                if tiles_in_common != possible_tiles_for_neighbor_cell:
                    # add the intersection to the set of possible tiles for the neighbor
                    self.possible_tiles_for_cells[neighbor_idx] = tiles_in_common

                    # if the intersection has only one tile, and the neighbor is not collapsed,
                    if len(tiles_in_common) == 1 and self.collapsed[neighbor_idx] is None:
                        # collapse the neighbor into the only possible tile
                        self.collapsed[neighbor_idx] = next(iter(tiles_in_common))

                    # add the neighbor to the queue
                    q.append(neighbor_idx)

        # return True if the grid is solvable
        return True

    def is_solved(self) -> bool:
        '''
        Returns True if the grid is solved (all cells have only one option, and therefore the grid is fully collapsed)
        '''
        # checks if the length of all the sets (each cell) is 1 (all cells have only one option as a tile)
        return all(len(propable_tiles) == 1 for propable_tiles in self.cells)
