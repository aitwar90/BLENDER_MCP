#!/usr/bin/env python3
import os
import shutil
import subprocess
import re

BLENDER_ROOT = "/media/aitwarcl/b6fec136-6fdf-43ec-aa0e-0c5f6a0afa37/BlenderRepo/blender_proj/BLENDER_MCP/blender-main/blender"
TARGET_DIR = os.path.join(BLENDER_ROOT, "source/blender/editors/sculpt_paint")

LOCAL_WRAPPER = "paint_mcp.cc"
LOCAL_ADDON_DIR = "multi_painter"


def reset_git_files():
    print("[MCP] Przywracanie czystego stanu z Git...")
    files_to_reset = [
        os.path.join(TARGET_DIR, "CMakeLists.txt"),
        os.path.join(TARGET_DIR, "paint_intern.hh"),
        os.path.join(TARGET_DIR, "paint_ops.cc"),
        os.path.join(TARGET_DIR, "mesh/paint_image_ops_paint.cc"),
        os.path.join(TARGET_DIR, "mesh/paint_image_proj.cc"),
        os.path.join(BLENDER_ROOT, "source/blender/blenkernel/intern/image_gpu.cc"),
        os.path.join(BLENDER_ROOT, "source/blender/blenkernel/intern/pbvh_pixels.cc"),
    ]
    for file_path in files_to_reset:
        if os.path.exists(file_path):
            try:
                subprocess.run(
                    ["git", "checkout", "HEAD", "--", file_path],
                    cwd=BLENDER_ROOT,
                    check=True,
                    capture_output=True,
                )
                print(f"  -> Przywrócono: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  -> [BŁĄD GIT] {os.path.basename(file_path)}: {e}")

