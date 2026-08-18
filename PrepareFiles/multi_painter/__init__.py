bl_info = {
    "name": "Multi Channel Painter",
    "author": "Aitwar",
    "version": (0, 2, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Multi Paint",
    "description": "Synchronizacja Texture Paint pomiędzy wieloma teksturami.",
    "category": "Paint"
}

import bpy
from bpy.app import handlers

from . import properties
from . import ui
from . import operators

classes = (
    properties.MCP_TextureEntry,
    properties.MCP_Channel,
    operators.MCP_OT_SelectChannel,
    operators.MCP_OT_ToggleChannel,
    operators.MCP_OT_AddChannel,
    operators.MCP_OT_RemoveChannel,
    operators.MCP_OT_StartPainting,
    ui.MCP_PT_MainPanel
)

@handlers.persistent
def on_file_load(dummy):
    context = bpy.context
    if context and hasattr(context, "scene") and context.scene:
        properties.sanitize_mcp_data(context.scene)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Błąd rejestracji klasy {cls}: {e}")

    try:
        bpy.types.Scene.mcp_channels = bpy.props.CollectionProperty(type=properties.MCP_Channel)
        bpy.types.Scene.mcp_active_channel = bpy.props.IntProperty(name="Active Channel", default=0)
        bpy.types.Scene.use_mcp = bpy.props.BoolProperty(name="Włącz MCP", default=False)
    except Exception as e:
        print(f"Błąd rejestracji właściwości sceny: {e}")

    if on_file_load not in handlers.load_post:
        handlers.load_post.append(on_file_load)

def unregister():
    if on_file_load in handlers.load_post:
        handlers.load_post.remove(on_file_load)

    try:
        if hasattr(bpy.types.Scene, "mcp_channels"):
            del bpy.types.Scene.mcp_channels
        if hasattr(bpy.types.Scene, "mcp_active_channel"):
            del bpy.types.Scene.mcp_active_channel
        if hasattr(bpy.types.Scene, "use_mcp"):
            del bpy.types.Scene.use_mcp
    except:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Błąd odrejestrowania klasy {cls}: {e}")

if __name__ == "__main__":
    register()