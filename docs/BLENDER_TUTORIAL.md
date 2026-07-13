# Minimal Blender tutorial for generated scenes

This guide assumes that the Linux pipeline has produced a portable bundle and
that the complete extracted folder is now on the Windows rendering machine. It
covers the edits most useful for publication figures without requiring prior
Blender experience.

## Open and inspect the scene

1. Extract the generated ZIP without changing its internal folder structure.
2. Open `scene.blend` in Blender 4.5 LTS.
3. Save a working copy before editing.
4. Switch the 3D viewport to **Rendered** shading with the rightmost sphere icon,
   or press `Z` and choose **Rendered**.
5. Use the timeline at the bottom to confirm that the volume, slices, sign
   shells, and phase text all advance together.

The important Outliner objects are:

| Object | Purpose |
| --- | --- |
| `Density_Volume` | Colored semi-transparent OpenVDB field |
| `Positive_Shell`, `Negative_Shell` | Red and blue surface meshes produced at render time |
| `Positive_Shell_Source`, `Negative_Shell_Source` | Animated VDB sources used by the shell modifiers |
| `Slice_X`, `Slice_Y`, `Slice_Z` | Optional animated slice-image planes |
| `Domain_Wireframe` | All 12 cube edges in one Curve object |
| `Colorbar` | Continuous PNG colorbar plane |
| `Axis_*`, `Tick_*`, `Title`, `Colorbar_*`, `Time_*` | Editable STIX text objects |

The source VDB objects are intentionally non-rendering. Do not delete them:
the visible shells reference them.

## Edit text, font, thickness, and color

Select a text object in the Outliner, then open **Object Data Properties**, the
green lowercase `a` icon.

- **Text** changes the displayed characters.
- **Size** changes glyph size. Generated labels/ticks use `0.6`; phase objects
  named `Time_####` use `0.4`.
- **Geometry > Extrude** changes text thickness. **Bevel > Depth** softens the
  glyph edges if desired.
- **Paragraph > Alignment** controls which edge remains fixed when text changes.
  Phase labels are left-aligned and use two decimal places to prevent shifting.
- **Font > Regular** changes the typeface. STIX General is already packed into
  the Blend file. To use another font, open a `.ttf`/`.otf`, then choose
  **File > External Data > Pack Resources** before transferring the scene again.

All generated text uses `Annotation_Material`. Select any label, open **Material
Properties**, select that material, and change **Principled BSDF > Base Color**.
Changing the shared material updates every annotation. Pure black is RGB
`0, 0, 0`; keep Roughness at `1` and Specular IOR Level at `0` for unlit-looking
publication text.

## Edit the wireframe

Select `Domain_Wireframe` and open **Object Data Properties**, the green curve
icon.

- **Geometry > Bevel > Depth** controls line thickness.
- Its shared `Wireframe_Material` controls color. The generated material is pure
  black with no emission or specular highlight.
- To remove selected edges, press `Tab` for Edit Mode, hover over an edge and
  press `L` to select its complete spline, then press `X` and delete the selected
  segment. Return with `Tab`. Each box edge is an independent two-point spline,
  so this does not damage neighboring edges.

## Edit the colorbar

Select `Colorbar`.

- Press `S`, then `X` to change its width in local/world X. Enter a value such
  as `1.5` and press Enter.
- To give the plane physical thickness, open **Modifiers** (wrench icon), choose
  **Add Modifier > Generate > Solidify**, and set a small Thickness such as
  `0.01`. This is usually unnecessary for a camera-facing publication render.
- Move the `Colorbar_Min`, `Colorbar_Max`, and `Colorbar_Label` text objects
  separately after resizing the bar.
- The gradient itself is `assets/colorbar.png`, using exactly the same colormap
  as the volume and slices. Rebuilding from YAML is safer than repainting it if
  scientific limits or the colormap change.

## Adjust the positive and negative shells

