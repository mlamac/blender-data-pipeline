# Blender Data Pipeline

A reproducible NumPy-to-OpenVDB-to-Blender pipeline for scientific scalar-field
visualization. It builds render-ready Cycles scenes with a transparent volume,
optional face-mounted slice plots, a wireframe domain, annotations, and a
portable Windows rendering bundle.

## Quick start

```bash
source ~/picenv/bin/activate
./scripts/bootstrap_linux.sh
bdp example --output examples/carrier_wave
bdp validate examples/carrier_wave/config.yaml
bdp build examples/carrier_wave/config.yaml --blender /usr/bin/blender
```

The resulting `examples/carrier_wave/build.zip` contains `scene.blend`, VDB and
slice sequences, a manifest, and a Windows rendering helper. See
[the user manual](docs/USER_MANUAL.md) and
[the NumPy format specification](docs/NUMPY_FORMAT.md) for the full workflow.
