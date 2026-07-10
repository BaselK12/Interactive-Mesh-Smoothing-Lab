# Mesh Smoothing Learning Summary

## Experiment settings
- Mesh: Cube
- Summary state: committed working mesh
- Mesh type: quad mesh
- Smoothing mode: Global smoothing
- Selected method: Uniform Laplacian
- Iterations per apply: 0
- Total iterations applied: 0
- Lambda: 0.30
- Preserve boundary: True

## Metrics (original vs current)
| Metric | Original | Current | Change |
| --- | --- | --- | --- |
| Vertices | 8 | 8 | 0 |
| Faces | 6 | 6 | 0 |
| Bounding box diagonal | 1.7321 | 1.7321 | +0.00% |
| Surface area | 6.0000 | 6.0000 | +0.00% |
| Volume | 1.0000 | 1.0000 | +0.00% |
| Roughness energy | 0.5774 | 0.5774 | +0.00% |

## Smoothing history
No smoothing actions recorded yet.

## What the metrics mean
- **Roughness energy**: average distance from each vertex to the average of its neighbors. Lower is smoother.
- **Bounding box / surface area / volume change**: how much the mesh shrank or grew. Negative usually means shrinkage.
- **Displacement**: how far vertices moved from the original.

## Limitations
- Uniform Laplacian smoothing shrinks meshes; Taubin reduces this.
- Cotangent smoothing supports triangle meshes only.
- Volume is available only for closed, watertight meshes.
- Local soft regions use graph distance, not Euclidean distance.