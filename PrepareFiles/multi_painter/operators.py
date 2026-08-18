import bpy

class MCP_OT_SelectChannel(bpy.types.Operator):
    bl_idname = "multi_painter.select_channel"
    bl_label = "Wybierz kanał"

    index: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.mcp_active_channel = self.index
        return {'FINISHED'}

class MCP_OT_ToggleChannel(bpy.types.Operator):
    bl_idname = "multi_painter.toggle_channel"
    bl_label = "Rozwiń / Zwiń"

    index: bpy.props.IntProperty()

    def execute(self, context):
        channel = context.scene.mcp_channels[self.index]
        channel.expanded = not channel.expanded
        return {'FINISHED'}

class MCP_OT_AddChannel(bpy.types.Operator):
    bl_idname = "multi_painter.add_channel"
    bl_label = "Dodaj Kanał"

    def execute(self, context):
        scene = context.scene

        new_channel = scene.mcp_channels.add()
        new_channel.name = f"Kanał {len(scene.mcp_channels)}"
        
        map_slots = ["base_color", "normal", "roughness", "metallic", "ao", "height", "emission"]
        for slot in map_slots:
            entry = getattr(new_channel, slot)
            if entry:
                entry.texture_type = slot.upper()

        scene.mcp_active_channel = len(scene.mcp_channels) - 1
        self.report({'INFO'}, f"Dodano kanał {scene.mcp_active_channel + 1}")
        return {'FINISHED'}

class MCP_OT_RemoveChannel(bpy.types.Operator):
    bl_idname = "multi_painter.remove_channel"
    bl_label = "Usuń"

    index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene

        if len(scene.mcp_channels) <= 1:
            self.report({'WARNING'}, "Nie można usunąć ostatniego kanału.")
            return {'CANCELLED'}

        idx = self.index
        scene.mcp_channels.remove(idx)

        if scene.mcp_active_channel > idx:
            scene.mcp_active_channel -= 1
        elif scene.mcp_active_channel >= len(scene.mcp_channels):
            scene.mcp_active_channel = max(0, len(scene.mcp_channels) - 1)

        self.report({'INFO'}, f"Usunięto kanał {idx+1}")
        return {'FINISHED'}

class MCP_OT_StartPainting(bpy.types.Operator):
    bl_idname = "multi_painter.start_painting"
    bl_label = "Przełącz MCP"
    bl_description = "Włącza/Wyłącza tryb malowania wielokanałowego w silniku"

    def execute(self, context):
        scene = context.scene
        scene.use_mcp = not scene.use_mcp
        
        if scene.use_mcp:
            if context.active_object and context.active_object.mode != 'TEXTURE_PAINT':
                bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
            self.report({'INFO'}, "MCP: Włączono malowanie wielokanałowe.")
        else:
            self.report({'INFO'}, "MCP: Wyłączono malowanie wielokanałowe.")
            
        return {'FINISHED'}