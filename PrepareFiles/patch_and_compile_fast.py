import os, subprocess

BLENDER_ROOT = "/media/aitwarcl/b6fec136-6fdf-43ec-aa0e-0c5f6a0afa37/BlenderRepo/blender_proj/BLENDER_MCP/blender-main/blender"
jobs = f"-j{os.cpu_count() or 4}"
subprocess.run(["make", jobs], cwd=BLENDER_ROOT)
