import time
from typing import Tuple, Callable, Optional
import random
import bpy
from mathutils import Vector
from typing import Dict

from .terrain_generator import generate
from .tile import WFCTile

# relative to this subpackage (`blender/`)
from .blender_utils import (
    read_bases_from_collection,
    instantiate_variant,
    build_guidance_from_settings,
    create_rotated_variations_in_collection
)

# class to create the rotated variations of every tile
# in the source collection that has a WFC_ALLOW_ROT property set to True
class MARSWFC_OT_CreateVariations(bpy.types.Operator):
    bl_idname = "mars_wfc.create_variations"
    bl_label = "Create Tile Variations"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cfg = context.scene.mars_wfc
        collection = cfg.source_collection
        if collection is None:
            self.report({'ERROR'}, "Pick a source Collection containing your modular tiles.")
            return {'CANCELLED'}
        try:
            created = create_rotated_variations_in_collection(collection)
        except Exception as e:
            self.report({'ERROR'}, f"Variation build failed: {e}")
            return {'CANCELLED'}
        bpy.context.view_layer.update()
        self.report({'INFO'}, f"Created {created} rotated variation object(s).")
        return {'FINISHED'}

# Optional keymap for Add Props
_keymaps = []

# class to add properties to the selected objects
class MARSWFC_OT_AddProps(bpy.types.Operator):
    bl_idname = "mars_wfc.add_props"
    bl_label = "Add Mars WFC Properties to Selected"
    bl_options = {"REGISTER", "UNDO"}

    '''
    tile_idx always means "which tile type"
    grid_idx always means "which grid position"
    tile always means "the WFCTile object"
    bases always means "list of available tile types"
    '''

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select at least one mesh object.")
            return {'CANCELLED'}
        for obj in sel:
            for key in ("WFC_E", "WFC_W", "WFC_N", "WFC_S", "WFC_UP", "WFC_DN"):
                if key not in obj:
                    obj[key] = "*"
            if "WFC_WEIGHT" not in obj:
                obj["WFC_WEIGHT"] = 1.0
            if "WFC_ALLOW_ROT" not in obj:
                obj["WFC_ALLOW_ROT"] = True
        self.report({'INFO'}, f"Added WFC props to {len(sel)} object(s).")
        return {'FINISHED'}


# class to generate the terrain
class MARSWFC_OT_Generate(bpy.types.Operator):
    bl_idname = "mars_wfc.generate"
    bl_label = "Generate Terrain"
    bl_options = {'REGISTER', 'UNDO'}

    build_delay: bpy.props.FloatProperty(
        name="Build Step Delay (s)", default=0.01, min=0.0, max=0.5
    )

    def execute(self, context):
        # Get configuration from UI
        cfg = context.scene.mars_wfc

        # Get the source collection from the UI
        collection = cfg.source_collection

        # Validate source collection exists
        if collection is None:
            self.report({'ERROR'}, "Pick a source Collection containing your modular tiles.")
            return {'CANCELLED'}

        # Read all tile objects from the collection
        try:
            bases = read_bases_from_collection(collection)
        except Exception as e:
            self.report({'ERROR'}, f"Tile reading failed. Identified the following cause: {e}")
            return {'CANCELLED'}

        # Create a random number generator to be used later in the generate function
        rng = random.Random(cfg.random_seed if cfg.use_seed else None)
        
        # If no name is provided, use "WFC_Terrain" as default
        out_name = cfg.output_collection_name or "WFC_Terrain"

        # Get the output collection name from the UI
        out_coll = bpy.data.collections.get(out_name)

        # If the output collection does not exist, create it
        if out_coll is None:
            out_coll = bpy.data.collections.new(out_name)
            context.scene.collection.children.link(out_coll)

        # If the clear output option is enabled, clear the output collection every time the generate function is called
        if cfg.clear_output:
            for obj in list(out_coll.objects):
                out_coll.objects.unlink(obj)
                bpy.data.objects.remove(obj, do_unlink=True)

        # Create a mapping dictionary that keeps track of which 3D objects have been created,
        # and at which grid positions during the terrain generation process.
        instantiated_objects_map: Dict[int, bpy.types.Object] = {}

        # a callback function to be called at each step of the generation process
        def step_callback(pos: Tuple[int, int, int], tile_idx: int):
            # If the bases are not yet created, return None
            if bases is None:
                return

            # Get the coordinates (position) of the tile
            x, y, z = pos

            # Calculate the index of the tile in the grid's flattened 1D array
            # Represents the physical position of the tile in the 3D grid
            # Is a unique identifier for each grid cell
            # Key in the instantiated_objects_map dictionary
            grid_idx = x + cfg.size_x * (y + cfg.size_y * z)

            # Get the tile from the bases using the tile_idx
            # This represents which tile type was chosen for this position
            tile: WFCTile = bases[tile_idx]

            # Get the source object from the tile
            src_obj = bpy.data.objects.get(tile.name)

            # If the source object is not found, return None
            if src_obj is None:
                return

            # Get the cell size from the configuration (the size of the tiles in the grid)
            cell_size = cfg.cell_size

            # If the tile is not yet instantiated, instantiate it
            if grid_idx not in instantiated_objects_map:
                instantiated_object = instantiate_variant(out_coll, src_obj, tile, (x, y, z), cell_size)
                instantiated_objects_map[grid_idx] = instantiated_object
            # Else if the tile is already instantiated, update its location and rotation
            else:
                instantiated_object = instantiated_objects_map[grid_idx]
                instantiated_object.location = Vector((x * cell_size, y * cell_size, z * cell_size))
            
            # Update the view layer and wait for the build step delay
            bpy.context.view_layer.update()
            time.sleep(self.build_delay)
            bpy.context.view_layer.update()

        # TODO : Add a button to the UI to save the generated terrain as a .fbx file

        '''
        a function that controls where and how tiles are placed during terrain generation
        based on a heightmap (either an image or texture).
        Essentially a "smart placement system" that makes the terrain follow elevation patterns.
        '''
        guidance: Optional[Callable] = build_guidance_from_settings(cfg, bases)

        # Generate the terrain using the WFC algorithm
        result = generate(
            bases=bases,
            size=(cfg.size_x, cfg.size_y, cfg.size_z),
            rng=rng,
            guidance=guidance,
            step_callback=step_callback
        )

        # Instantiate the tiles that were not instantiated during the generation process
        # This is done to ensure that all tiles are instantiated
        # This is necessary because the step_callback function is not called for all tiles
        # and some tiles may not be instantiated if they are not in the guidance function
        for (x, y, z, tile_idx) in result["placements"]:
            grid_idx = x + cfg.size_x * (y + cfg.size_y * z)
            if grid_idx in instantiated_objects_map:
                continue
            tile: WFCTile = result["bases"][tile_idx]
            src_obj = bpy.data.objects.get(tile.name)
            if src_obj is None:
                continue
            instantiate_variant(out_coll, src_obj, tile, (x, y, z), cfg.cell_size)

        # Update the view layer and wait for the build step delay
        bpy.context.view_layer.update()
        self.report({'INFO'}, f"Generated {len(result['placements'])} tiles in '{out_coll.name}'.")
        return {'FINISHED'}

# Register the classes
classes = (MARSWFC_OT_Generate, MARSWFC_OT_AddProps, MARSWFC_OT_CreateVariations)

# Register the keymaps
def register_keymaps():
    wm = bpy.context.window_manager
    if wm is None:
        return
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(MARSWFC_OT_AddProps.bl_idname, type='W', value='PRESS', alt=True, shift=True)
    _keymaps.append((km, kmi))

# Unregister the keymaps
def unregister_keymaps():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()
