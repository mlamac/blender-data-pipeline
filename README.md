# Blender Data Pipeline

A reproducible NumPy-to-OpenVDB-to-Blender pipeline for scientific scalar-field
visualization. It builds render-ready Cycles scenes with a transparent volume,
animated positive/negative isosurfaces, optional face-mounted slice plots, a
wireframe domain, STIX annotations, and a portable Windows rendering bundle.

## Requirements

- Linux preparation machine with Python 3.10 or newer.
- NumPy and OpenVDB bindings for the system Python used by the VDB bridge.
- Blender 4.0 or newer for scene creation; Blender 4.5 LTS is recommended for
  final rendering on Windows.

On Ubuntu/Debian, install the system components first:

```bash
sudo apt update
sudo apt install python3-venv python3-numpy python3-openvdb blender
```

Clone and install the Python package in an isolated environment:

```bash
git clone https://github.com/mlamac/blender-data-pipeline.git
cd blender-data-pipeline
python3 -m venv .venv
source .venv/bin/activate
./scripts/bootstrap_linux.sh
```

The OpenVDB writer deliberately uses `/usr/bin/python3`, because distro OpenVDB
bindings are normally installed there rather than inside the virtual environment.

## Quick start

```bash
bdp example --output examples/carrier_wave
bdp validate examples/carrier_wave/config.yaml
bdp build examples/carrier_wave/config.yaml \
  --blender /usr/bin/blender \
  --system-python /usr/bin/python3
```

The resulting `examples/carrier_wave/build.zip` contains `scene.blend`, VDB and
slice sequences, a manifest, and a Windows rendering helper. See
[the user manual](docs/USER_MANUAL.md) and
[the NumPy format specification](docs/NUMPY_FORMAT.md) for the complete data
workflow. The [minimal Blender tutorial](docs/BLENDER_TUTORIAL.md) explains how
to edit text, fonts, materials, shells, colorbar geometry, wireframe edges, and
animation rendering after transferring the bundle to Windows.

Generated `build/` directories and ZIP archives are intentionally ignored by
Git. Rebuild them from the tracked NumPy examples and YAML configuration.
