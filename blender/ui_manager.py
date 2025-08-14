import bpy

class MarsWFCSettings(bpy.types.PropertyGroup):
    source_collection: bpy.props.PointerProperty(name="Tile Collection", type=bpy.types.Collection)
    output_collection_name: bpy.props.StringProperty(name="Output Collection", default="WFC_Terrain")
    size_x: bpy.props.IntProperty(name="Size X", default=8, min=1)
    size_y: bpy.props.IntProperty(name="Size Y", default=8, min=1)
    size_z: bpy.props.IntProperty(name="Size Z", default=1, min=1)
    cell_size: bpy.props.FloatProperty(name="Cell Size", default=2.0, min=0.001)
    use_seed: bpy.props.BoolProperty(name="Use Seed", default=True)
    random_seed: bpy.props.IntProperty(name="Seed", default=42)
    use_heightmap: bpy.props.BoolProperty(name="Use Heightmap Guidance", default=False)
    heightmap_mode: bpy.props.EnumProperty(name="Source", items=[('IMAGE','Image',''),('TEXTURE','Texture','')], default='IMAGE')
    heightmap_image: bpy.props.PointerProperty(name="Heightmap Image", type=bpy.types.Image)
    heightmap_influence: bpy.props.FloatProperty(name="Heightmap Influence", default=1.0, min=0.0, max=5.0)
    post_repair_passes: bpy.props.IntProperty(name="Post-Repair Passes", default=1, min=0, max=10)
    clear_output: bpy.props.BoolProperty(name="Clear Output", default=True)

class MARSWFC_PT_Panel(bpy.types.Panel):
    bl_label = "Mars WFC"
    bl_idname = "MARSWFC_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mars WFC'

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.mars_wfc
        col = layout.column(align=True)
        col.prop(cfg, "source_collection")
        col.prop(cfg, "output_collection_name")
        grid = layout.box()
        grid.label(text="Grid")
        row = grid.row(align=True)
        row.prop(cfg, "size_x")
        row.prop(cfg, "size_y")
        row.prop(cfg, "size_z")
        grid.prop(cfg, "cell_size")
        rnd = layout.box()
        rnd.label(text="Randomness")
        rnd.prop(cfg, "use_seed")
        rnd.prop(cfg, "random_seed")
        hm = layout.box()
        hm.label(text="Heightmap Guidance")
        hm.prop(cfg, "use_heightmap")
        col2 = hm.column()
        col2.active = cfg.use_heightmap
        col2.prop(cfg, "heightmap_mode")
        if cfg.heightmap_mode == 'TEXTURE' and hasattr(bpy.types, 'Texture') and hasattr(cfg, 'heightmap_texture'):
            col2.prop(cfg, "heightmap_texture")
        if cfg.heightmap_mode == 'IMAGE':
            col2.prop(cfg, "heightmap_image")
        col2.prop(cfg, "heightmap_influence")
        post = layout.box()
        post.label(text="Post-Repair")
        post.prop(cfg, "post_repair_passes")
        layout.prop(cfg, "clear_output")
        layout.operator("mars_wfc.generate", icon='MESH_GRID')
        layout.separator()
        layout.operator("mars_wfc.add_props", icon='PLUS')
