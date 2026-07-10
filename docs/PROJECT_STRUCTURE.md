# Project Structure

Architecture and file responsibilities for **Mesh Smoothing Lecture Lab**. For
the user-facing overview see [../README.md](../README.md); for the smoothing math
see [METHODS.md](METHODS.md).

## Layout

```
app.py                 UI entry point (Streamlit)
requirements.txt       Runtime dependencies
src/                   Pure-Python mesh library (no Streamlit imports)
examples/              Sample OBJ meshes for upload
tests/                 Automated test suite (pytest)
docs/                  Documentation + README screenshots
assets/                Placeholder for runtime assets
```

The design separates a **pure mesh library** (`src/`) from the **UI** (`app.py`).
Everything in `src/` is framework-agnostic and unit-testable without a browser;
`app.py` handles layout, widgets, session state, and rendering.

## `app.py` — application and UI

The single Streamlit script. Responsibilities:

- **Layout & sections** — a radio selector renders exactly one section per run
  (Playground, Method Comparison, Step Inspector, Guided Learning, Student
  Exercises, Advanced Metrics), so hidden 3D viewers are not rebuilt.
- **State model** — `session_state` holds the four named meshes (source original,
  committed working, noisy preview stage, live preview) plus control values.
- **Live preview** — recomputes a preview from the committed mesh on each change
  without mutating it; commit/reset callbacks run before widgets instantiate.
- **Viewer** — calls into `src/visualization.py` and embeds the result via
  `st.iframe`.
- **Presets** — one-click, validated control setups.
- **Explanations & metrics** — the "What you are seeing" panel, the sticky metric
  strip, metric cards, comparison tables, and the downloadable Markdown summary.

## `src/` — mesh library

### `mesh_core.py`
The `MeshData` model (vertices, faces, name, source, validity) and derived
properties (counts, unique edges, mesh type). OBJ loading via Trimesh
(`load_obj_mesh`) with safe fallback, plus edge/topology helpers used across the
library.

### `sample_meshes.py`
Factory functions for the built-in meshes: `create_cube`, `create_plane_grid`,
`create_low_poly_sphere`, `create_cylinder`, and the `create_sample_mesh`
dispatcher used by the sidebar.

### `mesh_ops.py`
The heart of the lab. Contains:

- **Normals** — `compute_face_normals`, `compute_vertex_normals` (average /
  area-weighted).
- **Adjacency** — one-ring neighbor lists and boundary-vertex detection.
- **Smoothing** — `laplacian_smooth` (Uniform), `taubin_smooth` +
  `taubin_stability`, `cotangent_smooth` (+ `cotangent_weight_map`),
  `laplacian_smooth_local`, and the `apply_global_smoothing` dispatcher that
  returns a `SmoothingResult` with a `supported` flag.
- **Noise** — `add_noise` (reproducible, capped, normal/random modes).
- **Roughness** — `compute_roughness_energy` (mean/max/RMS neighbor distance).
- **Soft selection** — graph distances and falloff weights for local smoothing.
- **Inspectors** — `inspect_uniform_step`, `inspect_cotangent_step`,
  `inspect_local_step` for the Step Inspector.

### `mesh_metrics.py`
Geometry metrics kept separate from rendering: bounding-box diagonal, surface
area, gated volume, per-vertex displacement, and `percent_change`. Uses Trimesh
for area/volume with explicit validity gating.

### `visualization.py`
PyVista scene construction (solid/wireframe/points, normals, axes,
overlay/side-by-side) and `plotter_to_html`, which exports a plotter to a
self-contained HTML/VTK.js scene via Panel for iframe embedding.

## `tests/`

- `test_mesh_ops.py` — algorithm correctness (Uniform formula, boundary pinning,
  noise determinism, Taubin stability, cotangent support, falloff weights,
  roughness scale-dependence).
- `test_presets_and_metrics.py` — preset behavior and metric gating.
- `test_app_state.py` — Streamlit `AppTest` state transitions (reset, commit,
  comparison, summary, source switching).
- `test_release_qa.py` — end-to-end control/behavior regressions.

Run with `python -m pytest` from the repository root.

## Data flow (one interaction)

```
sidebar/preset  ──▶  session_state (controls)
                        │
                        ▼
        _sync_working_mesh / _build_preview_mesh   (uses src/mesh_ops.py)
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
   src/visualization.py         src/mesh_metrics.py
   (PyVista → Panel HTML)       (size / displacement)
          │                           │
          ▼                           ▼
     st.iframe viewer          metric strip / cards / tables
```
