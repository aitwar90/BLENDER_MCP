#include <iostream>
#include <cstdio>

#include "MEM_guardedalloc.h"

#include "BLI_listbase.hh"

#include "DNA_brush_types.h"
#include "DNA_image_types.h"
#include "DNA_listBase.h"
#include "DNA_scene_types.h"
#include "DNA_space_types.h"
#include "DNA_texture_types.h"

#include "BKE_context.hh"
#include "BKE_global.hh"
#include "BKE_image.hh"
#include "BKE_main.hh"
#include "BKE_paint.hh"

#include "ED_image.hh"
#include "ED_paint.hh"
#include "ED_screen.hh"

#include "RNA_access.hh"
#include "RNA_types.hh"
#include "WM_api.hh"
#include "WM_types.hh"

#include "paint_intern.hh"

static const char *g_mcp_slots[] = {
    "base_color", "normal", "roughness", "metallic", "ao", "height", "emission"};

extern "C" {
bool mcp_is_enabled(const blender::bContext *C);
int mcp_get_active_channels_count(void);
bool mcp_get_slot_data(int channel_index, int slot_index, blender::Image **out_target_img, blender::Tex **out_source_tex);
bool mcp_bind_slot(blender::bContext *C, blender::Brush *brush, int channel_index, const char *slot_name);
void mcp_inject_images(const blender::bContext *C, void *used_images_ptr, int *image_tot_ptr);
bool mcp_get_tex_for_image(int channel_index, blender::Image *target_img, blender::Tex **out_source_tex);
}

namespace blender::ed::sculpt_paint::mcp {

struct MCPPrepareImageEntry {
  MCPPrepareImageEntry *next, *prev;
  blender::Image *ima;
  blender::ImageUser iuser;
};

static blender::PointerRNA get_active_mcp_channel_rna(int channel_index) {
  blender::Main *bmain = blender::G.main;
  if (!bmain) return blender::PointerRNA{};

  blender::Scene *scene = static_cast<blender::Scene *>(bmain->scenes.first);
  if (!scene) return blender::PointerRNA{};

  blender::PointerRNA scene_ptr = blender::RNA_id_pointer_create(&scene->id);
  blender::PropertyRNA *channels_prop = blender::RNA_struct_find_property(&scene_ptr, "mcp_channels");
  if (!channels_prop) return blender::PointerRNA{};

  int count = blender::RNA_property_collection_length(&scene_ptr, channels_prop);
  if (channel_index < 0 || channel_index >= count) return blender::PointerRNA{};

  blender::PointerRNA channel_ptr{};
  blender::RNA_property_collection_lookup_int(&scene_ptr, channels_prop, channel_index, &channel_ptr);
  return channel_ptr;
}

static void add_image_to_used_list(blender::ListBase *used_images, int *image_tot_ptr, blender::Image *img) {
  if (!img) return;

  for (MCPPrepareImageEntry *e = static_cast<MCPPrepareImageEntry *>(used_images->first); e; e = e->next) {
    if (e->ima == img) {
      return;
    }
  }

  blender::ImageUser iuser;
  BKE_imageuser_default(&iuser);
  iuser.framenr = img->lastframe;

  if (BKE_image_has_ibuf(img, &iuser)) {
    MCPPrepareImageEntry *e = MEM_new<MCPPrepareImageEntry>("PrepareImageEntry");
    e->ima = img;
    e->iuser = iuser;
    BLI_addtail(used_images, e);
    (*image_tot_ptr)++;
    std::cout << "[MCP_LOG] Zarejestrowano obraz w projekcji MCP: " << img->id.name + 2 << "\n";
  }
}

}  // namespace blender::ed::sculpt_paint::mcp

