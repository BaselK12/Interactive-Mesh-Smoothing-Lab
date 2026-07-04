# Smoothing Methods

This lab implements four smoothing behaviors. All of them reuse the mesh
connectivity unchanged, so vertex/face/edge counts never change — only vertex
positions move.

## 1. Uniform Laplacian (neighbor-average) smoothing

For each movable vertex `v` with one-ring neighbors `N(v)`:

```
neighbor_average = mean(position of each neighbor)
v_new = v + lambda * (neighbor_average - v)
```

- `lambda` (0..1) controls how far the vertex moves each iteration.
- Every neighbor has equal influence, so the result depends mainly on
  connectivity.
- **Shrinkage:** repeatedly averaging pulls vertices inward, so closed shapes get
  smaller. This is the classic problem the other methods address.

## 2. Taubin smoothing (lambda / mu)

Each iteration applies two uniform-Laplacian steps:

```
v = v + lambda * (neighbor_average - v)   # positive smoothing step
v = v + mu     * (neighbor_average - v)   # negative correction step, mu < 0
```

Recommended defaults: `lambda = 0.5`, `mu = -0.53`.

- The positive step smooths; the negative step pushes back out to counteract
  shrinkage.
- Result: the mesh smooths while keeping its size much better than plain
  Laplacian smoothing.
- In the lab, Taubin typically shows a small bounding-box change where uniform
  smoothing shows a large one.

## 3. Cotangent-weighted Laplacian smoothing

For a triangle edge `(i, j)`, the weight is:

```
w_ij = 0.5 * (cot(alpha) + cot(beta))
```

where `alpha` and `beta` are the angles opposite the edge in the two triangles
sharing it (one triangle for a boundary edge). Cotangents are computed robustly
as:

```
cot(theta) = dot(a, b) / ||cross(a, b)||
```

The vertex update uses the normalized weighted average of neighbors:

```
target = sum_j (w_ij * position_j) / sum_j w_ij
v_new  = v + strength * (target - v)
```

- **Geometry-aware:** neighbors are weighted by triangle shape, not just
  connectivity, so it behaves differently on irregular triangulations.
- **Triangle meshes only.** On non-triangle meshes the lab disables it with a
  clear warning rather than producing wrong geometry.
- **Safety:** degenerate triangles (near-zero cross product) contribute zero;
  negative weights from obtuse triangles are clamped to zero so the weighted
  average stays inside the neighbor hull and smoothing cannot explode. This is a
  stability-focused simplification of the exact cotangent operator.

## 4. Local / soft-selection smoothing

Uniform smoothing scaled by a soft-selection weight based on graph distance from
a chosen center vertex:

```
v_new = v + strength * local_weight(v) * (neighbor_average - v)
```

- `local_weight` is 1 at the center and falls off (linear or smoothstep) to 0 at
  the selected graph radius.
- Vertices outside the radius are unchanged, giving a localized "soft brush"
  effect.

## Boundary preservation

When enabled, vertices on boundary edges (edges belonging to exactly one face)
are held fixed for every method. This keeps open meshes such as the plane/grid
from collapsing inward at their border.
