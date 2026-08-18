import bpy

class MCP_PT_MainPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Multi Paint'
    bl_label = 'Multi Channel Painter'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        channels = scene.mcp_channels
        active_idx = scene.mcp_active_channel

        # Przełącznik aktywności MCP
        ctrl_box = layout.box()
        row = ctrl_box.row(align=True)
        row.prop(scene, "use_mcp", text="Włącz Multi-Channel Paint", toggle=True, icon='BRUSH_DATA')

        layout.separator()

        if not channels:
            layout.label(text="Brak dodanych kanałów.", icon='INFO')
            layout.operator("multi_painter.add_channel", icon='ADD', text="Dodaj pierwszy kanał")
            return

        for i, channel in enumerate(channels):
            is_active = (i == active_idx)
            
            box = layout.box()
            row = box.row(align=True)
            
            icon = 'CHECKBOX_HLT' if is_active else 'CHECKBOX_DEHLT'

            op = row.operator(
                "multi_painter.select_channel",
                text="",
                icon=icon,
                emboss=False
            )
            op.index = i
            
            icon_expand = 'DOWNARROW_HLT' if channel.expanded else 'RIGHTARROW'

            op = row.operator(
                "multi_painter.toggle_channel",
                text="",
                icon=icon_expand,
                emboss=False
            )
            op.index = i
            
            row.prop(channel, "name", text="")
            
            op = row.operator(
                "multi_painter.remove_channel",
                text="",
                icon='TRASH'
            )
            op.index = i

            if channel.expanded:
                col = box.column(align=True)
                
                slots = [
                    ("base_color", "Base Color"),
                    ("normal", "Normal"),
                    ("roughness", "Roughness"),
                    ("metallic", "Metallic"),
                    ("ao", "AO"),
                    ("height", "Height"),
                    ("emission", "Emission")
                ]
                
                grid_header = col.row(align=True)
                grid_header.label(text="Kanał PBR")
                grid_header.label(text="Cel (Obraz)")
                grid_header.label(text="Pędzel (Tekstura)")
                col.separator()
                
                for prop_name, label in slots:
                    slot_entry = getattr(channel, prop_name, None)
                    
                    row = col.row(align=True)
                    row.label(text=label)
                    
                    if slot_entry and hasattr(slot_entry, "bl_rna") and slot_entry.bl_rna.identifier == "MCP_TextureEntry":
                        row.prop(slot_entry, "image", text="")
                        row.prop(slot_entry, "source_texture", text="", icon_only=False)
                    else:
                        row.label(text="[Błąd struktury]", icon='ERROR')
                
                layout.separator()

        layout.operator("multi_painter.add_channel", icon='ADD', text="Dodaj Kanał")