extern "C" {

bool mcp_is_enabled(const blender::bContext *C) {
  blender::Scene *scene = nullptr;

  if (C != nullptr) {
    scene = CTX_data_scene(C);
  } 
  
  // Jeśli brak kontekstu lub kontekst nie ma sceny, spróbuj pobrać z G.main
  if (scene == nullptr && blender::G.main != nullptr) {
    scene = static_cast<blender::Scene *>(blender::G.main->scenes.first);
  }

  // Jeśli scena nadal nie istnieje (np. na wczesnym etapie startu Blendera), bezpiecznie wracamy!
  if (scene == nullptr) {
    return false;
  }

  // Zabezpieczenie RNA
  blender::PointerRNA scene_ptr = blender::RNA_id_pointer_create(reinterpret_cast<blender::ID *>(scene));
  blender::PropertyRNA *prop = blender::RNA_struct_find_property(&scene_ptr, "use_mcp");
  if (prop == nullptr) {
    return false;
  }

  return blender::RNA_property_boolean_get(&scene_ptr, prop);
}

int mcp_get_active_channels_count() {
  blender::Main *bmain = blender::G.main;
  if (!bmain) return 0;

  blender::Scene *scene = static_cast<blender::Scene *>(bmain->scenes.first);
  if (!scene) return 0;

  blender::PointerRNA scene_ptr = blender::RNA_id_pointer_create(&scene->id);
  blender::PropertyRNA *channels_prop = blender::RNA_struct_find_property(&scene_ptr, "mcp_channels");
  if (!channels_prop) return 0;

  return blender::RNA_property_collection_length(&scene_ptr, channels_prop);
}

bool mcp_get_slot_data(int channel_index, int slot_index, blender::Image **out_target_img, blender::Tex **out_source_tex) {
  if (slot_index < 0 || slot_index >= 7) return false;

  blender::PointerRNA channel_ptr = blender::ed::sculpt_paint::mcp::get_active_mcp_channel_rna(channel_index);
  if (!channel_ptr.data) return false;

  blender::PointerRNA entry_ptr = blender::RNA_pointer_get(&channel_ptr, g_mcp_slots[slot_index]);
  if (!entry_ptr.data) return false;

  blender::PointerRNA img_ptr = blender::RNA_pointer_get(&entry_ptr, "image");
  blender::PointerRNA tex_ptr = blender::RNA_pointer_get(&entry_ptr, "source_texture");

  if (out_target_img) *out_target_img = static_cast<blender::Image *>(img_ptr.data);
  if (out_source_tex) *out_source_tex = static_cast<blender::Tex *>(tex_ptr.data);

  return (img_ptr.data != nullptr);
}

bool mcp_bind_slot(blender::bContext *C, blender::Brush *brush, int channel_index, const char *slot_name) {
  if (!C || !brush) return false;

  blender::PointerRNA channel_ptr = blender::ed::sculpt_paint::mcp::get_active_mcp_channel_rna(channel_index);
  if (!channel_ptr.data) return false;

  blender::PointerRNA entry_ptr = blender::RNA_pointer_get(&channel_ptr, slot_name);
  if (!entry_ptr.data) return false;

  blender::PointerRNA tex_ptr = blender::RNA_pointer_get(&entry_ptr, "source_texture");
  if (!tex_ptr.data) return false;
  brush->mtex.tex = static_cast<blender::Tex *>(tex_ptr.data);

  blender::PointerRNA img_ptr = blender::RNA_pointer_get(&entry_ptr, "image");
  if (!img_ptr.data) return false;

  blender::Image *img = static_cast<blender::Image *>(img_ptr.data);

  blender::SpaceImage *sima = CTX_wm_space_image(C);
  if (sima) {
    sima->image = img;
    WM_main_add_notifier(NC_IMAGE | ND_DISPLAY, img);
  } else {
    blender::Scene *scene = CTX_data_scene(C);
    if (scene && scene->toolsettings) {
      scene->toolsettings->imapaint.canvas = img;
      WM_main_add_notifier(NC_IMAGE | ND_DISPLAY, img);
    }
  }

  std::cout << "[MCP_LOG] [SUKCES] Kanał " << channel_index << " -> Zmapowano slot: " << slot_name << "\n";
  return true;
}
void mcp_inject_images(const blender::bContext *C, void *used_images_ptr, int *image_tot_ptr) {
  (void)C;
  printf("\n=== [MCP DEBUG] Start mcp_inject_images ===\n");

  if (!used_images_ptr || !image_tot_ptr) {
    printf("[MCP DEBUG] BLĄD: Null pointer! used_images: %p, image_tot: %p\n", used_images_ptr, image_tot_ptr);
    return;
  }

  blender::ListBase *used_images = static_cast<blender::ListBase *>(used_images_ptr);
  int channel_count = mcp_get_active_channels_count();
  printf("[MCP DEBUG] Liczba aktywnych kanalow: %d\n", channel_count);

  int injected_count = 0;
  for (int i = 0; i < channel_count; ++i) {
    for (int s = 0; s < 7; ++s) {
      blender::Image *target_img = nullptr;
      if (mcp_get_slot_data(i, s, &target_img, nullptr) && target_img) {
        printf("[MCP DEBUG] Ch: %d, Slot: %d -> Znaleziono obraz: %s (%p)\n", i, s, target_img->id.name, target_img);
        blender::ed::sculpt_paint::mcp::add_image_to_used_list(used_images, image_tot_ptr, target_img);
        injected_count++;
      }
    }
  }
  printf("[MCP DEBUG] Wstrzyknięto obrazow: %d | ps->image_tot wynosi teraz: %d\n", injected_count, *image_tot_ptr);
  printf("=== [MCP DEBUG] Koniec mcp_inject_images ===\n\n");
}
bool mcp_get_tex_for_image(int channel_index, blender::Image *target_img, blender::Tex **out_source_tex) {
  if (!target_img) return false;
  
  for (int s = 0; s < 7; ++s) {
    blender::Image *img = nullptr;
    blender::Tex *tex = nullptr;
    if (mcp_get_slot_data(channel_index, s, &img, &tex) && img == target_img) {
      if (out_source_tex) *out_source_tex = tex;
      return true;
    }
  }
  return false;
}
}  // extern "C"