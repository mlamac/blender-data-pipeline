# NumPy input format

Each simulation frame is one compressed or uncompressed NumPy `.npz` file. It
must contain these arrays:

| Key | Type and shape | Meaning |
| --- | --- | --- |
| `field` | finite, non-negative numeric `(nx, ny, nz)` | Density sampled in `(x, y, z)` order |
| `x` | numeric `(nx,)` | Physical x coordinates |
| `y` | numeric `(ny,)` | Physical y coordinates |
| `z` | numeric `(nz,)` | Physical z coordinates |
| `time` | optional scalar | Simulation time; required on every frame in a series |

Axes must be strictly monotonic and uniformly spaced. Increasing and decreasing
axes are accepted. All files in a series must have identical axes and shape, and
their `time` values must increase in filename/configuration order. Values and
coordinates must not contain NaN or infinity.

The key name `field` can be changed with `input.field_key`. Coordinate units and
display labels belong in YAML rather than the NPZ so the numeric contract remains
simple and independent of EPOCH/SDF.

```python
import numpy as np

x = np.linspace(-10e-6, 10e-6, 128)
y = np.linspace(-10e-6, 10e-6, 128)
z = np.linspace(-5e-6, 5e-6, 64)
density_xyz = np.asarray(epoch_density, dtype=np.float32)
assert density_xyz.shape == (x.size, y.size, z.size)
np.savez_compressed(
    "density_0042.npz",
    field=density_xyz,
    x=x,
    y=y,
    z=z,
    time=np.array(42.0e-15),
)
```

If the source array is stored as `(z, y, x)`, transpose it explicitly with
`source.transpose(2, 1, 0)`. Run `bdp validate config.yaml` before a full build;
the example marker-field tests guard against accidental transposition but cannot
infer the intended source convention.

Nonuniform rectilinear coordinates must currently be resampled before export.
This keeps OpenVDB voxel transforms and slice locations unambiguous.