def patch_paint_proj():
    proj_path = os.path.join(TARGET_DIR, "mesh/paint_image_proj.cc")
    print(f"[MCP] Patchowanie: {proj_path}")

    with open(proj_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Jawne deklaracje typów w przestrzeni blender::
    declaration = """#include "BKE_context.hh"

namespace blender {
struct Image;
struct Tex;
}

extern "C" {
  bool mcp_is_enabled(const blender::bContext *C);
  void mcp_inject_images(const blender::bContext *C, void *used_images_ptr, int *image_tot_ptr);
  bool mcp_get_slot_data(
    int channel_index, int slot_index, blender::Image **out_target_img, blender::Tex **out_source_tex);
  bool mcp_get_tex_for_image(int channel_index, blender::Image *target_img, blender::Tex **out_source_tex);
}
"""
    if "mcp_get_tex_for_image" not in content:
        content = declaration + content

    # 2. Patch w project_paint_prepare_all_faces
    target_prep = """  /* Build an array of images we use. */
  if (ps->is_shared_user == false) {
    project_paint_build_proj_ima(ps, arena, &used_images);
  }"""

    replacement_prep = """  /* 2. Wstrzyknięcie kanałów MCP PO zebraniu siatki, żeby dopisać je na koniec listy used_images */
  if (mcp_is_enabled(nullptr)) {
    mcp_inject_images(nullptr, &used_images, &ps->image_tot);
    //printf("[MCP DEBUG] Po wstrzyknieciu MCP, finalne image_tot = %d\\n", ps->image_tot);
  }

  /* 3. Alokacja buforów dla wszystkich obrazów (w tym MCP) */
  if (ps->is_shared_user == false) {
    //printf("[MCP DEBUG] ps->is_shared_user = false czyli co? \\n");
    project_paint_build_proj_ima(ps, arena, &used_images);
  }"""

    if target_prep in content:
        content = content.replace(target_prep, replacement_prep, 1)
    else:
        print("  -> BŁĄD: Nie znaleziono punktu wywołania project_paint_build_proj_ima!")
        return False

    # 3. Bezpieczny replacement bez zjadania funkcji – dopasowanie po ścisłej strukturze
    pattern_thread = (
        r"default:\s*\n?"
        r"\s*if\s*\(\s*is_floatbuf\s*\)\s*\{\s*\n?"
        r"\s*do_projectpaint_draw_f\(\s*ps,\s*projPixel,\s*texrgb,\s*mask\s*\);\s*\n?"
        r"\s*\}\s*\n?"
        r"\s*else\s*\{\s*\n?"
        r"\s*do_projectpaint_draw\(\s*\n?"
        r"\s*ps,\s*projPixel,\s*texrgb,\s*mask,\s*ps->dither,\s*projPixel->x_px,\s*projPixel->y_px\s*\);\s*\n?"
        r"\s*\}\s*\n?"
        r"\s*break;"
    )

    replacement_thread = """default:
                  if (mcp_is_enabled(nullptr) && ps->image_tot > 1) {
                    const int orig_img_idx = projPixel->image_index;
                    void *orig_color_pt = projPixel->origColor.ch_pt;

                    float3 samplecos = {projPixel->projCoSS[0], projPixel->projCoSS[1], 0.0f};

                    for (int img_i = 0; img_i < ps->image_tot; img_i++) {
                      ProjPaintImage *cur_ima = projImages + img_i;
                      cur_ima->touch = true;

                      const bool cur_is_float = (cur_ima->ibuf->float_data() != nullptr);
                      projPixel->image_index = img_i;

                      float channel_texrgb[3];
                      copy_v3_v3(channel_texrgb, texrgb);

                      blender::Tex *source_tex = nullptr;
                      const int active_chan = 0;

                      if (mcp_get_tex_for_image(active_chan, cur_ima->ima, &source_tex) && source_tex) {
                        MTex mtex_tmp = {};
                        mtex_tmp.tex = source_tex;
                        mtex_tmp.brush_map_mode = MTEX_MAP_MODE_VIEW;
                        
                        float4 texrgba;
                        BKE_brush_sample_tex_3d(ps->paint, brush, &mtex_tmp, samplecos, texrgba, thread_index, pool);
                        copy_v3_v3(channel_texrgb, texrgba);
                      }

                      if (cur_is_float) {
                        projPixel->origColor.f_pt = cur_ima->float_data_mut + projPixel->pixel_offset;
                        do_projectpaint_draw_f(ps, projPixel, channel_texrgb, mask);
                      }
                      else {
                        projPixel->origColor.ch_pt = cur_ima->byte_data_mut + projPixel->pixel_offset;
                        do_projectpaint_draw(
                            ps, projPixel, channel_texrgb, mask, ps->dither, projPixel->x_px, projPixel->y_px);
                      }

                      ImagePaintPartialRedraw *redraw_cell = cur_ima->partRedrawRect + projPixel->bb_cell_index;
                      image_paint_partial_redraw_expand(redraw_cell, projPixel);
                    }

                    projPixel->image_index = orig_img_idx;
                    projPixel->origColor.ch_pt = static_cast<uint8_t *>(orig_color_pt);
                  }
                  else {
                    if (is_floatbuf) {
                      do_projectpaint_draw_f(ps, projPixel, texrgb, mask);
                    }
                    else {
                      do_projectpaint_draw(
                          ps, projPixel, texrgb, mask, ps->dither, projPixel->x_px, projPixel->y_px);
                    }
                  }
                  break;"""

    new_content, count = re.subn(pattern_thread, replacement_thread, content, count=1)
    if count > 0:
        with open(proj_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("  -> Pomyślnie zapatczowano paint_image_proj.cc!")
        return True

    print("  -> BŁĄD: Nie znaleziono bloku default w do_projectpaint_thread!")
    return False

def patch_cmake():
    cmake_path = os.path.join(TARGET_DIR, "CMakeLists.txt")
    with open(cmake_path, "r", encoding="utf-8") as f:
        content = f.read()
    anchor = "paint_curve.cc"
    if anchor in content and LOCAL_WRAPPER not in content:
        content = content.replace(anchor, f"{anchor}\n  {LOCAL_WRAPPER}", 1)
        with open(cmake_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  -> Dodano paint_mcp.cc do CMakeLists.txt")
        return True
    return True


def deploy_python_addon():
    addons_target_path = os.path.join(
        BLENDER_ROOT, "release", "scripts", "addons", LOCAL_ADDON_DIR
    )
    if not os.path.exists(LOCAL_ADDON_DIR):
        return True
    try:
        if os.path.exists(addons_target_path):
            shutil.rmtree(addons_target_path)
        shutil.copytree(LOCAL_ADDON_DIR, addons_target_path)
        print("  -> Addon skopiowany pomyślnie!")
        return True
    except Exception as e:
        print(f"  -> BŁĄD kopiowania addonu: {e}")
        return False


def main():
    print("=== [MCP BUILD & HOOK SYSTEM] ===")
    reset_git_files()

    dest_wrapper = os.path.join(TARGET_DIR, LOCAL_WRAPPER)
    if os.path.exists(LOCAL_WRAPPER):
        shutil.copyfile(LOCAL_WRAPPER, dest_wrapper)

    if not patch_cmake() or not patch_paint_proj():
        print("\n[MCP] Błąd patchowania. Przerywam.")
        return

    deploy_python_addon()

    print("\n[MCP] Uruchamiam kompilację (make)...")
    try:
        jobs = f"-j{os.cpu_count() or 4}"
        result = subprocess.run(["make", jobs], cwd=BLENDER_ROOT)
        if result.returncode == 0:
            print("\n=== [SUKCES] Kompilacja gotowa! ===")
    except Exception as e:
        print(f"\n[MCP] Błąd uruchomienia make: {e}")


if __name__ == "__main__":
    main()