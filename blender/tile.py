# tile.py - Wave Function Collapse (WFC) Tile System
# This file defines the core tile classes used in the WFC algorithm for procedural terrain generation

# Dictionary mapping each direction to its opposite direction
# Used to check if tiles can connect to each other
OPPOSITE = {"EAST": "WEST", "WEST": "EAST", "NORTH": "SOUTH", "SOUTH": "NORTH", "UP": "DOWN", "DOWN": "UP"}

# List of cardinal directions that can be rotated (horizontal plane only)
# UP and DOWN are not included because they don't rotate with the tile
CARDINAL = ["NORTH", "EAST", "SOUTH", "WEST"]

# Tuple defining all 6 possible connection directions for a tile
# Each entry contains: (direction_name, 3D_vector, blender_property_name)
# The 3D vector represents the offset in that direction
# The property name is what gets stored in Blender objects (e.g., "WFC_E" for East)
DIRECTIONS = (
    ("EAST",  (1, 0, 0),  "WFC_E"),   # Right direction (+X)
    ("WEST",  (-1, 0, 0), "WFC_W"),   # Left direction (-X)
    ("NORTH", (0, 1, 0),  "WFC_N"),   # Forward direction (+Y)
    ("SOUTH", (0, -1, 0), "WFC_S"),   # Backward direction (-Y)
    ("UP",    (0, 0, 1),  "WFC_UP"),  # Upward direction (+Z)
    ("DOWN",  (0, 0, -1), "WFC_DN"),  # Downward direction (-Z)
)

class WFCTile:
    """
    Represents a single tile in the Wave Function Collapse system.
    Each tile defines connection rules, weight, and rotation properties.
    """

    def __init__(self, name, sockets=None, weight=1.0, allow_rot=True):
        """
        Initialize a WFC tile.
        
        Args:
            name: String identifier for the tile
            sockets: Dictionary mapping directions to connection tokens (e.g., {"EAST": ["road", "grass"]})
            weight: Probability weight for tile placement (higher = more likely)
            allow_rot: Whether this tile can be rotated during generation
        """
        self.name = name
        self.sockets = sockets if sockets is not None else {}
        self.weight = weight
        self.allow_rot = allow_rot

    @staticmethod
    def _get_tile_sockets(obj):
        """
        Extract connection rules from Blender object.
        This method reads the WFC properties from a Blender object to determine
        what this tile can connect to in each direction.
        """
        sockets = {}
        # Check both the object's data and the object itself for WFC properties
        source_chain = (getattr(obj, "data", None), obj)
        
        # For each possible direction, extract the connection tokens
        for dir_name, _, prop in DIRECTIONS:
            tokens = None
            # Look for the property in either the object's data or the object itself
            for source in source_chain:
                if source and prop in source:
                    tokens = WFCTile._tokenize(source[prop])
                    break
            # If no tokens found, use wildcard "*" (connects to anything)
            if tokens is None:
                tokens = ["*"]
            sockets[dir_name] = set(tokens)
        return sockets
    
    @staticmethod
    def _get_tile_weight(obj):
        """
        Get tile placement weight from Blender object properties. Default to 1.0 if not found.
        Weight determines how likely this tile is to be chosen during generation.
        """
        chain = (getattr(obj, "data", None), obj)
        for source in chain:
            if source and "WFC_WEIGHT" in source:
                try:
                    return max(0.01, min(float(source["WFC_WEIGHT"]), 10.0))
                except Exception:
                    pass
        return 1.0
    
    @staticmethod
    def _get_tile_allow_rot(obj):
        """
        Check if tile can be rotated during generation.
        Reads the WFC_ALLOW_ROT property from Blender object.
        """
        def _to_bool(x):
            """Convert various input types to boolean"""
            if isinstance(x, str):
                return x.lower() not in ("0","false","no")
            return bool(x)
        
        # Check if rotation is allowed on the object itself
        if "WFC_ALLOW_ROT" in obj:
            return _to_bool(obj["WFC_ALLOW_ROT"])
        # Check if rotation is allowed on the object's data
        if hasattr(obj, "data") and obj.data and "WFC_ALLOW_ROT" in obj.data:
            return _to_bool(obj.data["WFC_ALLOW_ROT"])
        # Default to allowing rotation
        return True
    
    @staticmethod
    def _tokenize(value):
        """
        Parse socket values into tokens.
        Converts various input formats into a list of connection tokens.
        
        Args:
            value: Input value (string, None, or other type)
            
        Returns:
            List of token strings
        """
        if value is None:
            return ["*"]  # Wildcard - connects to anything
        if isinstance(value, str):
            # Split comma-separated values and clean them up
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts if parts else ["*"]
        # Convert other types to string
        return [str(value)]
    
    @staticmethod
    def sockets_compatible(tokens_a, tokens_b):
        """
        Check if two sets of socket tokens are compatible.
        This determines whether two tiles can be placed adjacent to each other.
        
        Args:
            tokens_a: First set of connection tokens
            tokens_b: Second set of connection tokens
            
        Returns:
            True if tiles can connect, False otherwise
        """
        # "NA" means "Not Allowed" - these tiles can never connect
        if "NA" in tokens_a or "NA" in tokens_b:
            return False
        # "*" is a wildcard - connects to anything
        if "*" in tokens_a or "*" in tokens_b:
            return True
        # Check if there's any overlap between the token sets
        return not set(tokens_a).isdisjoint(set(tokens_b))