Select `Positive_Shell` or `Negative_Shell`, then open **Modifiers**. The
**Volume to Mesh** modifier turns the corresponding animated VDB density grid
into a surface.

- **Threshold** is the isovalue. Lower values make a larger shell; higher values
  retain only stronger field regions. The generated default is `0.25` of the
  global peak magnitude.
- **Adaptivity** reduces geometry at the cost of shape fidelity.
- **Smooth Shading** gives the surface a continuous appearance.

The materials are `Positive_Shell_Material` and `Negative_Shell_Material`.
In **Material Properties**, the most useful Principled BSDF controls are:

- **Base Color**: sign color (seismic red or blue by default).
- **Roughness**: lower values are shinier; `0.2`–`0.35` gives a plastic surface.
- **Specular IOR Level**: strength of dielectric reflections.
- **Coat Weight**: adds a clear outer highlight; the pipeline uses `0.15`.
- **Metallic**: leave at `0` for plastic rather than metal.

To make a material from scratch, select the object, open **Material Properties**,
press **New**, keep the default Principled BSDF connected to Material Output,
and set the controls above. Assign distinct materials to the two shell objects.

The colored cloud remains beneath the shells. Its strength is controlled by the
Multiply node in `Density_Volume_Material`: select `Density_Volume`, open the
**Shader Editor**, switch from Object to Material if necessary, and change the
second value of the Multiply node. Lower values make the cloud clearer; zero
hides it. Rebuilding with `shells.volume_density_multiplier` is more reproducible.

## Materials and Geometry Nodes in brief

A material controls how existing geometry interacts with light. Surface shells
use a Principled BSDF connected to the **Surface** input of Material Output. The
OpenVDB cloud instead uses a Principled Volume shader connected to **Volume**.
Slice planes and the colorbar use image textures with transparency/emission so
their scientific colors are not strongly altered by lighting.

Geometry Nodes is Blender's general node system for procedurally creating and
modifying geometry. This project uses the simpler dedicated **Volume to Mesh**
modifier because each shell needs only one operation and remains easy to edit.
An advanced equivalent Geometry Nodes graph would pass Volume geometry into a
**Volume to Mesh** node, optionally smooth or transform it, apply **Set Material**,
and connect the result to **Group Output**. Use Geometry Nodes when adding
procedural clipping, displacement, multiple thresholds, or instancing; keep the
modifier for ordinary isovalue adjustment.

## Slice planes and visibility

Use the monitor and camera icons in the Outliner to hide objects in the viewport
or final render. This is the quickest way to compare shells, volume, and slices.
The generated y slice is placed on the y-max face so it does not block the main
volume from the default camera. Moving a slice changes only its display plane,
not the coordinate from which its PNG was sampled; rebuild the bundle to change
the scientific sampling coordinate.

## Render the full animation

1. Open **Output Properties** (printer/output icon).
2. Confirm the frame range, normally `1` through `20`.
3. Choose an output directory that exists on Windows.
4. For reliable long renders, select **PNG**, RGBA or RGB, and render an image
   sequence. A stopped render can then resume at the missing frame without
   losing previous work.
5. Open **Render Properties** and keep **Cycles** for production quality. Select
   a supported GPU under **Edit > Preferences > System**, then choose GPU Compute
   as the Cycles device if desired.
6. Choose **Render > Render Animation**, or press `Ctrl+F12`.

Alternatively, with `blender.exe` on `PATH`, run `render_windows.bat` from the
bundle. Blender writes frames using the output path saved inside the scene.
Convert the resulting PNG sequence to a movie afterward; rendering directly to
video is less recoverable if Blender or the machine stops midway.

## Save portable edits

Keep `scene.blend`, `manifest.json`, and `assets/` together. Before moving a
manually changed font or other new external asset, choose **File > External Data
> Pack Resources** or **Make All Paths Relative**. The generated STIX font is
already packed, while VDB and PNG sequences intentionally remain external to
avoid making the Blend file enormous.
