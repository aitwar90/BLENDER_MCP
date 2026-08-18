import bpy

TEXTURE_TYPES = [
    ('BASE_COLOR', "Base Color", ""),
    ('NORMAL', "Normal", ""),
    ('ROUGHNESS', "Roughness", ""),
    ('METALLIC', "Metallic", ""),
    ('AO', "Ambient Occlusion", ""),
    ('HEIGHT', "Height", ""),
    ('EMISSION', "Emission", ""),
]

class MCP_TextureEntry(bpy.types.PropertyGroup):
    texture_type: bpy.props.EnumProperty(
        name="Type",
        items=TEXTURE_TYPES,
        default='BASE_COLOR'
    )
    image: bpy.props.PointerProperty(
        name="Target Image",
        type=bpy.types.Image
    )
    source_texture: bpy.props.PointerProperty(
        name="Source Texture",
        type=bpy.types.Texture,
        description="Tekstura/maska pędzla przypisana do tego kanału"
    )
    expanded: bpy.props.BoolProperty(
        default=True
    )

class MCP_Channel(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Channel")
    expanded: bpy.props.BoolProperty(name="Expanded", default=True)
    
    # Bezpieczne dowiązanie typu przez nazwę klasy zarejestrowanej w Blenderze
    base_color: bpy.props.PointerProperty(type=MCP_TextureEntry)
    normal: bpy.props.PointerProperty(type=MCP_TextureEntry)
    roughness: bpy.props.PointerProperty(type=MCP_TextureEntry)
    metallic: bpy.props.PointerProperty(type=MCP_TextureEntry)
    ao: bpy.props.PointerProperty(type=MCP_TextureEntry)
    height: bpy.props.PointerProperty(type=MCP_TextureEntry)
    emission: bpy.props.PointerProperty(type=MCP_TextureEntry)

# Globalna rejestracja właściwości w scenie z poprawnym wcięciem
bpy.types.Scene.mcp_active_channel = bpy.props.IntProperty(
    name="Aktywny kanał",
    default=0,
)
    
def sanitize_mcp_data(scene):
    """Skanuje i czyści stare/uszkodzone struktury danych w kolekcji mcp_channels."""
    if not hasattr(scene, "mcp_channels"):
        return

    map_slots = ["base_color", "normal", "roughness", "metallic", "ao", "height", "emission"]
    
    # Przechodzimy od końca, na wypadek gdyby trzeba było usunąć cały uszkodzony kanał
    for i in range(len(scene.mcp_channels) - 1, -1, -1):
        channel = scene.mcp_channels[i]
        
        # Sprawdzamy każdy slot PBR w kanale
        for slot in map_slots:
            try:
                entry = getattr(channel, slot, None)
                
                # Jeśli slot istnieje, ale nie jest naszą nową klasą PropertyGroup (czyli jest starym Image)
                if entry and (not hasattr(entry, "bl_rna") or entry.bl_rna.identifier != "MCP_TextureEntry"):
                    print(f"[MCP FIX] Wykryto uszkodzone dane w kanale {channel.name}, slot: {slot}. Czyszczenie bufora...")
                    
                    # Blender nie pozwala łatwo podmienić typu PointerProperty w locie, 
                    # dlatego najbezpieczniejszą metodą jest usunięcie całego skażonego kanału.
                    scene.mcp_channels.remove(i)
                    break
                    
            except Exception as e:
                # Jeśli samo odpytanie pola rzuca błędem w C++ – kanał jest trupem, usuwamy
                print(f"[MCP CRITICAL FIX] Kanał {i} jest uszkodzony estructuralnie: {e}. Usuwanie.")
                scene.mcp_channels.remove(i)
                break