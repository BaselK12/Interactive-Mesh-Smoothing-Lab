# Mesh Smoothing Lecture Lab

## Project Purpose

Mesh Smoothing Lecture Lab is an interactive visual lecture companion for a
computer graphics mesh modeling lecture. It focuses on neighbor-based mesh
smoothing and shrinkage.

The app maps short explanations to live visual controls. Students can change a
mesh, apply smoothing, and immediately compare the original shape with the
current smoothed result.

## Course/Lecture Connection

The lab supports the mesh modeling lecture topic of neighbor-based smoothing.
It shows how polygonal meshes store vertices, edges, and faces, how mesh
connectivity provides neighboring vertices, and how repeated averaging changes
surface shape.

## Guided Lecture Walkthrough

The app includes a step-based walkthrough:

1. Polygonal Mesh: connect solid, wireframe, and points modes to faces, edges,
   and vertices.
2. Mesh Connectivity: inspect statistics and wireframe structure to see why
   neighbor queries matter.
3. Normals: compare face normals and vertex normals as surface orientation
   cues.
4. Neighbor-Average Smoothing: apply one smoothing step and observe sharp
   regions relax.
5. Repeated Smoothing and Shrinkage: apply many iterations and watch size
   metrics decrease.
6. Boundary Preservation: compare the plane/grid with boundary preservation on
   and off.

Each step has a short explanation, a student action, and what to observe.

## Smoothing Observation Metrics

The metrics panel compares the original mesh with the current working mesh:

- Vertex count.
- Face count.
- Unique edge count.
- Smoothing iterations applied.
- Average vertex displacement from the original.
- Max vertex displacement from the original.
- Bounding box diagonal for original and current mesh, plus percent change.
- Surface area for original and current mesh, plus percent change.
- Volume for original and current mesh, plus percent change when available.

Displacement is shown as N/A if the original and current meshes do not have the
same vertex count. Volume is shown as N/A for open or non-watertight meshes.

## Before / After Comparison

The comparison view shows the unchanged original mesh and the current working
mesh after smoothing. This gives students a direct visual way to inspect
shrinkage and boundary behavior.

The app supports:

- Side-by-side comparison with original mesh on the left and current mesh on
  the right.
- Overlay comparison with the original mesh as wireframe and the current mesh
  as shaded geometry.
- Original-only and current-only views for focused inspection.

The original mesh is replaced only when the user switches source or uploads a
new valid OBJ. Smoothing changes only the current working mesh.

## Local / Soft Smoothing

Local / soft smoothing connects the smoothing experiment to the lecture idea of
soft selection. Instead of smoothing every movable vertex equally, the app lets
students choose a center vertex and apply smoothing with a graph-distance
falloff around that center.

The center vertex receives the strongest smoothing weight. Vertices farther
away through mesh connectivity receive smaller weights, and vertices outside
the radius are unchanged. Boundary preservation still keeps boundary vertices
fixed when enabled.

To try it:

1. Choose a mesh.
2. Set Smoothing mode to Local / soft smoothing.
3. Choose a center vertex index.
4. Set the soft selection radius in graph steps.
5. Choose linear or smoothstep falloff.
6. Apply one or more iterations.
7. Compare before/after views, metrics, and smoothing history.

## Lecture Notes Companion

The Lecture Notes Companion maps lecture concepts to interactive visual
experiments in the app. Each entry includes:

- Lecture idea.
- Where to try it in the app.
- What students should observe.

The mapping covers polygonal meshes, mesh data and connectivity, face normals,
vertex normals, neighbor-average smoothing, repeated smoothing and shrinkage,
local/soft smoothing, and boundary preservation.

The app also includes a lightweight Scribe Notes Placeholder. A future version
can add notes transcribed from the lecture recording and link each paragraph to
the matching visual experiment.

## What Shrinkage Metrics Mean

Neighbor-average smoothing repeatedly moves each vertex toward its connected
neighbors. This relaxes sharp details, but it can also pull the mesh inward.

The bounding box diagonal shows whether the overall extent is changing. Surface
area shows whether the visible surface is shrinking. Volume, when available,
shows whether a closed mesh encloses less space after smoothing.

Topology counts should usually stay the same because smoothing changes vertex
positions without changing faces or edges.

## What Students Can Explore

