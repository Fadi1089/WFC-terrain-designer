# tile.py
OPPOSITE = {"EAST": "WEST", "WEST": "EAST", "NORTH": "SOUTH", "SOUTH": "NORTH", "UP": "DOWN", "DOWN": "UP"}

CARDINAL = ["NORTH", "EAST", "SOUTH", "WEST"]

DIRECTIONS = (
    ("EAST",  (1, 0, 0),  "WFC_E"),
    ("WEST",  (-1, 0, 0), "WFC_W"),
    ("NORTH", (0, 1, 0),  "WFC_N"),
    ("SOUTH", (0, -1, 0), "WFC_S"),
    ("UP",    (0, 0, 1),  "WFC_UP"),
    ("DOWN",  (0, 0, -1), "WFC_DN"),
)

class WFCTile:

    def __init__(self, obj):
        self.obj = obj
        self.name = obj.name
        self.sockets = self._get_tile_sockets()
        self.weight = self._get_tile_weight()
        self.allow_rot = self._get_tile_allow_rot()
    
    def _get_tile_sockets(self):
        """Extract connection rules from Blender object"""
        sockets = {}
        source_chain = (getattr(self.obj, "data", None), self.obj)
        
        for dir_name, _, prop in self.DIRECTIONS:
            tokens = None
            for source in source_chain:
                if source and prop in source:
                    tokens = self._tokenize(source[prop])
                    break
            if tokens is None:
                tokens = ["*"]
            sockets[dir_name] = set(tokens)
        return sockets
    
    def _get_tile_weight(self):
        """Get tile placement weight"""
        weight = 1.0
        if "WFC_WEIGHT" in self.obj:
            try:
                weight = float(self.obj["WFC_WEIGHT"])
            except Exception:
                pass
        elif hasattr(self.obj, "data") and self.obj.data and "WFC_WEIGHT" in self.obj.data:
            try:
                weight = float(self.obj.data["WFC_WEIGHT"])
            except Exception:
                pass
        return max(0.01, min(weight, 10.0))
    
    def _get_tile_allow_rot(self):
        """Check if tile can be rotated"""
        if "WFC_ALLOW_ROT" in self.obj:
            v = self.obj["WFC_ALLOW_ROT"]
            if isinstance(v, str):
                return v.lower() not in ("0","false","no")
            return bool(v)
        if hasattr(self.obj, "data") and self.obj.data and "WFC_ALLOW_ROT" in self.obj.data:
            v = self.obj.data["WFC_ALLOW_ROT"]
            if isinstance(v, str):
                return v.lower() not in ("0","false","no")
            return bool(v)
        return True
    
    @staticmethod
    def _tokenize(value):
        """Parse socket values into tokens"""
        if value is None:
            return ["*"]
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts if parts else ["*"]
        return [str(value)]
    
    @staticmethod
    def sockets_compatible(tokens_a, tokens_b):
        """Check if two sets of socket tokens are compatible"""
        if "NA" in tokens_a or "NA" in tokens_b:
            return False
        if "*" in tokens_a or "*" in tokens_b:
            return True
        return not set(tokens_a).isdisjoint(set(tokens_b))


class WFCTileVariant:

    def __init__(self, base: 'WFCTile', rot: int):
        self.base = base
        self.rot = rot % 4
        self.name = f"{base.name}_rot{self.rot}"
        self.sockets = self._rotated_sockets(base.sockets, self.rot)
        self.weight = base.weight
        self.allow_rot = base.allow_rot

    @staticmethod
    def _rotated_sockets(self, sockets, rot):
        out = {}
        # Map each original direction to its rotated target
        for i, attribute in enumerate(CARDINAL):
            target = CARDINAL[(i + rot) % 4]
            out[target] = set(sockets[attribute])
        out["UP"] = set(sockets["UP"])
        out["DOWN"] = set(sockets["DOWN"])
        return out