# Mesh Smoothing Lecture Lab

**A visual playground for learning mesh smoothing.**

## Project Purpose

Mesh Smoothing Lecture Lab is an interactive Streamlit app for one focused
computer graphics topic: **mesh smoothing**. The main learning loop is:

1. Change a control.
2. Watch the mesh preview update immediately.
3. Read the metric strip and look-for hint under the viewer, and the short
   explanation beside it.
4. Commit the preview only when you want it to become the current working mesh.

The app keeps four named mesh states separate so experiments cannot silently
overwrite each other:

- **Source original** — the untouched mesh from the sidebar source.
- **Committed working mesh** — the result of committed actions; what Method
  Comparison, the Step Inspector, and Advanced Metrics read.
- **Noisy preview stage** — when the live preview includes noise, the noisy
  mesh *before* smoothing (usable as a comparison input).
- **Live preview** — the temporary result of the current controls.

## Learning Sections

Navigation renders one section at a time (heavy 3D viewers are not rebuilt for
hidden sections):

- **Playground**: the default visual learning area — presets, live preview
  controls, the main viewer with a sticky metric strip, short explanations, and
  metric cards. The app opens on the clean original mesh with zero smoothing
  iterations; the recommended first experiment is the **See shrinkage** preset.
- **Method Comparison**: runs Uniform Laplacian, Taubin, and Cotangent-weighted
  smoothing on one explicitly chosen input baseline (committed mesh, source
  original, noisy preview stage, or live preview), shows visual result cards,
  and reports literal metric observations. Stored results are flagged as stale
  when their input has changed since the run.
- **Step Inspector**: the one-vertex smoothing computation — neighbors,
  average or cotangent weights, displacement, predicted position — honoring the
  boundary-preservation rule the smoother actually applies.
- **Guided Learning**: a how-to-use path, an eight-step walkthrough, and a key
  terms reference.
- **Student Exercises**: seven short exercises with exact control names and
  expected observations.
- **Advanced Metrics**: full observation tables, the roughness breakdown,
  committed action history, and the Markdown summary download (generated from
  the committed history, never from uncommitted widget positions).

## Implemented Smoothing Concepts

Lecture core: polygonal mesh anatomy, connectivity and one-ring neighbors, face
and vertex normals, uniform Laplacian smoothing, shrinkage, boundary
preservation, and local/soft-selection smoothing.

Project extensions: Taubin smoothing (with a stability check on lambda/mu
pairs), simplified cotangent-weighted smoothing for triangle meshes, controlled
noise experiments, method comparison, and the numeric metrics.

No subdivision, warping, export, advanced rendering, lecture transcription, or
new smoothing algorithms are included.

## How Live Preview Works

Live Preview is on by default in the Playground.

- On first load, noise is off and smoothing iterations are 0, so the viewer
  shows the clean original.
- Changing method, iterations, lambda, Taubin mu, noise controls, boundary
  preservation, or local smoothing controls recomputes the preview from the
  committed working mesh without mutating it.
- A stage flag counts as "changed" only when vertices actually moved — zero
  lambda or zero-strength noise cannot be committed or recorded as work.
- **Commit preview as current mesh** promotes the preview to the working mesh,
  records exactly what happened in the history, and resets the one-shot noise
  and iteration controls to neutral, so the viewer then shows precisely the
  committed state (the same operation is not immediately re-applied).
- **Reset experiment** restores the clean original and neutral controls.

When Live Preview is off, **Add noise to current mesh** and **Apply smoothing**
mutate the working mesh directly. Both buttons are disabled (with an
explanation) when their settings would do nothing.

## How to Run

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Run the app:

```bash
python -m streamlit run app.py
```

Run the test suite:

```bash
python -m pytest tests
```

## Suggested 2-3 Minute Demo Flow

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for the full script.

1. **Playground** → **See shrinkage** preset → read the Overlay and metric strip.
2. **Reset experiment** → **Remove noise** preset → read the
   start → noisy → smoothed roughness line.
