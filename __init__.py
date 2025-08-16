'''
Copyright (C) 2025 Fadi SULTAN
fadi.sultan@outlook.com

Created by Fadi SULTAN

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    "name": "Mars WFC Terrain Generator",
    "author": "Fadi SULTAN",
    "version": (1, 7, 0),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mars WFC",
    "description": "Wave Function Collapse terrain generator with weights, rotation control, heightmap guidance, and real-time build+repair visualization.",
    "warning": "This addon is still in development.",
    "category": "Object" }

import bpy
import importlib
import traceback

# --- relative imports into your existing subpackage ---
from .blender.addon_operator import classes as _addon_classes, register_keymaps, unregister_keymaps
from .blender.ui_manager import MarsWFCSettings, MARSWFC_PT_Panel
from .blender import developer_utils

# hot-reload your submodules during development
importlib.reload(developer_utils)
_reload = "bpy" in locals()
modules = developer_utils.setup_addon_modules(__path__, __name__, _reload)

def register():
    try:
        # make sure types match; convert to list if needed
        classes = list(_addon_classes) + [MarsWFCSettings, MARSWFC_PT_Panel]
        for cls in classes:
            bpy.utils.register_class(cls)
        bpy.types.Scene.mars_wfc = bpy.props.PointerProperty(type=MarsWFCSettings)
        register_keymaps()
    except Exception:
        traceback.print_exc()
    print(f"Registered {bl_info['name']} with {len(modules)} modules")

def unregister():
    try:
        unregister_keymaps()
        if hasattr(bpy.types.Scene, "mars_wfc"):
            del bpy.types.Scene.mars_wfc
        classes = list(_addon_classes) + [MarsWFCSettings, MARSWFC_PT_Panel]
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except Exception:
        traceback.print_exc()
    print(f"Unregistered {bl_info['name']}")