# Student Guide

This guide lists the exercises available in the app's **Student Exercises**
section. Each one reinforces a single idea about mesh smoothing. Do them in
order for a guided path, or jump to the one that matches your question.

For each exercise: try it, then read the metrics and the before/after comparison
to confirm the expected observation.

## Exercise 1 - Topology stays fixed
- **Goal:** See that smoothing changes geometry but not connectivity.
- **Steps:** Load the cube. Apply uniform Laplacian smoothing for 5 iterations.
- **Expected:** Vertex, face, and edge counts stay the same while the shape
  changes.
- **Why:** Smoothing moves vertices but reuses the same faces and edges.

## Exercise 2 - Shrinkage
- **Goal:** Observe why uniform smoothing shrinks a mesh.
- **Steps:** Load the low-poly sphere. Apply 20 iterations of uniform Laplacian
  smoothing with lambda around 0.5.
- **Expected:** Bounding box diagonal and surface area decrease noticeably.
- **Why:** Repeated averaging pulls vertices inward, so closed shapes shrink.

## Exercise 3 - Boundary preservation
- **Goal:** See how open boundaries behave during smoothing.
- **Steps:** Load the plane/grid. Apply smoothing with boundary preservation
  off; reset; apply it on.
- **Expected:** The open border moves inward when preservation is off and stays
  fixed when on.
- **Why:** Boundary edges belong to one face; without care, open meshes collapse
  at the border.

## Exercise 4 - Noise removal
- **Goal:** Use smoothing to reduce roughness from noise.
- **Steps:** Load the low-poly sphere. Add noise (along vertex normals), then
  apply smoothing.
- **Expected:** Roughness energy decreases, but the shape may also shrink.
- **Why:** Smoothing removes high-frequency noise, showing the reduce-roughness
  vs preserve-shape tradeoff.

## Exercise 5 - Method comparison
- **Goal:** Compare how different methods handle the same noisy mesh.
- **Steps:** Load the low-poly sphere and add noise. Open Smoothing Method
  Comparison and run it.
- **Expected:** Uniform, Taubin, and cotangent smoothing show different
  shrinkage and roughness reduction.
- **Why:** There is no single best method; each trades roughness reduction
  against shape preservation.

## Exercise 6 - Local soft smoothing
- **Goal:** See how a soft-selection radius controls the affected region.
- **Steps:** Load the cube, choose Local / soft smoothing, pick a center vertex,
  try radius 1 then radius 3.
- **Expected:** The affected vertex count and the smoothed region grow with
  radius.
- **Why:** Soft selection localizes edits, like a soft brush on the surface.

## Exercise 7 - Step inspector
- **Goal:** Connect the smoothing formula to a single vertex.
- **Steps:** Open the Smoothing Step Inspector and pick a vertex. Note its
  neighbor average and predicted position, then apply smoothing and inspect
  again.
- **Expected:** The vertex moves toward the average of its neighbors, matching
  the prediction.
- **Why:** It makes the abstract update formula concrete and checkable.