3. **Uniform vs Taubin** preset → **Method Comparison** → run from the noisy
   preview stage.
4. **Boundary preservation** preset → toggle the boundary checkbox.
5. **Step Inspector** → corner vertex (pinned) vs interior vertex.

## Smoothing Methods

See [docs/METHODS.md](docs/METHODS.md) for formulas, stability conditions, and
the documented simplifications.

- **Uniform Laplacian**: each vertex moves toward the average of its one-ring
  neighbors. Simple and connectivity-driven; usually shrinks closed meshes.
- **Taubin**: alternates a positive step (lambda) with a negative correction
  (mu). It reduces shrinkage **for suitable pairs** (lambda < |mu|, e.g.
  0.5 / −0.53); unsuitable pairs amplify mid frequencies and can expand the
  mesh, and the app warns when the current pair is unstable.
- **Cotangent-weighted Laplacian**: weights neighbors using triangle geometry.
  Triangle-only; this implementation freezes the weights at the starting
  geometry, clamps negative weights, and omits the mass term (a documented
  teaching simplification).
- **Local / soft smoothing**: scales uniform smoothing by graph distance from a
  chosen center vertex; the falloff choice matters only at radius 3+.

## Metrics

The sticky strip under the viewer shows the three key numbers (roughness
change, AABB diagonal change, average vertex movement) with the baseline named
in each tooltip. Details:

- **Roughness (mean neighbor distance)**: the average distance from each vertex
  to the mean of its neighbors, in mesh length units. **Scale-dependent** —
  uniformly shrinking a mesh also lowers it, so always read it together with
  the size metrics.
- **AABB diagonal change**: axis-aligned bounding-box diagonal versus the
  source original; a size proxy, not a full shape measure.
- **Surface area change**: can rise or fall for many reasons; not a direct
  "detail removed" score.
- **Average vertex movement**: mean per-vertex distance from the source
  original.
- **Topology counts changed?**: vertex/face/edge counts only.
- **Boundary moved?**: appears on open meshes; compares boundary movement to
  interior movement.
- **Volume**: reported only for closed meshes with consistent outward winding;
  watertightness alone is not sufficient.

## Supported Mesh Sources

Built-in meshes: Cube, Plane/grid, Low-poly sphere, Cylinder.

OBJ upload is supported with a size limit and safe fallback. Invalid uploads
show an error and the app falls back to the default cube. Switching the mesh
source resets the experiment controls to neutral (presets carry their own
settings).

## Which Methods Support Which Mesh Types

| Mesh | Type | Uniform | Taubin | Cotangent |
| --- | --- | --- | --- | --- |
| Cube | quad | yes | yes | no |
| Plane/grid | quad | yes | yes | no |
| Low-poly sphere | triangle | yes | yes | yes |
| Cylinder | mixed | yes | yes | no |
| pyramid.obj | triangle (after load) | yes | yes | yes |

Cotangent smoothing requires a triangle-only mesh. Unsupported meshes show a
warning and do not produce fake cotangent output. Note that Trimesh may
triangulate uploaded OBJ files during parsing (pyramid.obj is authored with a
quad base but loads as six triangles).

## Known Limitations

- The cotangent implementation is a simplified teaching smoother (frozen
  weights, clamped negatives, no mass matrix).
- Taubin lambda/mu sliders allow unstable pairs by design (for exploration);
  the app warns and flags preview expansion instead of blocking them.
- Volume requires a closed, consistently outward-wound mesh.
- Local soft regions use graph distance through connectivity, not Euclidean
  distance; the radius ring itself has zero weight.
- Vertex selection uses numeric sliders; there is no mouse picking in the 3D
  viewer.
- Side-by-side renders both meshes in one shared scene so scale is honest;
  Overlay remains the clearest before/after mode.
- Live preview has a large-mesh safety guard to keep the app responsive.
- Rendering is intentionally simple so the lesson stays focused on smoothing.
