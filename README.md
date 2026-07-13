# Blender Data Pipeline

A reproducible NumPy-to-OpenVDB-to-Blender pipeline for scientific scalar-field
visualization. It builds render-ready Cycles scenes with a transparent volume,
optional face-mounted slice plots, a wireframe domain, annotations, and a
portable Windows rendering bundle.

## Quick start

```bash
source ~/picenv/bin/activate
./scripts/bootstrap_linux.sh
bdp example --output examples/gaussian
bdp validate examples/gaussian/config.yaml
bdp build examples/gaussian/config.yaml --blender /usr/bin/blender
```

The resulting `examples/gaussian/build.zip` contains `scene.blend`, VDB and
slice sequences, a manifest, and a Windows rendering helper. See
[the user manual](docs/USER_MANUAL.md) and
[the NumPy format specification](docs/NUMPY_FORMAT.md) for the full workflow.
