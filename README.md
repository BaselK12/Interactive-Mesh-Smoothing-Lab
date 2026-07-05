# Mesh Smoothing Lecture Lab

**A visual playground for learning mesh smoothing.**

## Project Purpose

Mesh Smoothing Lecture Lab is an interactive Streamlit app for one focused
computer graphics topic: **mesh smoothing**. The main learning loop is:

1. Change a control.
2. Watch the mesh preview update immediately.
3. Read the short explanation and quick metric cards.
4. Commit the preview only when you want it to become the current working mesh.

The app keeps the original clean mesh, committed working mesh, and temporary
preview mesh separate so students can experiment without accidentally overwriting
the current state.

## Learning Tabs

- **Playground**: the default visual learning area. It contains presets, live
  preview controls, the main overlay viewer, short explanations, and simple
  metric cards. Presets change control settings only; they keep the currently
  selected sample or uploaded mesh.
- **Method Comparison**: runs Uniform Laplacian, Taubin, and Cotangent-weighted
  smoothing on the same committed input mesh, shows visual result cards, and
  ranks the tradeoffs.
- **Step Inspector**: shows the one-vertex smoothing computation: neighbors,
  average or weights, displacement, predicted new position, and a vertex-level
  visual.
- **Advanced Metrics**: full observation tables, roughness details, smoothing
  history, charts, and the downloadable Markdown summary.

## Implemented Smoothing Concepts

- Polygonal mesh topology: vertices, edges, faces, and mesh type.
- Connectivity and one-ring neighbor queries.
- Face normals and vertex normals.
- Uniform Laplacian smoothing.
- Shrinkage from repeated averaging.
- Boundary preservation on open meshes.
- Local / soft-selection smoothing with graph-distance falloff.
- Taubin smoothing to reduce shrinkage.
- Cotangent-weighted Laplacian smoothing for triangle meshes.
- Roughness energy, shrinkage, surface area, displacement, and topology metrics.
- Controlled noisy-mesh experiments.
- Method comparison and per-vertex step inspection.

No subdivision, warping, export, advanced rendering, lecture transcription, or
new smoothing algorithms are included.

## How Live Preview Works

Live Preview is on by default in the Playground tab.

- Changing method, iterations, lambda, Taubin mu, noise strength, noise seed,
  boundary preservation, or local smoothing controls recomputes the preview mesh.
- The preview starts from the committed working mesh.
- The preview does not mutate the working mesh.
- **Commit preview as current mesh** intentionally promotes the preview to the
  working mesh and records a history row.
- **Reset experiment** restores the working mesh to the original clean mesh and
  clears preview/history state.

When Live Preview is off, the app keeps the older apply-button workflow: use
**Add noise to current mesh** and **Apply smoothing** to mutate the working mesh.

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

Streamlit opens the app in a browser. If it does not open automatically, use the
local URL printed in the terminal.

## Suggested 2-3 Minute Demo Flow

1. Open **Playground**.
2. Click the **Remove noise** preset.
3. Move lambda and iterations; point out that the preview updates live.
4. Keep the overlay view on and explain shrinkage using the original wireframe
   versus the shaded preview.
5. Click **Method Comparison**.
6. Run the comparison and show Uniform Laplacian versus Taubin shrinkage.
7. Open **Step Inspector**.
8. Show one vertex moving toward its neighbor average.

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a fuller script.

## Smoothing Methods

See [docs/METHODS.md](docs/METHODS.md) for more detail.

- **Uniform Laplacian**: each vertex moves toward the average of its one-ring
  neighbors. Simple and connectivity-driven, but it can shrink the mesh.
- **Taubin**: alternates a positive smoothing step with a negative correction
  step to reduce shrinkage.
- **Cotangent-weighted Laplacian**: weights neighbors using triangle geometry.
  It is available only for triangle-only meshes.
- **Local / soft smoothing**: scales uniform smoothing by graph distance from a
  chosen center vertex.

## Metrics

The Playground shows simple cards first:

- **Roughness change**: lower usually means vertices are closer to neighbor
  averages.
- **Shrinkage / bounding box change**: negative means the mesh got smaller.
- **Surface area change**: often drops as detail is smoothed away.
- **Average vertex movement**: how far vertices moved from the original clean
  mesh.
- **Topology changed?**: smoothing should move vertices without changing faces
  or edges.

The **Advanced Metrics** tab contains the full tables, roughness breakdown,
history chart, and Markdown summary download.

## Supported Mesh Sources

Built-in meshes:

- Cube
- Plane/grid
- Low-poly sphere
- Cylinder

OBJ upload is supported with a size limit and safe fallback. Invalid uploads
show an error and the app falls back to the default cube.

## Which Methods Support Which Mesh Types

| Mesh | Type | Uniform | Taubin | Cotangent |
| --- | --- | --- | --- | --- |
| Cube | quad | yes | yes | no |
| Plane/grid | quad | yes | yes | no |
| Low-poly sphere | triangle | yes | yes | yes |
| Cylinder | mixed | yes | yes | no |
| pyramid.obj | triangle | yes | yes | yes |

Cotangent smoothing requires a triangle-only mesh. Unsupported meshes show a
warning and do not produce fake cotangent output.

## Known Limitations

- Cotangent smoothing supports triangle meshes only; negative cotangent weights
  are clamped to zero for stability.
- Uploaded OBJ files may be triangulated by Trimesh during parsing.
- Volume is available only for closed, watertight meshes.
- Local soft regions use graph distance through connectivity, not Euclidean
  distance.
- Vertex selection uses numeric sliders; there is no direct mouse picking in
  the 3D viewer.
- The overlay view is a visual aid, not a signed-distance error field.
- Live preview has a large-mesh safety guard to keep the app responsive.
- Rendering is intentionally simple so the lesson stays focused on smoothing.
