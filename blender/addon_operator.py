import time
import random
import bpy
from mathutils import Vector
from typing import Dict
from ..core.terrain_generator import generate
from ..core.tile import WFCTileVariant
from .blender_utils import (
    read_bases_from_collection,
    instantiate_variant,
    clear_collection,
    build_guidance_from_settings,
)

# Optional keymap for Add Props
_keymaps = []

class MARSWFC_OT_AddProps(bpy.types.Operator):
    bl_idname = "mars_wfc.add_props"
    bl_label = "Add Mars WFC Properties to Selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select at least one mesh object.")
            return {'CANCELLED'}
        for obj in sel:
            for key in ("WFC_E","WFC_W","WFC_N","WFC_S","WFC_UP","WFC_DN"):
                if key not in obj:
                    obj[key] = "*"
            if "WFC_WEIGHT" not in obj:
                obj["WFC_WEIGHT"] = 1.0
            if "WFC_ALLOW_ROT" not in obj:
                obj["WFC_ALLOW_ROT"] = True
        self.report({'INFO'}, f"Added WFC props to {len(sel)} object(s).")
        return {'FINISHED'}

class MARSWFC_OT_Generate(bpy.types.Operator):
    bl_idname = "mars_wfc.generate"
    bl_label = "Generate Terrain"
    bl_options = {'REGISTER', 'UNDO'}

    build_delay: bpy.props.FloatProperty(name="Build Step Delay (s)", default=0.02, min=0.0, max=0.5)
    repair_delay: bpy.props.FloatProperty(name="Repair Step Delay (s)", default=0.02, min=0.0, max=0.5)

    def execute(self, context):
        cfg = context.scene.mars_wfc
        coll = cfg.source_collection
        if coll is None:
            self.report({'ERROR'}, "Pick a source Collection containing your modular tiles.")
            return {'CANCELLED'}
        try:
            bases = read_bases_from_collection(coll)
        except Exception as e:
            self.report({'ERROR'}, f"Tile read failed: {e}")
            return {'CANCELLED'}

        rng = random.Random(cfg.random_seed if cfg.use_seed else None)
        guidance = build_guidance_from_settings(cfg, [])  # variants filled later in step_callback init

        out_name = cfg.output_collection_name or "WFC_Terrain"
        out_coll = bpy.data.collections.get(out_name)
        if out_coll is None:
            out_coll = bpy.data.collections.new(out_name)
            context.scene.collection.children.link(out_coll)
        if cfg.clear_output:
            clear_collection(out_coll)

        inst_map: Dict[int, bpy.types.Object] = {}
        variants_holder = {"variants": None}  # late bind

        def step_callback(phase, pos, vi):
            if variants_holder["variants"] is None:
                return
            x, y, z = pos
            idx = x + cfg.size_x * (y + cfg.size_y * z)
            variant: WFCTileVariant = variants_holder["variants"][vi]
            src_obj = bpy.data.objects.get(variant.base.name)
            if src_obj is None:
                return
            cs = cfg.cell_size
            if idx not in inst_map:
                inst = instantiate_variant(out_coll, src_obj, variant, (x, y, z), cs)
                inst_map[idx] = inst
            else:
                inst = inst_map[idx]
                inst.location = Vector((x * cs, y * cs, z * cs))
                inst.rotation_euler[2] = variant.rot * (3.141592653589793 / 2.0)
            bpy.context.view_layer.update()
            time.sleep(self.build_delay if phase == "build" else self.repair_delay)

        result = generate(
            bases=bases,
            size=(cfg.size_x, cfg.size_y, cfg.size_z),
            rng=rng,
            guidance=build_guidance_from_settings(cfg, []),  # temp None-like
            step_callback=step_callback,
            post_repair_passes=cfg.post_repair_passes,
        )

        variants_holder["variants"] = result["variants"]

        # If any placements were not visualized (e.g., zero delay), ensure they're instantiated
        for (x, y, z, vi) in result["placements"]:
            idx = x + cfg.size_x * (y + cfg.size_y * z)
            if idx in inst_map:
                continue
            variant: WFCTileVariant = result["variants"][vi]
            src_obj = bpy.data.objects.get(variant.base.name)
            if src_obj is None:
                continue
            instantiate_variant(out_coll, src_obj, variant, (x, y, z), cfg.cell_size)
        bpy.context.view_layer.update()
        self.report({'INFO'}, f"Generated {len(result['placements'])} tiles in '{out_coll.name}'.")
        return {'FINISHED'}

classes = (MARSWFC_OT_Generate, MARSWFC_OT_AddProps)

def register_keymaps():
    wm = bpy.context.window_manager
    if wm is None:
        return
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(MARSWFC_OT_AddProps.bl_idname, type='W', value='PRESS', alt=True, shift=True)
    _keymaps.append((km, kmi))

def unregister_keymaps():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()
