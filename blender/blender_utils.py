import bpy
import math
from mathutils import Vector
from typing import Dict, Set, List, Optional, Tuple, Callable
from .tile import WFCTile, DIRECTIONS

# --- helpers for physical, pre-rotated_sockets asset variants ---
_DIR_TO_PROP = {d: p for (d, _, p) in DIRECTIONS}
_CARDINAL = ["NORTH", "EAST", "SOUTH", "WEST"]
_ROT_SUFFIX = {0: "", 1: "_r90", 2: "_r180", 3: "_r270"}

def _rotate_cardinal_dir(direction: str, rot: int) -> str:
    """Return the direction after rot (0..3) 90° steps CCW (+Z in Blender)."""
    if direction not in _CARDINAL:
        return direction
    i = _CARDINAL.index(direction)
    # CCW: positive rot moves index backwards around CARDINAL
    return _CARDINAL[(i - (rot % 4)) % 4]

# Helpers to rotate single-letter suffixes like ..._N/_E/_S/_W in token strings
_LETTER_TO_DIR = {"S": "SOUTH", "E": "EAST", "N": "NORTH", "W": "WEST"}
_DIR_TO_LETTER = {v: k for k, v in _LETTER_TO_DIR.items()}

def _rotate_dir_letter(letter: str, rot: int) -> str:
    up = letter.upper()
    if up not in _LETTER_TO_DIR:
        return letter
    dir_name = _LETTER_TO_DIR[up]
    rotated_dir = _rotate_cardinal_dir(dir_name, rot)
    rotated_letter = _DIR_TO_LETTER[rotated_dir]
    return rotated_letter if letter.isupper() else rotated_letter.lower()

def _rotate_token_suffix(token: str, rot: int) -> str:
    # Match last underscore followed by a single cardinal letter, e.g. "slope_E"
    if "_" not in token:
        return token
    head, tail = token.rsplit("_", 1)
    if len(tail) == 1 and tail.upper() in _LETTER_TO_DIR:
        return f"{head}_{_rotate_dir_letter(tail, rot)}"
    return token

def _read_socket_props(obj: bpy.types.ID) -> dict:
    """Read WFC_* socket tokens from an object or data-block into a dict by DIR name."""
    sockets = {}
    for direction, _, prop in DIRECTIONS:
        if prop in obj:
            sockets[direction] = WFCTile._tokenize(obj[prop])
    return sockets

def _write_sockets_onto_object(obj: bpy.types.ID, sockets_by_dir: dict) -> None:
    """Write WFC_* socket tokens into an object (string form, comma-joined)."""
    for direction, _, prop in DIRECTIONS:
        tokens = sockets_by_dir.get(direction, ["*"])
        obj[prop] = ",".join(tokens) if isinstance(tokens, (list, tuple, set)) else str(tokens)

def _rotate_sockets(original: dict, rot: int) -> dict:
    """Rotate sockets to match a +rot (CCW, +Z) mesh rotation and rotate directional suffixes in tokens.

    After rotating the mesh by +rot*90°, the tokens that face a given world
    direction D come from the original direction rotate(D, +rot).
    Also, any token ending with _[N|E|S|W] will have that letter rotated.
    """
    rot = rot % 4
    result = {}

    for direction in _CARDINAL:
        # use CW = -rot because we’re finding the original source that ends up at `direction`
        src = _rotate_cardinal_dir(direction, -rot)
        tokens = original.get(src, ["*"])
        # Rotate any directional suffixes in the token itself by the actual mesh rotation (+rot)
        rotated_tokens = [
            _rotate_token_suffix(t, rot) if isinstance(t, str) else t for t in (tokens if isinstance(tokens, (list, tuple, set)) else [tokens])
        ]
        result[direction] = list(rotated_tokens)

    up_tokens = original.get("UP", ["*"])
    dn_tokens = original.get("DOWN", ["*"])
    result["UP"] = list(up_tokens if isinstance(up_tokens, (list, tuple, set)) else [up_tokens])
    result["DOWN"] = list(dn_tokens if isinstance(dn_tokens, (list, tuple, set)) else [dn_tokens])

    return result

