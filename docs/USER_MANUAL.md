# User manual

## Installation on the Linux preparation machine

Activate the existing environment and install the package:

```bash
cd blender-data-pipeline
source ~/picenv/bin/activate
./scripts/bootstrap_linux.sh
```

Install the Ubuntu OpenVDB bridge when prompted:

```bash
sudo apt update
sudo apt install python3-numpy python3-openvdb
```

Ubuntu's Blender 4.0 package is a supported scene-building compatibility floor;
the latest stable Blender 4.5 LTS Linux archive can alternatively be used from
`~/.local/opt/blender-4.5/blender`. Blender 4.5 LTS is recommended on the Windows
rendering machine. The exact builder version is written to `manifest.json`.

## Prepare and validate data

Follow [NUMPY_FORMAT.md](NUMPY_FORMAT.md). A minimal configuration is:

```yaml
input:
  glob: "data/density_*.npz"
output:
  directory: build
mapping:
  mode: linear              # or log10
  range: global             # or explicit with minimum/maximum
  colormap: inferno
volume:
  density_scale: 5.0
  cutoff: 0.005
geometry:
  aspect_mode: preserve_physical_aspect  # or equal_sided_cube
slices:
  - {axis: x, coordinate: 0.0, face: min}
  - {axis: z, coordinate: 0.0, face: min}
labels:
  x: "x [micrometers]"
  y: "y [micrometers]"
  z: "z [micrometers]"
  field: "electron density"
  time: "t [fs]"
  title: "EPOCH density"
```

There may be zero to three slices and no axis may occur twice. `coordinate` is
where the data are sampled; `face` is where that image is displayed. Therefore
a `z: 0` slice can be sampled through the center but displayed on the bottom
`z-min` face without cutting through the volume.

`linear` maps the selected minimum and maximum directly into 0..1. `log10`
reveals weaker structures across orders of magnitude and accepts `log_floor`.
Both mappings keep zero transparent. `density_scale` changes volume opacity
without changing the scientific color scale. `cutoff` sparsifies almost-empty
voxels after normalization. Optional `percentiles: [1, 99.8]` clips outliers;
for exact comparisons prefer explicit or un-clipped global limits.

Validate, then build:

```bash
bdp validate config.yaml
bdp build config.yaml --blender ~/.local/opt/blender-4.5/blender
```

Use `--preview` for a quick EEVEE preview and `--force` to replace an existing
build. The final saved scene remains configured for Cycles unless preview mode
is used specifically for the smoke render.

## Time series

List files explicitly to guarantee ordering, or use a zero-padded glob. Blender
frames start at 1. The VDB volume, slice images, and time annotation advance
together. A single global value range is scanned before any assets are written,
so color and opacity remain comparable across frames.

## Windows rendering

Transfer the generated ZIP and extract the whole directory. Do not move the
`assets` subdirectory away from `scene.blend`. Open the scene in Blender 4.5 LTS
or run `render_windows.bat`. The scene uses CPU-compatible Cycles defaults; select
CUDA, OptiX, HIP, or oneAPI in Blender preferences if appropriate for the Windows
GPU. Set the desired output path and format in Blender before a production render.

## Troubleshooting

- `Output exists`: inspect it, then rebuild with `--force`.
- `nonuniform`: resample each axis to uniform spacing before creating the NPZ.
- empty volume: lower `volume.cutoff` or raise `volume.density_scale`.
- oversaturated volume: lower `density_scale`; normalization and color-bar values
  remain unchanged.
- missing VDB on Windows: keep the extracted relative directory structure and use
  File > External Data > Find Missing Files only if it was changed manually.
