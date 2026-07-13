"""Headless post-build assertions; run with Blender after opening scene.blend."""

from pathlib import Path
import sys

import bpy


required = {"Density_Volume", "Domain_Wireframe", "Colorbar", "Camera", "Key_Light"}
missing = required.difference(bpy.data.objects.keys())
if missing:
    raise RuntimeError(f"scene is missing objects: {sorted(missing)}")
volume = bpy.data.objects["Density_Volume"].data
if not volume.filepath.startswith("//assets/vdb/"):
    raise RuntimeError(f"volume path is not portable: {volume.filepath}")
if bpy.context.scene.render.engine != "CYCLES":
    raise RuntimeError("saved production scene is not configured for Cycles")
if not bpy.context.scene.render.filepath.startswith("//renders/"):
    raise RuntimeError(f"render output path is not portable: {bpy.context.scene.render.filepath}")
if not Path(bpy.path.abspath(volume.filepath)).is_file():
    raise RuntimeError(f"relative VDB does not resolve: {volume.filepath}")
for image in bpy.data.images:
    if image.source in {"FILE", "SEQUENCE"} and image.filepath and not image.filepath.startswith("//assets/"):
        raise RuntimeError(f"image path is not portable: {image.filepath}")
if bpy.context.scene.frame_end > 1:
    if not volume.is_sequence or volume.frame_duration != bpy.context.scene.frame_end:
        raise RuntimeError("VDB sequence duration does not match the scene timeline")
    if any(image.source != "SEQUENCE" for image in bpy.data.images if image.filepath.startswith("//assets/slices/")):
        raise RuntimeError("slice image sequence is not configured for animation")
print(f"scene check passed: {len(bpy.data.objects)} objects, {len(bpy.data.images)} images")
