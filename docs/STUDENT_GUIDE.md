# Student Guide

This guide mirrors the exercises in the app's **Student Exercises** section.
Each one reinforces a single idea about mesh smoothing. Do them in order for a
guided path, or jump to the one that matches your question.

The app uses a **live preview** workflow: moving a control updates a temporary
preview immediately; **Commit preview as current mesh** makes it the committed
working mesh (what Method Comparison and the Step Inspector read); **Reset
experiment** returns to the clean original at any time.

## Exercise 1 - Topology counts stay fixed
- **Goal:** See that smoothing changes geometry but not connectivity.
- **Steps:** Load Cube (sidebar). Set method Uniform Laplacian, iterations 5,
  then click **Commit preview as current mesh**.
- **Expected:** Vertex, face, and edge counts stay the same while the shape
  changes ("Topology counts changed?" stays No).
- **Why:** Smoothing moves vertices but reuses the same faces and edges.

## Exercise 2 - Shrinkage
- **Goal:** Observe why uniform smoothing shrinks a closed mesh.
- **Steps:** Click the **See shrinkage** preset (Low-poly sphere, 14 iterations,
  lambda 0.5).
- **Expected:** In the Overlay the blue preview sits well inside the black
  original wireframe; the AABB diagonal change in the metric strip is strongly
  negative.
- **Why:** Repeated averaging pulls vertices inward. Note that the roughness
  metric also falls partly *because* the mesh got smaller — the metric has
  length units.

## Exercise 3 - Boundary preservation
- **Goal:** See how open boundaries behave during smoothing.
- **Steps:** Click the **Boundary preservation** preset, then toggle
  **Preserve boundary vertices** off and on.
- **Expected:** The border moves inward when preservation is off and stays
  pinned when it is on (watch the "Boundary moved?" card).
- **Why:** Boundary edges belong to one face; pinning the border keeps open
  meshes from sliding inward at the edge. It does not freeze the interior.

## Exercise 4 - Noise removal
- **Goal:** Use smoothing to reduce roughness from noise.
- **Steps:** Click the **Remove noise** preset, then read the
  *start -> noisy -> smoothed* roughness line in the explanation panel.
- **Expected:** The smoothed roughness is well below the noisy stage and close
  to the clean value while the size changes only a few percent. Then set lambda
  to 0.2: the app warns that the Taubin pair became unstable.
- **Why:** Denoising trades roughness reduction against shape preservation, and
  Taubin only limits shrinkage for suitable lambda/mu pairs (lambda < |mu|).

## Exercise 5 - Method comparison
- **Goal:** Compare methods on the *same* noisy input.
- **Steps:** Click **Uniform vs Taubin**, open **Method Comparison**, confirm
  the comparison input says **Noisy preview stage (before smoothing)**, and
  click **Run comparison from the selected input**.
- **Expected:** All methods start from the same seed-42 noisy sphere. Uniform
  shrinks more; Taubin keeps size better at the shown settings.
- **Why:** A fair comparison needs one shared input. Even then, equal iteration
  counts are not equal work (Taubin does two passes per iteration), and the
  observations describe this input only, not methods in general.

## Exercise 6 - Local soft smoothing
- **Goal:** See how a soft-selection radius controls the affected region.
- **Steps:** Click **Local soft smoothing**. Try radius 1, then radius 3; at
  radius 3 switch the falloff between linear and smoothstep.
- **Expected:** The orange highlighted region and the ring-weight table grow
  with radius; the falloff choice changes the middle-ring weights only at
  radius 3+ (at radius 1-2 both curves are identical, so the control is locked
  there).
- **Why:** Soft selection localizes edits through graph distance (1 step =
  crossing one edge). Vertices exactly at the radius always have weight 0.

## Exercise 7 - Step inspector
- **Goal:** Connect the smoothing formula — including the boundary rule — to a
  single vertex.
- **Steps:** Open **Step Inspector** on Plane/grid. Inspect vertex 0 (a
  corner), then an interior vertex such as 12.
- **Expected:** Vertex 0 is reported as a pinned boundary vertex with zero
  predicted movement; the interior vertex moves toward its neighbor average as
  the formula predicts.
- **Why:** The inspector shows the real update rule the smoother applies,
  including boundary pinning and the synchronous (all-at-once) update.
