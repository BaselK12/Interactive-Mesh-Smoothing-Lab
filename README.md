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
- Shape shrinkage after repeated smoothing.
- Boundary preservation on open meshes such as the plane/grid.
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
- Boundary vertex preservation.
- Guided lecture walkthrough.
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
7. Watch the observation metrics and history table update.
8. Compare boundary preservation on and off for the plane/grid.
9. Reset and try another mesh.

## Current Limitations

- The lab covers neighbor-average smoothing only.
- Uploaded OBJ files may be triangulated by Trimesh during parsing.
- There is no side-by-side before/after view yet.
- Volume is available only for closed, watertight meshes.
- Smoothing is applied globally to all movable vertices.
- Rendering is intentionally simple so the lesson stays focused on smoothing.

## Future Work Focused Only on This Lab

- Clearer side-by-side before/after comparison.
- Local or soft smoothing connected to soft selection.
- Integrating scribe notes from the lecture.
