# User manual

## Installation on the Linux preparation machine

Install the Ubuntu system components:

```bash
sudo apt update
sudo apt install python3-venv python3-numpy python3-openvdb blender
```

Then clone the repository, create an environment, and install the package:

```bash
git clone https://github.com/mlamac/blender-data-pipeline.git
cd blender-data-pipeline
python3 -m venv .venv
source .venv/bin/activate
./scripts/bootstrap_linux.sh
```

Ubuntu's Blender 4.0 package is a supported scene-building compatibility floor;
the latest stable Blender 4.5 LTS Linux archive can alternatively be used from
`~/.local/opt/blender-4.5/blender`. Blender 4.5 LTS is recommended on the Windows
rendering machine. The exact builder version is written to `manifest.json`.

Generate the included-style demonstration with `bdp example`. By default it
creates 20 frames of a stationary 3D Gaussian envelope multiplied by a carrier
whose phase advances along x. It uses `seismic` over the fixed range `[-2, 2]`,
plus animated red and blue sign shells.

## Prepare and validate data

Follow [NUMPY_FORMAT.md](NUMPY_FORMAT.md). A minimal configuration is:

```yaml
input:
  glob: "data/density_*.npz"
output:
  directory: build
mapping:
  mode: linear              # or log10
  range: explicit           # or global
  minimum: -2.0
  maximum: 2.0
  transparent_value: 0.0
  colormap: seismic
volume:
  density_scale: 5.0
  cutoff: 0.005
shells:
  enabled: true
  isovalue: 0.25
  volume_density_multiplier: 0.5
geometry:
  aspect_mode: preserve_physical_aspect  # or equal_sided_cube
slices:
  - {axis: x, coordinate: 0.0, face: min}
  - {axis: y, coordinate: 0.0, face: max} # back face: does not hide volume
  - {axis: z, coordinate: 0.0, face: min}
labels:
  x: "x [micrometers]"
  y: "y [micrometers]"
  z: "z [micrometers]"
  field: "E / E0"
  time: "t [fs]"
  title: "Laser pulse"
```

There may be zero to three slices and no axis may occur twice. `coordinate` is
where the data are sampled; `face` is where that image is displayed. Therefore
a `z: 0` slice can be sampled through the center but displayed on the bottom
`z-min` face without cutting through the volume.

`linear` maps the selected minimum and maximum directly into 0..1. With
`symmetric: true`, limits become `[-max(abs(field)), +max(abs(field))]`, which is
appropriate for diverging maps such as `seismic`. Color represents signed value
while transparency follows distance from `transparent_value`, normally zero.
Color normalization is deliberately independent from opacity and shell
normalization: an explicit color range of `[-2, 2]` will not make a dataset with
peak amplitude 1 half-transparent.
`log10` reveals weaker positive structures across orders of magnitude and accepts
`log_floor`; it cannot be combined with a symmetric signed range. `density_scale`
changes volume opacity without changing the scientific color scale. `cutoff`
sparsifies almost-empty voxels after normalization. Optional
`percentiles: [1, 99.8]` clips outliers; for exact comparisons prefer explicit or
un-clipped global limits. The continuous color bar is generated as a PNG and uses
the same normalization and Matplotlib colormap as the volume and slices.

The default publication theme has a white world background with black wireframe,
ticks, and annotations. All annotations use STIX General; the font is copied into
the bundle and packed into the Blend file, so the Windows machine does not need
it installed. Labels, titles, and numeric ticks use Blender size 0.6; the animated
phase annotation uses size 0.4.
Override `scene.background`, `scene.wire_color`, and `scene.annotation_color`
with RGBA arrays when a dark or custom theme is needed.

### Configuration reference

- `input.files` is an explicitly ordered file list; `input.glob` is the compact
  alternative for consistently zero-padded filenames. `input.field_key` changes
  the NPZ scalar-array key from its default, `field`.
- `output.directory` is resolved relative to the YAML file. `output.archive`
  controls creation of the portable ZIP and defaults to true.
- `mapping` controls scientific color normalization. Use `range: explicit` with
  `minimum`/`maximum` for comparisons across datasets, or `range: global` to scan
  all frames. `symmetric`, `percentiles`, `log_floor`, `transparent_value`, and
  any Matplotlib `colormap` are supported as described above.
