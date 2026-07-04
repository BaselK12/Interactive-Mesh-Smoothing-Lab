# Mesh Smoothing Lecture Lab

**A visual deep dive into mesh smoothing.**

## Project Purpose

Mesh Smoothing Lecture Lab is an interactive learning tool built around a single
topic: **mesh smoothing**. It lets students understand smoothing visually,
mathematically, and experimentally. Instead of covering many shallow topics, it
goes deep on one: what smoothing does, why it shrinks meshes, how different
smoothing methods compare, and how connectivity and boundaries affect the
result.

The app maps short explanations to live visual controls. Students can add noise
to a mesh, apply several smoothing methods, compare them on identical input,
inspect the per-vertex computation, and read metrics that quantify roughness and
shrinkage.

## Course / Lecture Connection

The lab supports the computer graphics mesh modeling lecture, focusing on the
smoothing portion: polygonal mesh topology, connectivity, normals,
neighbor-average (Laplacian) smoothing, shrinkage, boundary preservation,
soft-selection smoothing, and two more advanced methods (Taubin and
cotangent-weighted Laplacian). It also adds a roughness energy metric so the
"smoothness" of a mesh becomes a measurable number.

## What Problem the Lab Solves

Smoothing is easy to state ("move each vertex toward the average of its
neighbors") but its consequences are subtle:

- It reduces roughness but can shrink the whole mesh.
- Different methods trade roughness reduction against shape preservation.
- Connectivity and triangle shape change the result.
- Open boundaries need special handling.

The lab makes each of these observable with controlled experiments and metrics.

## Implemented Smoothing Concepts

- Polygonal mesh topology (vertices, edges, faces; triangle/quad/mixed).
- Mesh connectivity and one-ring neighbor queries.
- Face normals and vertex normals (average and area-weighted).
- Uniform Laplacian (neighbor-average) smoothing.
- Shrinkage from repeated averaging.
- Boundary preservation on open meshes.
- Local / soft-selection smoothing with graph-distance falloff.
- **Taubin smoothing** (lambda/mu) to reduce shrinkage.
- **Cotangent-weighted Laplacian smoothing** (geometry-aware, triangle meshes).
- **Roughness (smoothness) energy** metric.
- **Method comparison** on identical input.
- **Smoothing step inspector** for the per-vertex computation.
- **Noisy mesh experiment** (clean -> noisy -> smoothed).

## How to Run

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate with:

```bash
source .venv/bin/activate
```

Run the app:

```bash
python -m streamlit run app.py
```

Streamlit opens the app in a browser. If it does not open automatically, use the
local URL printed in the terminal.

## Suggested 2-3 Minute Demo Flow

1. Load the **Low-poly sphere** and note the mesh statistics and roughness
   energy.
2. In the sidebar **Noisy mesh experiment**, add noise along vertex normals
   (strength ~0.4, seed 42). Watch roughness energy jump.
3. Apply **Uniform Laplacian** smoothing (10+ iterations) and point out that
   roughness drops but the bounding box and surface area shrink a lot.
4. Reset to clean original, re-add the same noise, and apply **Taubin** — note
   that it reduces roughness with far less shrinkage.
5. Open **Smoothing Method Comparison** and run it: one table shows uniform vs
   Taubin vs cotangent on the same input, with ranking notes.
6. Open the **Smoothing Step Inspector**, pick a vertex, and show the neighbor
   average and predicted one-step position — the smoothing formula made visible.

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a fuller script.

## Student Exercises

The app's **Student Exercises** section (and [docs/STUDENT_GUIDE.md](docs/STUDENT_GUIDE.md))
includes short guided tasks:

1. Topology stays fixed during smoothing.
2. Shrinkage from repeated uniform smoothing.
3. Boundary preservation on the plane/grid.
4. Noise removal and the roughness/shrinkage tradeoff.
5. Method comparison on a noisy sphere.
6. Local soft smoothing with different radii.
7. Step inspector before and after smoothing.

Each exercise lists a goal, steps, the expected observation, and why it matters.

## Explanation of Each Smoothing Method

See [docs/METHODS.md](docs/METHODS.md) for detail. In short:

- **Uniform Laplacian**: each vertex moves toward the plain average of its
  one-ring neighbors. Simple and connectivity-driven, but shrinks meshes.
- **Taubin**: alternates a positive smoothing step (lambda) with a negative
  correction step (mu < 0). Smooths while preserving size much better.
- **Cotangent-weighted Laplacian**: weights each neighbor using triangle angles
  (cotangent weights), so it is geometry-aware. Defined for triangle meshes
  only; the lab clamps negative weights for stability.
- **Local / soft smoothing**: uniform smoothing scaled by a graph-distance
  falloff from a chosen center vertex, like a soft brush.

## Explanation of Metrics

- **Topology counts** (vertices, faces, edges): should stay constant; smoothing
  changes positions, not connectivity.
- **Average / max vertex displacement**: how far vertices moved from the
  original.
- **Bounding box diagonal, surface area, volume**: size measures; a decrease
  indicates shrinkage. Volume is available only for closed, watertight meshes.
- **Roughness energy**: the average distance from each vertex to the average of
  its neighbors (mean, max, and RMS). Lower usually means smoother geometry. A
  method can lower roughness while shrinking the mesh, so read it alongside the
  size metrics.

## Noisy Mesh Experiment

The sidebar controls add controlled, reproducible noise to the working mesh:

- **Noise strength** scales displacement relative to the median edge length, so
  noise stays proportional to mesh resolution and cannot explode the mesh.
- **Noise seed** makes the result reproducible; the same seed gives the same
  noise, a different seed gives different noise.
- **Noise mode**: along vertex normals (falling back to random 3D displacement
  for degenerate normals) or random 3D displacement.

Noise changes only the working mesh; the clean original is preserved and used in
the before/after comparison. Noise adds a clearly labeled step to the smoothing
history, and "Reset to clean original" restores the clean mesh.

## Which Methods Support Which Mesh Types

| Mesh          | Type     | Uniform | Taubin | Cotangent |
| ------------- | -------- | ------- | ------ | --------- |
| Cube          | quad     | yes     | yes    | no        |
| Plane/grid    | quad     | yes     | yes    | no        |
| Low-poly sphere | triangle | yes   | yes    | yes       |
| Cylinder      | mixed    | yes     | yes    | no        |
| pyramid.obj   | triangle | yes     | yes    | yes       |

Cotangent smoothing requires a triangle-only mesh. On other meshes it shows a
clear warning and leaves the mesh unchanged instead of producing wrong geometry.

## Known Limitations

- Cotangent smoothing supports triangle meshes only; negative cotangent weights
  (from obtuse triangles) are clamped to zero for stability, which is a
  simplification of the exact operator.
- Uploaded OBJ files may be triangulated by Trimesh during parsing.
- Volume is available only for closed, watertight meshes.
- Local soft regions use graph distance through connectivity, not Euclidean
  distance.
- Vertex selection (soft center and inspector) uses numeric sliders; there is no
  direct mouse picking in the 3D viewer.
- The overlay view is a visual aid, not a signed-distance error field.
- Rendering is intentionally simple so the lesson stays focused on smoothing.

## Future Work (focused only on this lab)

- Lecture notes integration refinement.
- Optional direct vertex picking in the 3D viewer.
- More mesh examples.
- Additional smoothing methods, clearly labeled as future research (e.g.
  bilateral or implicit/backward-Euler smoothing).
