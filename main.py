# Entry point for scripting inside Blender's Text Editor:
# Run this file to register the add-on package manually.

import bpy
import importlib

try:
    from .blender import __init__ as addon_entry
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(__file__))
    from blender import __init__ as addon_entry

def register():
    importlib.reload(addon_entry)
    addon_entry.register()

def unregister():
    addon_entry.unregister()

if __name__ == "__main__":
    register()
