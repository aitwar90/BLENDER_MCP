#!/usr/bin/env python3
import os
import shutil
import subprocess
import re
import sys

# Dynamiczne wyznaczanie sciezek
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

BLENDER_ROOT = os.path.join(BASE_DIR, "blender-main", "blender")
TARGET_DIR = os.path.join(BLENDER_ROOT, "source/blender/editors/sculpt_paint")

LOCAL_WRAPPER_NAME = "paint_mcp.cc"
LOCAL_WRAPPER_SRC = os.path.join(SCRIPT_DIR, LOCAL_WRAPPER_NAME)

LOCAL_ADDON_NAME = "multi_painter"
LOCAL_ADDON_SRC = os.path.join(SCRIPT_DIR, LOCAL_ADDON_NAME)


def reset_git_files():
    git_dir = os.path.join(BLENDER_ROOT, ".git")
    if not os.path.exists(git_dir):
        print("[MCP] Brak repozytorium Git w katalogu Blendera. Pomijam resetowanie plikow.")
        return
    
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
                print(f"  -> Przywrocono: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  -> [BLAD GIT] {os.path.basename(file_path)}: {e}")


def patch_paint_proj():
    proj_path = os.path.join(TARGET_DIR, "mesh/paint_image_proj.cc")
    print(f"[MCP] Patchowanie: {proj_path}")

    if not os.path.exists(proj_path):
        print(f"  -> BLAD: Plik nie istnieje pod sciezka {proj_path}")
        return False

    with open(proj_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Normalizacja koncowek linii (CRLF -> LF)
    content = content.replace("\r\n", "\n")

    # Sygnatura sprawdzajaca, czy plik zawiera juz nasze modyfikacje
    MCP_MARKER = "/* MCP_PATCH_APPLIED */"

    if MCP_MARKER in content:
        print("  -> INFO: Poprawki MCP sa juz nalozone na paint_image_proj.cc. Pomijam.")
        return True

    # 1. Deklaracja MCP
    declaration = f"""{MCP_MARKER}
#include "BKE_context.hh"

namespace blender {{
struct Image;
struct Tex;
}}

extern "C" {{
  bool mcp_is_enabled(const blender::bContext *C);
  void mcp_inject_images(const blender::bContext *C, void *used_images_ptr, int *image_tot_ptr);
  bool mcp_get_slot_data(
    int channel_index, int slot_index, blender::Image **out_target_img, blender::Tex **out_source_tex);
  bool mcp_get_tex_for_image(int channel_index, blender::Image *target_img, blender::Tex **out_source_tex);
}}
"""
    if "mcp_get_tex_for_image" not in content:
        content = declaration + content

    # 2. Szukanie miejsca wywolania project_paint_build_proj_ima
    pattern_prep = r"(if\s*\(\s*ps->is_shared_user\s*==\s*false\s*\)\s*\{\s*project_paint_build_proj_ima\(\s*ps,\s*arena,\s*&used_images\s*\);\s*\})"

    replacement_prep = """  /* 2. Wstrzykniecie kanalow MCP */
  if (mcp_is_enabled(nullptr)) {
    mcp_inject_images(nullptr, &used_images, &ps->image_tot);
  }

  /* 3. Alokacja buforow dla wszystkich obrazow (w tym MCP) */
  if (ps->is_shared_user == false) {
    project_paint_build_proj_ima(ps, arena, &used_images);
  }"""

    new_content, count_prep = re.subn(pattern_prep, replacement_prep, content, count=1)
    if count_prep == 0:
        print("  -> BLAD: Brak wzorca dla project_paint_build_proj_ima w kodzie Blendera!")
        return False
    content = new_content

    # 3. Patch bloku default
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

    new_content, count_thread = re.subn(pattern_thread, replacement_thread, content, count=1)
    if count_thread == 0:
        print("  -> BLAD: Brak bloku default w do_projectpaint_thread w kodzie Blendera!")
        return False

    with open(proj_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("  -> Pomyslnie zapatczowano paint_image_proj.cc!")
    return True


def patch_cmake():
    cmake_path = os.path.join(TARGET_DIR, "CMakeLists.txt")
    if not os.path.exists(cmake_path):
        print(f"  -> BLAD: CMakeLists.txt nie istnieje pod {cmake_path}")
        return False

    with open(cmake_path, "r", encoding="utf-8") as f:
        content = f.read()

    if LOCAL_WRAPPER_NAME in content:
        print("  -> INFO: paint_mcp.cc znajduje sie juz w CMakeLists.txt. Pomijam.")
        return True

    anchor = "paint_curve.cc"
    if anchor in content:
        content = content.replace(anchor, f"{anchor}\n  {LOCAL_WRAPPER_NAME}", 1)
        with open(cmake_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  -> Dodano paint_mcp.cc do CMakeLists.txt")
        return True

    print(f"  -> BLAD: Nie znaleziono kotwicy '{anchor}' w CMakeLists.txt!")
    return False


def deploy_python_addon():
    addons_target_path = os.path.join(
        BLENDER_ROOT, "release", "scripts", "addons", LOCAL_ADDON_NAME
    )
    if not os.path.exists(LOCAL_ADDON_SRC):
        print(f"  -> OSTRZEZENIE: Brak katalogu zrodlowego addonu pod {LOCAL_ADDON_SRC}, pomijam.")
        return True
    try:
        if os.path.exists(addons_target_path):
            shutil.rmtree(addons_target_path)
        shutil.copytree(LOCAL_ADDON_SRC, addons_target_path)
        print("  -> Addon skopiowany pomyslnie!")
        return True
    except Exception as e:
        print(f"  -> BLAD kopiowania addonu: {e}")
        return False


def compile_blender_linux():
    print("\n[MCP] Wykryto system Linux. Uruchamianie kompilacji (make)...")
    try:
        cmd = ["make", "-C", BLENDER_ROOT]
        print(f"  -> Wykonywanie: {' '.join(cmd)}")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("\n[MCP BLAD] Kompilacja na Linuksie zakonczona niepowodzeniem!")
            return False
        print("\n[MCP] Kompilacja zakonczona sukcesem!")
        return True
    except Exception as e:
        print(f"\n[MCP BLAD] Nie udalo sie uruchomic procesu kompilacji: {e}")
        return False


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=== [MCP BUILD & HOOK SYSTEM] ===")
    
    reset_git_files()

    dest_wrapper = os.path.join(TARGET_DIR, LOCAL_WRAPPER_NAME)
    if os.path.exists(LOCAL_WRAPPER_SRC):
        shutil.copyfile(LOCAL_WRAPPER_SRC, dest_wrapper)
        print(f"  -> Skopiowano/nadpisano wrapper: {LOCAL_WRAPPER_NAME}")
    else:
        print(f"  -> BLAD: Brak pliku zrodlowego wrappera pod {LOCAL_WRAPPER_SRC}!")
        sys.exit(1)

    cmake_ok = patch_cmake()
    proj_ok = patch_paint_proj()

    if not cmake_ok or not proj_ok:
        print("\n[MCP] Blad patchowania - nie udalo sie nalozyc modyfikacji. Przerywam.")
        sys.exit(1)

    deploy_python_addon()

    # Dedykowany krok kompilacji dla środowiska Linux
    if sys.platform.startswith("linux"):
        if not compile_blender_linux():
            sys.exit(1)

    print("\n=== [SUKCES] Proces zakonczony pomyslnie! ===")


if __name__ == "__main__":
    main()