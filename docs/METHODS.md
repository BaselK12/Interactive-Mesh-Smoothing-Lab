# Smoothing Methods

This lab implements four smoothing behaviors. All of them reuse the mesh
connectivity unchanged, so vertex/face/edge counts never change — only vertex
positions move. Uniform, Cotangent, and local passes use **synchronous
updates**: every vertex reads its neighbors' *old* positions. A Taubin
iteration contains two synchronous passes; its negative `mu` pass reads the
positions produced by its positive `lambda` pass.

Provenance note: uniform neighbor-average smoothing, shrinkage, boundaries, and
local/soft selection are lecture-core ideas. Taubin smoothing (Taubin, 1995)
and cotangent weighting (Desbrun et al., 1999 / Meyer et al., 2003) are
project extensions, implemented here in simplified teaching form.

## 1. Uniform Laplacian (neighbor-average) smoothing

For each movable vertex `v` with one-ring neighbors `N(v)`:

```
neighbor_average = mean(position of each neighbor)
v_new = v + lambda * (neighbor_average - v)
```

- `lambda` (0..1) controls how far the vertex moves each iteration; `lambda = 0`
  moves nothing (the app refuses to record it as work).
- Every neighbor has equal influence, so the result depends mainly on
  connectivity.
- **Shrinkage:** repeated averaging pulls vertices inward, so closed shapes
  usually get smaller. This is the classic problem the other methods address.

## 2. Taubin smoothing (lambda / mu)

Each iteration applies **two** uniform-Laplacian passes:

```
v = v + lambda * (neighbor_average - v)   # positive smoothing step
v = v + mu     * (neighbor_average - v)   # negative correction step, mu < 0
```

Recommended pair: `lambda = 0.5`, `mu = -0.53`.

- **What the app checks:** the per-iteration transfer function is
  `f(w) = (1 - lambda*w) * (1 - mu*w)` for sampled frequencies `w` in `(0, 2]`.
  The UI labels a pair unstable when the largest sampled `|f(w)|` exceeds
  `1.01`. This is a teaching guard, not a proof of stability for every mesh.
- **Pass-band is not enough:** `lambda < |mu|` gives the positive pass-band
  `1/lambda + 1/mu`, but does not by itself keep `|f(w)|` near 1 over the full
  sampled range. The recommended pair passes the app's check; other pairs can
  amplify frequencies, expand, or roughen the mesh.
- `lambda = 0` does not make Taubin a no-op when `mu` is nonzero: the negative
  pass still runs. The UI warns about an unstable active pair when iterations
  are requested.
- Because each iteration is two passes, comparing Taubin with Uniform at equal
  iteration counts is a same-input comparison, not an equal-work comparison.

## 3. Cotangent-weighted Laplacian smoothing

For a triangle edge `(i, j)`, the weight is:

```
w_ij = 0.5 * (cot(alpha) + cot(beta))
```

where `alpha` and `beta` are the angles opposite the edge in the two triangles
sharing it (one triangle for a boundary edge). Cotangents are computed robustly
as `cot(theta) = dot(a, b) / ||cross(a, b)||`.

The vertex update uses the normalized weighted average of neighbors:

```
target = sum_j (w_ij * position_j) / sum_j w_ij
v_new  = v + strength * (target - v)
```

**This is a simplified teaching smoother, not a full Laplace–Beltrami
discretization:**

- **Frozen weights:** the weight map is computed once from the *starting*
  geometry and reused for every iteration.
- **Clamping:** aggregate negative edge weights (from obtuse triangles) are
  clamped to zero so the weighted average stays inside the neighbor hull.
- **No mass matrix:** the update normalizes by the positive weight sum instead
  of using a vertex-area (dual-cell/barycentric) mass term.
- **Degeneracy guard:** near-degenerate triangles contribute zero weight, using
  an absolute tolerance (very small meshes may behave differently than scaled
  copies).
- **Triangulations only.** This implementation requires a triangle-only mesh;
  on other meshes the lab reports "unsupported" and leaves the geometry
  unchanged rather than producing wrong output. (Uploaded OBJ files may already
  be triangulated by the loader.)

## Synthetic noise (project extension)

Noise is not a smoothing method. It adds an independent Gaussian displacement
to every vertex while leaving faces and connectivity unchanged.

- The Gaussian standard deviation is `strength * median_edge_length` of the
  current mesh. Each displacement is capped at half that median edge length.
- **Along vertex normals** uses area-weighted vertex normals; vertices whose
  normal is degenerate fall back to a random 3D displacement.
- **Random 3D displacement** draws a three-component Gaussian offset and caps
  its vector length. A seed reproduces the same noise only for the same input
  geometry and noise mode.

## 4. Local / soft-selection smoothing

Uniform smoothing scaled by a soft-selection weight based on graph distance from
a chosen center vertex (1 graph step = crossing one edge):

```
v_new = v + strength * local_weight(v) * (neighbor_average - v)
```

- `local_weight` is 1 at the center and falls off (linear or smoothstep) to
  **exactly 0 at the selected radius**, so vertices on the radius ring are
  neither moved nor included in the orange nonzero-weight highlight.
- Because graph distances are integers, linear and smoothstep produce
  **identical weights at radius 1** (center 1, ring 0) **and radius 2** (center
  1, distance-1 ring 1/2, radius ring 0). They first diverge at radius 3, so the
  falloff choice matters only at radius 3 or more, and the app locks the
  selector below that.

## Boundary preservation

When enabled, vertices on boundary edges (edges belonging to exactly one face)
are held fixed for every method. The Step Inspector predicts the same rule when
its separate inspection checkbox is set to preserve boundaries.
This pins the open border of meshes such as the plane/grid. It does **not**
prevent the interior from moving or collapsing, and it does nothing on closed
meshes (which have no boundary edges).

## Metrics and their limits

- **Roughness (mean neighbor distance):** the mean of `||v - mean(N(v))||` over
  vertices with neighbors, in mesh length units. It is **scale-dependent**:
  uniformly scaling a mesh by 0.5 halves the value, so a collapsing mesh
  "improves" this number without becoming better-shaped. Always read it with
  the size metrics. A perfectly flat open grid still scores nonzero because of
  boundary/valence effects.
- **AABB diagonal change:** axis-aligned bounding-box diagonal; a size proxy,
  sensitive to orientation, not a full shape measure.
- **Surface area / volume:** computed by Trimesh over fan-triangulated
  polygons. Area is not a direct detail or size score. Volume is shown only
  when Trimesh reports a watertight, winding-consistent, nonzero-volume mesh;
  it is the magnitude of the aggregate signed volume. This gate does not
  validate outward orientation of each disconnected component, so opposing
  components can still cancel or understate the physical total.
- **Displacement:** per-vertex distance from the comparison baseline; requires
  identical vertex indexing.
