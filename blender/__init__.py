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


# load and reload submodules
##################################

import importlib
from .addon_operator import classes as _addon_classes, register_keymaps, unregister_keymaps
from .ui_manager import MarsWFCSettings, MARSWFC_PT_Panel
from . import developer_utils
importlib.reload(developer_utils)
modules = developer_utils.setup_addon_modules(__path__, __name__, "bpy" in locals())


# register
##################################

import traceback

def register():
    try:
        for cls in _addon_classes + (MarsWFCSettings, MARSWFC_PT_Panel):
            bpy.utils.register_class(cls)
        bpy.types.Scene.mars_wfc = bpy.props.PointerProperty(type=MarsWFCSettings)
        register_keymaps()
    except: traceback.print_exc()
    print("Registered {} with {} modules".format(bl_info["name"], len(modules)))


def unregister():
    try:
        unregister_keymaps()
        if hasattr(bpy.types.Scene, "mars_wfc"):
            del bpy.types.Scene.mars_wfc
        for cls in reversed(_addon_classes + (MarsWFCSettings, MARSWFC_PT_Panel)):
            bpy.utils.unregister_class(cls)
    except: traceback.print_exc()
    print("Unregistered {}".format(bl_info["name"]))
