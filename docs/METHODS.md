# Smoothing Methods

This lab implements four smoothing behaviors. All of them reuse the mesh
connectivity unchanged, so vertex/face/edge counts never change — only vertex
positions move. All methods use **synchronous updates**: within one iteration,
every vertex reads its neighbors' *old* positions.

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

Recommended stable pair: `lambda = 0.5`, `mu = -0.53`.

- **Stability condition:** the per-iteration transfer function is
  `f(w) = (1 - lambda*w) * (1 - mu*w)` for frequencies `w` in `(0, 2]`. Suitable
  pairs keep `lambda < |mu|` with a small positive pass-band
  `1/lambda + 1/mu`; then `|f(w)|` stays at or below ~1 and the mesh smooths
  with little size change.
- **Unsuitable pairs amplify.** For example `lambda = 0.35, mu = -0.53` gains
  about 3.3% per iteration at mid frequencies and makes the noisy demo sphere
  *rougher and larger*; `lambda = 0.05, mu = -0.95` explodes. The app computes
  this gain and warns before you rely on the result.
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

## 4. Local / soft-selection smoothing

Uniform smoothing scaled by a soft-selection weight based on graph distance from
a chosen center vertex (1 graph step = crossing one edge):

```
v_new = v + strength * local_weight(v) * (neighbor_average - v)
```

- `local_weight` is 1 at the center and falls off (linear or smoothstep) to
  **exactly 0 at the selected radius**, so vertices on the radius ring are
  highlighted as the region border but do not move.
- Because graph distances are integers, linear and smoothstep produce
  **identical weights at radius 1 and 2** (both give 1, 1/2, 0). The falloff
  choice matters only at radius 3 or more, and the app locks the selector below
  that.

## Boundary preservation

When enabled, vertices on boundary edges (edges belonging to exactly one face)
are held fixed for every method, including the Step Inspector's prediction.
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
  polygons. Volume is reported only for closed meshes with consistent outward
  winding; watertightness alone is not enough (oppositely oriented components
  cancel, a flipped face inflates the signed sum).
- **Displacement:** per-vertex distance from the comparison baseline; requires
  identical vertex indexing.
