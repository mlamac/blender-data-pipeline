"""Build a render-ready Blender scene from a prepared bundle manifest.

Run through Blender, not ordinary Python:
blender --background --factory-startup --python scripts/build_scene.py -- ...
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def rgba(value):
    result = list(value)
    while len(result) < 4:
        result.append(1.0)
    return tuple(result[:4])


def material_surface(name, color, emission=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = rgba(color)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba(color)
    principled.inputs["Roughness"].default_value = 0.55
    if emission:
        emission_input = principled.inputs.get("Emission Color") or principled.inputs.get("Emission")
        emission_input.default_value = rgba(color)
        principled.inputs["Emission Strength"].default_value = emission
    return material


def curve_segments(name, segments, material, radius):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    for start, end in segments:
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(name, curve)
    curve.materials.append(material)
    bpy.context.collection.objects.link(obj)
    return obj


def text_object(name, body, location, size, material, align="CENTER"):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = size * 0.008
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    curve.materials.append(material)
    bpy.context.collection.objects.link(obj)
    # Face the camera via a constraint; it remains editable in the final scene.
    return obj


def create_box(bounds, material):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    corners = [(x, y, z) for x in (xmin, xmax) for y in (ymin, ymax) for z in (zmin, zmax)]
    segments = []
    for i, a in enumerate(corners):
        for b in corners[i + 1 :]:
            if sum(a[j] != b[j] for j in range(3)) == 1:
                segments.append((a, b))
    return curve_segments("Domain_Wireframe", segments, material, max(xmax - xmin, ymax - ymin, zmax - zmin) * 0.006)


def create_volume(manifest, root, bounds):
    volume_data = bpy.data.volumes.new("Density_VDB")
    absolute = root / manifest["vdb_files"][0]
    volume_data.filepath = str(absolute)
    volume_data.is_sequence = manifest["frame_count"] > 1
    volume_data.frame_start = 1
    volume_data.frame_duration = manifest["frame_count"]
    volume_data.sequence_mode = "CLIP"
    obj = bpy.data.objects.new("Density_Volume", volume_data)
    bpy.context.collection.objects.link(obj)
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    shape = manifest["shape"]
    obj.scale = ((xmax - xmin) / max(shape[0] - 1, 1), (ymax - ymin) / max(shape[1] - 1, 1), (zmax - zmin) / max(shape[2] - 1, 1))
    obj.location = (xmin, ymin, zmin)
    material = bpy.data.materials.new("Density_Volume_Material")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeVolumePrincipled")
    info = nodes.new("ShaderNodeVolumeInfo")
    multiply = nodes.new("ShaderNodeMath")
    multiply.operation = "MULTIPLY"
    multiply.inputs[1].default_value = float(manifest["volume"]["density_scale"])
    links = material.node_tree.links
    links.new(info.outputs["Density"], multiply.inputs[0])
    links.new(info.outputs["Color"], principled.inputs["Color"])
    links.new(multiply.outputs[0], principled.inputs["Density"])
    links.new(principled.outputs["Volume"], output.inputs["Volume"])
    volume_data.materials.append(material)
    return obj, volume_data


def image_material(name, image_path, frame_count):
    image = bpy.data.images.load(str(image_path), check_existing=False)
    if frame_count > 1:
        image.source = "SEQUENCE"
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    if hasattr(material, "surface_render_method") and hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False
    if hasattr(material, "shadow_method"):
        material.shadow_method = "NONE"
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.image_user.frame_duration = frame_count
    texture.image_user.frame_start = 1
    texture.image_user.use_auto_refresh = True
    emission = nodes.new("ShaderNodeEmission")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links = material.node_tree.links
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 0.8
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    return material, image


def slice_vertices(axis, position, bounds, epsilon):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    if axis == "x":
        x = position + epsilon
        return [(x, ymin, zmin), (x, ymax, zmin), (x, ymax, zmax), (x, ymin, zmax)]
    if axis == "y":
        y = position + epsilon
        return [(xmin, y, zmin), (xmax, y, zmin), (xmax, y, zmax), (xmin, y, zmax)]
    z = position + epsilon
    return [(xmin, ymin, z), (xmax, ymin, z), (xmax, ymax, z), (xmin, ymax, z)]


def create_slices(manifest, root, bounds):
    size = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
    images = []
    for spec in manifest["slices"]:
        axis = spec["axis"]
        axis_index = "xyz".index(axis)
        position = bounds[2 * axis_index + (1 if spec["face"] == "max" else 0)]
        sign = -1 if spec["face"] == "max" else 1
        vertices = slice_vertices(axis, position, bounds, sign * size * 0.002)
        mesh = bpy.data.meshes.new(f"Slice_{axis.upper()}_Mesh")
        mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
        uv = mesh.uv_layers.new(name="UVMap")
        for loop, coordinate in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
            uv.data[loop].uv = coordinate
        obj = bpy.data.objects.new(f"Slice_{axis.upper()}", mesh)
        bpy.context.collection.objects.link(obj)
        material, image = image_material(f"Slice_{axis.upper()}_Material", root / spec["files"][0], manifest["frame_count"])
        mesh.materials.append(material)
        images.append((image, spec["files"][0]))
    return images


def create_colorbar(manifest, root, bounds):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    size = max(xmax - xmin, ymax - ymin, zmax - zmin)
    center_x = xmax + 0.28 * size
    half_width = 0.035 * size
    y = ymax + 0.01 * size
    vertices = [
        (center_x - half_width, y, zmin),
        (center_x + half_width, y, zmin),
        (center_x + half_width, y, zmax),
        (center_x - half_width, y, zmax),
    ]
    mesh = bpy.data.meshes.new("Colorbar_Mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, coordinate in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[loop].uv = coordinate
    obj = bpy.data.objects.new("Colorbar", mesh)
    bpy.context.collection.objects.link(obj)
    relative = manifest["colorbar_file"]
    material, image = image_material("Colorbar_Material", root / relative, 1)
    mesh.materials.append(material)
    return image, relative


def create_annotations(manifest, bounds, camera):
    annotation = material_surface("Annotation_Material", manifest["scene"]["annotation_color"], 0.0)
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    size = max(xmax - xmin, ymax - ymin, zmax - zmin)
    labels = manifest["labels"]
    objects = [
        text_object("Axis_X", labels["x"], ((xmin + xmax) / 2, ymin - 0.12 * size, zmin - 0.07 * size), 0.09 * size, annotation),
        text_object("Axis_Y", labels["y"], (xmax + 0.11 * size, (ymin + ymax) / 2, zmin - 0.07 * size), 0.09 * size, annotation),
        text_object("Axis_Z", labels["z"], (xmin - 0.10 * size, ymin, (zmin + zmax) / 2), 0.09 * size, annotation),
    ]
    if labels.get("title"):
        objects.append(text_object("Title", labels["title"], ((xmin + xmax) / 2, (ymin + ymax) / 2, zmax + 0.28 * size), 0.10 * size, annotation))
    # Endpoint tick labels preserve physical coordinate values even in equal-cube mode.
    for axis_i, axis in enumerate("xyz"):
        scene_min, scene_max = bounds[2 * axis_i : 2 * axis_i + 2]
        data_min, data_max = manifest["extents"][axis]
        for suffix, scene_value, data_value in (("min", scene_min, data_min), ("max", scene_max, data_max)):
            location = [xmin - 0.055 * size, ymin - 0.055 * size, zmin - 0.055 * size]
            location[axis_i] = scene_value
            if axis == "y":
                location[0] = xmax + 0.055 * size
            objects.append(text_object(f"Tick_{axis}_{suffix}", f"{data_value:.3g}", location, 0.045 * size, annotation))
    bar_x, bar_y = xmax + 0.28 * size, ymax
    low, high = manifest["value_limits"]
    objects.extend([
        text_object("Colorbar_Min", f"{low:.3g}", (bar_x + 0.07 * size, bar_y, zmin), 0.045 * size, annotation, "LEFT"),
        text_object("Colorbar_Max", f"{high:.3g}", (bar_x + 0.07 * size, bar_y, zmax), 0.045 * size, annotation, "LEFT"),
        text_object("Colorbar_Label", labels["field"], (bar_x, bar_y, zmax + 0.09 * size), 0.055 * size, annotation),
    ])
    for index, time in enumerate(manifest["times"], 1):
        obj = text_object(f"Time_{index:04d}", f"{labels['time']} = {time:.5g}", (xmax, ymax, zmax + 0.12 * size), 0.055 * size, annotation)
        obj.hide_render = index != 1
        obj.keyframe_insert("hide_render", frame=max(1, index - 1))
        obj.hide_render = False
        obj.keyframe_insert("hide_render", frame=index)
        obj.hide_render = True
        obj.keyframe_insert("hide_render", frame=index + 1)
        objects.append(obj)
    for obj in objects:
        constraint = obj.constraints.new("COPY_ROTATION")
        constraint.target = camera
    return objects


def point_camera(camera, target=(0, 0, 0)):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def scene_dimensions(manifest):
    extents = manifest["extents"]
    physical = [extents[a][1] - extents[a][0] for a in "xyz"]
    box_size = float(manifest["geometry"]["box_size"])
    if manifest["geometry"].get("aspect_mode") == "equal_sided_cube":
        sizes = [box_size] * 3
    elif manifest["geometry"].get("aspect_mode") == "preserve_physical_aspect":
        scale = box_size / max(physical)
        sizes = [value * scale for value in physical]
    else:
        raise ValueError("geometry.aspect_mode must be preserve_physical_aspect or equal_sided_cube")
    return (-sizes[0] / 2, sizes[0] / 2, -sizes[1] / 2, sizes[1] / 2, -sizes[2] / 2, sizes[2] / 2)


def build(manifest, root, output, preview):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = manifest["scene"]["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "//renders/frame_"
    scene.frame_start = 1
    scene.frame_end = manifest["frame_count"]
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if "None" in {item.name for item in scene.view_settings.bl_rna.properties["look"].enum_items}:
        scene.view_settings.look = "None"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = int(manifest["scene"]["samples"])
        scene.cycles.use_denoising = True
    world = bpy.data.worlds.new("Scientific_World") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = rgba(manifest["scene"]["background"])
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = float(manifest["scene"].get("background_strength", 1.0))
    bounds = scene_dimensions(manifest)
    wire = material_surface("Wireframe_Material", manifest["scene"]["wire_color"], 0.2)
    create_box(bounds, wire)
    volume_obj, volume_data = create_volume(manifest, root, bounds)
    images = create_slices(manifest, root, bounds)
    images.append(create_colorbar(manifest, root, bounds))
    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    size = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
    direction = Vector(manifest["scene"]["camera"]).normalized()
    camera.location = direction * (size * 4.2)
    camera.data.lens = float(manifest["scene"]["lens_mm"])
    point_camera(camera)
    scene.camera = camera
    create_annotations(manifest, bounds, camera)
    bpy.ops.object.light_add(type="AREA", location=(size * 2, -size * 2, size * 2.5))
    light = bpy.context.object
    light.name = "Key_Light"
    light.data.energy = 900.0
    light.data.shape = "DISK"
    light.data.size = size * 2
    point_camera(light)
    # Save once while files are absolute and loaded, then make all external paths portable.
    bpy.context.preferences.filepaths.save_version = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    volume_data.filepath = "//" + manifest["vdb_files"][0].replace("\\", "/")
    for image, relative in images:
        image.filepath = "//" + relative.replace("\\", "/")
    scene["bdp_manifest"] = "//manifest.json"
    scene["bdp_blender_version"] = bpy.app.version_string
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    if preview:
        # EEVEE was renamed in Blender 4.2. Version testing keeps 4.0 as a useful
        # compatibility floor while the prepared deliverable targets 4.5 LTS.
        scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
        scene.render.resolution_percentage = 50
        scene.render.filepath = str(output.parent / "preview.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = arguments()
    manifest_path = Path(args.manifest).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["blender_version"] = bpy.app.version_string
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    build(data, manifest_path.parent, Path(args.output).resolve(), args.preview)
