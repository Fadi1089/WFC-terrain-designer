import bpy
import math
from mathutils import Vector
from typing import Dict, Set, List, Optional, Tuple, Callable
from .tile import WFCTile, WFCTileVariant, DIRECTIONS

# --- helpers for physical, pre-rotated_sockets asset variants ---
_DIR_TO_PROP = {d: p for (d, _, p) in DIRECTIONS}
_CARDINAL = ["NORTH", "EAST", "SOUTH", "WEST"]
_ROT_SUFFIX = {0: "", 1: "_r90", 2: "_r180", 3: "_r270"}

def _rotate_cardinal_dir(dir_name: str, rot: int) -> str:
    """Return the direction name after rot (0..3) 90° steps clockwise."""
    if dir_name not in _CARDINAL:
        return dir_name
    i = _CARDINAL.index(dir_name)
    return _CARDINAL[(i + (rot % 4)) % 4]

def _read_socket_props(obj: bpy.types.ID) -> dict:
    """Read WFC_* socket tokens from an object or data-block into a dict by DIR name."""
    sockets = {}
    for dir_name, _, prop in DIRECTIONS:
        if prop in obj:
            sockets[dir_name] = WFCTile._tokenize(obj[prop])
    return sockets

def _write_sockets_onto_object(obj: bpy.types.ID, sockets_by_dir: dict) -> None:
    """Write WFC_* socket tokens into an object (string form, comma-joined)."""
    for dir_name, _, prop in DIRECTIONS:
        tokens = sockets_by_dir.get(dir_name, ["*"])
        obj[prop] = ",".join(tokens) if isinstance(tokens, (list, tuple, set)) else str(tokens)

def _rotate_sockets(orig: dict, rot: int) -> dict:
    """Rotate a sockets dict keyed by DIR names, remapping keys (UP/DOWN unchanged)."""
    out = {}
    for dir_name in _CARDINAL:
        out[_rotate_cardinal_dir(dir_name, rot)] = list(orig.get(dir_name, ["*"]))
    out["UP"]   = list(orig.get("UP",   ["*"]))
    out["DOWN"] = list(orig.get("DOWN", ["*"]))
    return out

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

            # Hide for convenience
            try:
                # Hiding in viewport uses the monitor screen icon.
                # This may not be visible unless you select it from the filter icon in the top right corner.
                dup.hide_viewport = True
            except Exception:
                print("failed to hide tile variant")
                pass

            coll.objects.link(dup)
            created += 1
    return created

def sockets_from_object(obj: bpy.types.Object) -> Dict[str, Set[str]]:
    sockets = {}
    chain = (getattr(obj, "data", None), obj)
    for dir_name, _, prop in DIRECTIONS:
        tokens = None
        for source in chain:
            if source and prop in source:
                tokens = WFCTile._tokenize(source[prop])
                break
        if tokens is None:
            tokens = ["*"]
        sockets[dir_name] = set(tokens)
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

def read_bases_from_collection(coll: bpy.types.Collection) -> List[WFCTile]:
    tiles = []
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            sockets = sockets_from_object(obj)
            weight = weight_from_object(obj)
            allow_rot = allow_rot_from_object(obj)
            tiles.append(WFCTile(obj.name, sockets, weight, allow_rot))
    if not tiles:
        raise ValueError("Selected collection has no mesh objects.")
    return tiles

def instantiate_variant(
    out_coll: bpy.types.Collection,
    src_obj: bpy.types.Object,
    variant: WFCTileVariant,
    pos: Tuple[float, float, float],
    cell_size: float
) -> bpy.types.Object:

   # Guard clauses
    if src_obj is None or src_obj.type != 'MESH' or src_obj.data is None:
        print(f"instantiate_variant: invalid source object '{getattr(src_obj, 'name', None)}'")
        return None
    if out_coll is None:
        print("instantiate_variant: invalid output collection")
        return None

    # Duplicate object; SHARE the mesh (lighter than copying mesh data)
    inst = src_obj.copy()
    inst.data = src_obj.data
    print(f"instantiate_variant: {inst.name} copied successfully")

    # Ensure visible in viewport/render
    try:
        inst.hide_set(False)
    except Exception:
        pass
    inst.hide_viewport = False
    inst.hide_render = False

    # Place and rotate (90° steps around Z)
    x, y, z = pos
    inst.location = Vector((x * cell_size, y * cell_size, z * cell_size))
    inst.rotation_euler.z = (variant.rot % 4) * (math.pi / 2.0)

    # Link to target collection
    out_coll.objects.link(inst)

    # Update depsgraph so transforms/visibility take effect
    bpy.context.view_layer.update()

    return inst

def update_instance(inst_variant: bpy.types.Object, variant: WFCTileVariant):
    # Mesh data remains as-is; only the rotation is variant-specific here.
    inst_variant.rotation_euler[2] = variant.rot * (math.pi / 2.0)

def clear_collection(out_coll: bpy.types.Collection):
    for obj in list(out_coll.objects):
        out_coll.objects.unlink(obj)
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass

def build_guidance_from_settings(cfg, variants: List[WFCTileVariant]) -> Optional[Callable]:
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

    up_is_air = [('air' in v.sockets.get('UP', set())) for v in variants]
    up_is_ground = [('ground' in v.sockets.get('UP', set())) for v in variants]
    dn_is_ground = [('ground' in v.sockets.get('DOWN', set())) for v in variants]

    def sample01(u, v):
        if sampler_tex is not None:
            s = sampler_tex(u, v)
            if s is not None:
                return s
        if sampler_img is not None:
            return sampler_img(u, v)
        return 0.0

    def guidance(x, y, z, vi):
        nonlocal maxz
        if maxz < 1:
            maxz = 1
        u = (x + 0.5) / max(1, cfg.size_x)
        v = (y + 0.5) / max(1, cfg.size_y)
        target = sample01(u, v) * max(1, cfg.size_z - 1)
        if z < target - 0.5:
            m = 1.0
            if up_is_air[vi]: m *= 0.1
            if up_is_ground[vi]: m *= 1.5
            if dn_is_ground[vi]: m *= 1.2
        elif abs(z - target) <= 0.5:
            m = 1.0
            if up_is_air[vi] and dn_is_ground[vi]: m *= 2.0
            elif up_is_air[vi]: m *= 1.5
            elif up_is_ground[vi]: m *= 0.6
        else:
            m = 0.15
            if up_is_air[vi]: m *= 0.8
        return 1.0 + (m - 1.0) * influence

    return guidance