def create_rotated_variations_in_collection(coll: bpy.types.Collection) -> int:
    """
    For every MESH in `coll` that has WFC_ALLOW_ROT true, create three hidden duplicates
    at the same location: +90, +180, +270 (Z). Also rotate their socket properties
    accordingly. Returns the number of new objects created.
    """
    created = 0
    meshes = [o for o in coll.all_objects if o.type == 'MESH']
    for mesh in meshes:
        if not allow_rot_from_object(mesh):
            continue

        # Prefer properties from the object first; fall back to data
        sockets_obj  = _read_socket_props(mesh)
        if not sockets_obj and getattr(mesh, "data", None):
            sockets_obj = _read_socket_props(mesh.data)

        for rot in (1, 2, 3):
            dup = mesh.copy()
            dup.data = mesh.data  # share mesh
            dup.name = f"{mesh.name}{_ROT_SUFFIX[rot]}"
            dup.location = mesh.location
            dup.rotation_euler = mesh.rotation_euler.copy()
            dup.rotation_euler.z += rot * (math.pi / 2.0)

            # Write rotated_sockets onto the duplicate OBJECT (explicit and consistent place)
            rotated_sockets = _rotate_sockets(sockets_obj, rot)
            _write_sockets_onto_object(dup, rotated_sockets)
            # Carry over weight; disable further rotation on these variants
            if "WFC_WEIGHT" in mesh:
                dup["WFC_WEIGHT"] = mesh["WFC_WEIGHT"]
            elif getattr(mesh, "data", None) and "WFC_WEIGHT" in mesh.data:
                dup["WFC_WEIGHT"] = mesh.data["WFC_WEIGHT"]
            dup["WFC_ALLOW_ROT"] = False

            dup.hide_viewport = False

            # Link the duplicate to the collection
            coll.objects.link(dup)
            created += 1
    return created

def sockets_from_object(obj: bpy.types.Object) -> Dict[str, Set[str]]:
    sockets = {}
    # prefer object-level properties first because rotated variants
    # write their rotated tokens onto the OBJECT. Fall back to mesh data.
    chain = (obj, getattr(obj, "data", None))
    for direction, _, prop in DIRECTIONS:
        tokens = None
        for source in chain:
            if source and prop in source:
                tokens = WFCTile._tokenize(source[prop])
                break
        if tokens is None:
            tokens = ["*"]
        sockets[direction] = set(tokens)
    return sockets

def weight_from_object(obj: bpy.types.Object) -> float:
    v = None
    if "WFC_WEIGHT" in obj:
        v = obj["WFC_WEIGHT"]
    elif hasattr(obj, "data") and obj.data and "WFC_WEIGHT" in obj.data:
        v = obj.data["WFC_WEIGHT"]
    try:
        return max(0.01, min(float(v if v is not None else 1.0), 10.0))
    except Exception:
        return 1.0

def allow_rot_from_object(obj: bpy.types.Object) -> bool:
    def _to_bool(x):
        if isinstance(x, str):
            return x.lower() not in ("0", "false", "no")
        return bool(x)
    if "WFC_ALLOW_ROT" in obj:
        return _to_bool(obj["WFC_ALLOW_ROT"])
    if hasattr(obj, "data") and obj.data and "WFC_ALLOW_ROT" in obj.data:
        return _to_bool(obj.data["WFC_ALLOW_ROT"])
    return True

# Creates and returns a list of WFCTile objects from the collection
def read_bases_from_collection(coll: bpy.types.Collection) -> List[WFCTile]:
    tiles = []

    # Reads all mesh objects from the selected collection
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            # Extracts connection rules, weights, and rotation settings from each object
            sockets = sockets_from_object(obj)
            weight = weight_from_object(obj)
            allow_rot = allow_rot_from_object(obj)
            # Creates a WFCTile object from the extracted information
            tiles.append(WFCTile(obj.name, sockets, weight, allow_rot))

    # Tries to return the list of WFCTile objects
    if not tiles:
        raise ValueError("Selected collection has no mesh objects.")
    return tiles

