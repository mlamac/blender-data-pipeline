"""Headless post-build assertions; run with Blender after opening scene.blend."""

from pathlib import Path
import sys

import bpy


required = {
    "Density_Volume", "Positive_Shell", "Negative_Shell", "Positive_Shell_Source",
    "Negative_Shell_Source", "Domain_Wireframe", "Colorbar", "Camera", "Key_Light",
}
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
for name in ("Positive_Shell_Source", "Negative_Shell_Source"):
    source = bpy.data.objects[name].data
    if not source.filepath.startswith("//assets/vdb/") or not Path(bpy.path.abspath(source.filepath)).is_file():
        raise RuntimeError(f"shell VDB path is not portable: {source.filepath}")
    if source.frame_duration != bpy.context.scene.frame_end:
        raise RuntimeError(f"shell sequence duration is wrong for {name}")
for name in ("Positive_Shell", "Negative_Shell"):
    modifiers = [modifier for modifier in bpy.data.objects[name].modifiers if modifier.type == "VOLUME_TO_MESH"]
    if len(modifiers) != 1 or abs(modifiers[0].threshold - 0.25) > 1e-6:
        raise RuntimeError(f"{name} is missing its configured Volume to Mesh modifier")
wire = bpy.data.objects["Domain_Wireframe"]
if len(wire.data.splines) != 12:
    raise RuntimeError("the complete cube wireframe must contain all 12 edges")
for material_name in ("Wireframe_Material", "Annotation_Material"):
    material = bpy.data.materials[material_name]
    if tuple(material.diffuse_color) != (0.0, 0.0, 0.0, 1.0):
        raise RuntimeError(f"{material_name} is not pure black")
for obj in (item for item in bpy.data.objects if item.type == "FONT"):
    expected = 0.4 if obj.name.startswith("Time_") else 0.6
    if abs(obj.data.size - expected) > 1e-6 or "STIX" not in obj.data.font.name.upper():
        raise RuntimeError(f"incorrect typography on {obj.name}")
for obj in (item for item in bpy.data.objects if item.name.startswith("Time_")):
    if obj.data.align_x != "LEFT" or len(obj.data.body.rsplit("=", 1)[-1].strip().split(".")[-1]) != 2:
        raise RuntimeError(f"unstable time-label formatting on {obj.name}")
for image in bpy.data.images:
    if image.source in {"FILE", "SEQUENCE"} and image.filepath and not image.filepath.startswith("//assets/"):
        raise RuntimeError(f"image path is not portable: {image.filepath}")
if bpy.context.scene.frame_end > 1:
    if not volume.is_sequence or volume.frame_duration != bpy.context.scene.frame_end:
        raise RuntimeError("VDB sequence duration does not match the scene timeline")
    if any(image.source != "SEQUENCE" for image in bpy.data.images if image.filepath.startswith("//assets/slices/")):
        raise RuntimeError("slice image sequence is not configured for animation")
print(f"scene check passed: {len(bpy.data.objects)} objects, {len(bpy.data.images)} images")