- Vertices, edges, and faces in triangle, quad, and mixed polygon meshes.
- Solid, wireframe, points, and wireframe plus shaded views.
- Face normals and vertex normals.
- Average and area-weighted vertex normal visualization.
- Neighbor-average smoothing with adjustable iteration count.
- Smoothing strength, also called lambda in the lecture formula.
- Local / soft smoothing with graph-distance falloff from a chosen center
  vertex.
- Shape shrinkage after repeated smoothing.
- Boundary preservation on open meshes such as the plane/grid.
- Before/after visual comparison between original and current mesh.
- Lecture concept mappings tied to app actions and observations.
- Smoothing history over repeated actions.
- Reset behavior for returning to the original mesh.

## Implemented Features

- Streamlit app with a PyVista-based 3D viewer.
- Built-in sample meshes: cube, plane/grid, low-poly sphere, and cylinder.
- OBJ upload with safe fallback for missing, invalid, empty, or unsupported
  files.
- Mesh statistics for vertices, faces, unique edges, and mesh type.
- Display modes for shaded mesh, wireframe, points, and shaded wireframe.
- Face normal and vertex normal overlays.
- Normal length control.
- Vertex normal weighting control.
- Neighbor-average smoothing.
- Local / soft smoothing connected to soft selection.
- Boundary vertex preservation.
- Guided lecture walkthrough.
- Before/after comparison with side-by-side and overlay modes.
- Lecture Notes Companion with concept-to-control mappings.
- Scribe Notes Placeholder for future lecture transcript integration.
- Original/current smoothing observation metrics.
- Smoothing history table and change chart.
- Reset to the original loaded or generated mesh.

## How to Run

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Run the app:

```bash
python -m streamlit run app.py
```

If the normal Streamlit launcher is blocked on Windows, use the same module
command above instead of `streamlit run app.py`.

Streamlit opens the app in a browser. If it does not open automatically, use
the local URL printed in the terminal.

## Suggested Learning Flow

1. Choose a built-in mesh.
2. Follow the Guided Lecture Walkthrough tabs.
3. Switch between solid, wireframe, and points to identify vertices, edges, and
   faces.
4. Toggle face normals and vertex normals.
5. Apply one smoothing iteration.
6. Apply many smoothing iterations.
7. Try Local / soft smoothing with a center vertex and graph radius.
8. Use the Before / After Comparison section to inspect visual change.
9. Read the Lecture Notes Companion entries for the matching lecture idea.
10. Watch the observation metrics and history table update.
11. Compare boundary preservation on and off for the plane/grid.
12. Reset and try another mesh.

## Suggested 2-3 Minute Demo Flow

1. Open with the cube or low-poly sphere and point out the mesh statistics:
   vertices, faces, edges, and mesh type.
2. Switch display modes between solid, wireframe, points, and shaded wireframe
   to connect the viewer to polygonal mesh structure.
3. Toggle face normals and vertex normals briefly to show orientation cues from
   the lecture.
4. Apply one global smoothing iteration with moderate strength and explain that
   each vertex moves toward the average of its neighbors.
5. Apply several more iterations and use the metrics plus history chart to show
   average displacement, bounding-box shrinkage, and surface-area change.
6. Open Before / After Comparison, then switch between side-by-side and overlay
   to show that the original mesh is preserved while the current mesh changes.
7. Switch to the plane/grid and compare smoothing with boundary preservation on
   and off to show why open mesh boundaries need special handling.
8. Switch to Local / soft smoothing, choose a center vertex and graph radius,
   and apply smoothing to show a localized effect with distance falloff.
9. Reset the mesh and state the main takeaway: the lab turns lecture concepts
   about connectivity, normals, smoothing, shrinkage, boundaries, and soft
   selection into live experiments.

## Current Limitations

- The lab covers neighbor-average smoothing only.
- Uploaded OBJ files may be triangulated by Trimesh during parsing.
- Volume is available only for closed, watertight meshes.
- Local soft regions use graph distance through mesh connectivity, not direct
  Euclidean distance.
- Vertex picking is through a numeric center vertex slider; there is no direct
  mouse picking in the 3D viewer.
- The overlay view is a visual aid, not a signed distance or geometric error
  field.
- Rendering is intentionally simple so the lesson stays focused on smoothing.

## Future Work Focused Only on This Lab

- Lecture notes integration refinement.
- Optional direct vertex picking in the 3D viewer.