def instantiate_variant(out_coll: bpy.types.Collection, src_obj: bpy.types.Object, tile: WFCTile, pos: Tuple[int, int, int], cell_size: float) -> bpy.types.Object:
    x, y, z = pos
    inst = src_obj.copy()
    inst.data = src_obj.data  # share mesh; orientation is baked on the object
    inst.location = Vector((x * cell_size, y * cell_size, z * cell_size))
    # Preserve the baked orientation of the source object (no extra rotation)
    try:
        inst.rotation_euler = src_obj.rotation_euler.copy()
    except Exception:
        pass
    out_coll.objects.link(inst)
    return inst

def update_instance(inst_tile: bpy.types.Object, tile: WFCTile):
    # Keep whatever baked rotation the inst already has (no runtime rotation).
    return

def clear_collection(out_coll: bpy.types.Collection):
    for obj in list(out_coll.objects):
        out_coll.objects.unlink(obj)
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass

def build_guidance_from_settings(cfg, tiles: List[WFCTile]) -> Optional[Callable]:
    if not getattr(cfg, "use_heightmap", False):
        return None
    mode = getattr(cfg, "heightmap_mode", "IMAGE")
    sampler_tex = None
    sampler_img = None

    if mode == "TEXTURE" and hasattr(cfg, "heightmap_texture") and cfg.heightmap_texture:
        tex = cfg.heightmap_texture
        def sample_tex(u, v):
            try:
                c = tex.evaluate((u, v, 0.0))
                if isinstance(c, (list, tuple)) and len(c) >= 3:
                    r, g, b = float(c[0]), float(c[1]), float(c[2])
                else:
                    r = g = b = float(c)
                return max(0.0, min(1.0, 0.2126 * r + 0.7152 * g + 0.0722 * b))
            except Exception:
                return None
        sampler_tex = sample_tex

    if mode == "IMAGE" and getattr(cfg, "heightmap_image", None) is not None:
        img = cfg.heightmap_image
        if img.size[0] > 0 and img.size[1] > 0 and len(img.pixels) > 0:
            w, h = img.size
            px = list(img.pixels)
            def sample_img(u, v):
                u = min(max(u, 0.0), 0.999999)
                v = min(max(v, 0.0), 0.999999)
                ix = int(u * w)
                iy = int(v * h)
                idx = (iy * w + ix) * 4
                r, g, b = px[idx], px[idx + 1], px[idx + 2]
                return max(0.0, min(1.0, 0.2126 * r + 0.7152 * g + 0.0722 * b))
            sampler_img = sample_img

    maxz = 1
    influence = float(getattr(cfg, "heightmap_influence", 1.0))

    up_is_air = [('air' in t.sockets.get('UP', set())) for t in tiles]
    up_is_ground = [('ground' in t.sockets.get('UP', set())) for t in tiles]
    dn_is_ground = [('ground' in t.sockets.get('DOWN', set())) for t in tiles]

    def sample01(u, v):
        if sampler_tex is not None:
            s = sampler_tex(u, v)
            if s is not None:
                return s
        if sampler_img is not None:
            return sampler_img(u, v)
        return 0.0

    def guidance(x, y, z, tile_idx):
        nonlocal maxz
        if maxz < 1:
            maxz = 1
        u = (x + 0.5) / max(1, cfg.size_x)
        v = (y + 0.5) / max(1, cfg.size_y)
        target = sample01(u, v) * max(1, cfg.size_z - 1)
        if z < target - 0.5:
            m = 1.0
            if up_is_air[tile_idx]: m *= 0.1
            if up_is_ground[tile_idx]: m *= 1.5
            if dn_is_ground[tile_idx]: m *= 1.2
        elif abs(z - target) <= 0.5:
            m = 1.0
            if up_is_air[tile_idx] and dn_is_ground[tile_idx]: m *= 2.0
            elif up_is_air[tile_idx]: m *= 1.5
            elif up_is_ground[tile_idx]: m *= 0.6
        else:
            m = 0.15
            if up_is_air[tile_idx]: m *= 0.8
        return 1.0 + (m - 1.0) * influence

    return guidance