- `volume.density_scale` affects rendered optical density. `volume.cutoff`
  discards weak normalized voxels to reduce VDB size.
- `shells` controls the signed isosurfaces and their materials; see the next
  section.
- `geometry.aspect_mode` either preserves physical axis ratios or forces an
  equal-sided cube. `box_size` sets the longest displayed side in Blender units.
- `slices` accepts at most one entry per axis. Sampling `coordinate` and display
  `face` are independent.
- `labels` controls all displayed strings. Blender text is not a LaTeX renderer;
  use plain portable text such as `E / E0` unless the selected font is known to
  contain a desired Unicode symbol.
- `scene` can override `resolution`, Cycles `samples`, preview samples, camera
  direction, lens, background strength/color, wire color, and annotation color.
  Colors are linear RGBA arrays with four values from 0 to 1.

## Positive and negative shells

Shells are enabled by default. The processor writes separate normalized
positive and negative VDB sequences and Blender converts them to animated meshes
with editable **Volume to Mesh** modifiers. The default `isovalue: 0.25` means a
surface is drawn where the signed magnitude reaches 25% of the global peak
magnitude. The shell scale is global across all frames, so the geometry does not
change merely because a frame has a weaker peak.

The two surface materials are named `Positive_Shell_Material` and
`Negative_Shell_Material`. Their publication defaults are seismic red/blue,
roughness 0.28, and coat weight 0.15. The original colored cloud remains visible
at half density; adjust `volume_density_multiplier` from 0 to 1 to hide it or
restore its full strength. Set `shells.enabled: false` for the former volume-only
scene. Colors and material defaults can also be overridden:

```yaml
shells:
  positive_color: [0.9941, 0.0, 0.0, 1.0]
  negative_color: [0.0039, 0.0039, 1.0, 1.0]
  roughness: 0.28
  coat_weight: 0.15
```

Validate, then build:

```bash
bdp validate config.yaml
bdp build config.yaml \
  --blender /usr/bin/blender \
  --system-python /usr/bin/python3
```

Use `--preview` for a quick EEVEE preview and `--force` to replace an existing
build. The final saved scene remains configured for Cycles unless preview mode
is used specifically for the smoke render.

The build directory contains:

```text
build/
  scene.blend
  manifest.json
  render_windows.bat
  WINDOWS_README.txt
  assets/
    colorbar.png
    fonts/
    slices/
    vdb/
  renders/                 # created when animation frames are rendered
```

The manifest records the resolved limits, extents, frame times, asset paths, and
builder version. Treat it as useful provenance, but change the YAML and rebuild
rather than editing the manifest by hand.

## Time series

List files explicitly to guarantee ordering, or use a zero-padded glob. Blender
frames start at 1. The VDB volume, signed shells, slice images, and time
annotation advance together. A single global amplitude is scanned before any
assets are written, so opacity and shell geometry remain comparable across
frames. Phase text uses two decimal places and a fixed left anchor, preventing
the annotation from shifting as its digits change.

## Windows rendering

Transfer the generated ZIP and extract the whole directory. Do not move the
`assets` subdirectory away from `scene.blend`. Open the scene in Blender 4.5 LTS
or run `render_windows.bat`. The scene uses CPU-compatible Cycles defaults; select
CUDA, OptiX, HIP, or oneAPI in Blender preferences if appropriate for the Windows
GPU. Set the desired output path and format in Blender before a production render.
See [BLENDER_TUTORIAL.md](BLENDER_TUTORIAL.md) for a guided tour of the generated
scene and safe publication-oriented edits.

## Troubleshooting

- `Output exists`: inspect it, then rebuild with `--force`.
- `nonuniform`: resample each axis to uniform spacing before creating the NPZ.
- empty volume: lower `volume.cutoff` or raise `volume.density_scale`.
- missing shells: lower `shells.isovalue`; positive-only data naturally has an
  empty negative shell.
- oversaturated volume: lower `density_scale`; normalization and color-bar values
  remain unchanged.
- missing VDB on Windows: keep the extracted relative directory structure and use
  File > External Data > Find Missing Files only if it was changed manually.
