"""Streamlit entry point for the Mesh Smoothing Lecture Lab."""

from __future__ import annotations

import hashlib

import numpy as np
import streamlit as st

from src.mesh_core import MeshData
from src.mesh_metrics import compare_meshes
from src.mesh_ops import (
    affected_soft_selection_vertices,
    clone_mesh,
    find_boundary_vertices,
    graph_distances_from_vertex,
    laplacian_smooth,
    laplacian_smooth_local,
)
from src.sample_meshes import create_sample_mesh, sample_mesh_names
from src.visualization import (
    DISPLAY_MODES,
    make_overlay_plotter,
    make_plotter,
    plotter_to_html,
)


MESH_SOURCE_KEY = "mesh_source_key"
ORIGINAL_MESH_KEY = "original_mesh"
WORKING_MESH_KEY = "working_mesh"
SMOOTHING_STEPS_KEY = "smoothing_steps"
SMOOTHING_HISTORY_KEY = "smoothing_history"
LOCAL_CENTER_KEY = "local_center_vertex"
LOCAL_RADIUS_KEY = "local_soft_radius"
COMPARISON_MODES = ["Side-by-side", "Overlay", "Original only", "Current only"]
SMOOTHING_MODES = ["Global smoothing", "Local / soft smoothing"]
FALLOFF_TYPES = ["linear", "smoothstep"]


def _load_uploaded_mesh(file_bytes: bytes, file_name: str) -> MeshData:
    """Load an uploaded OBJ file into the shared mesh wrapper."""
    from src.mesh_core import load_obj_mesh

    return load_obj_mesh(file_bytes, file_name)


def _render_statistics(mesh: MeshData) -> None:
    """Render basic mesh statistics in the sidebar."""
    stats = mesh.statistics()
    st.caption(f"Current mesh: {mesh.name}")
    st.metric("Vertices", stats["vertices"])
    st.metric("Faces", stats["faces"])
    st.metric("Unique edges", stats["unique_edges"])
    st.write(f"Mesh type: **{stats['mesh_type']}**")
    st.write(f"Source: `{mesh.source}`")


def _render_lab_intro() -> None:
    """Render the landing explanation for the lecture lab."""
    st.markdown(
        """
        An interactive visual lecture companion for the mesh modeling lecture.
        Use the controls beside the viewer to connect each explanation to a
        visible mesh result.

        This lab demonstrates neighbor-based mesh smoothing:

        - A polygonal mesh is made of vertices, edges, and faces.
        - Mesh data structures let us query neighboring vertices.
        - Face normals and vertex normals help visualize surface orientation.
        - Smoothing moves each vertex toward the average of its neighboring vertices.
        - Repeated smoothing can cause shrinkage.
        - Boundary preservation changes what happens on open meshes.
        """
    )


def _render_guided_walkthrough() -> None:
    """Render the step-based guided lecture walkthrough."""
    st.subheader("Guided Lecture Walkthrough")
    tabs = st.tabs(
        [
            "1. Polygonal Mesh",
            "2. Connectivity",
            "3. Normals",
            "4. Smoothing",
            "5. Shrinkage",
            "6. Boundaries",
        ]
    )

    steps = [
        (
            tabs[0],
            [
                "A mesh is made of vertices, edges, and faces.",
                "The viewer can show solid, wireframe, and points modes.",
            ],
            ["Switch between display modes."],
            [
                "Points show vertices.",
                "Wireframe shows edges.",
                "Solid view shows faces and surface shape.",
            ],
        ),
        (
            tabs[1],
            [
                "Smoothing needs neighboring vertices.",
                "A vertex changes based on the vertices connected to it.",
            ],
            ["Look at mesh statistics and wireframe."],
            ["Different meshes have different connectivity."],
        ),
        (
            tabs[2],
            [
                "Face normals describe face orientation.",
                "Vertex normals are estimated from incident faces.",
            ],
            ["Toggle face normals and vertex normals."],
            [
                "Cube face normals are faceted.",
                "Vertex normals approximate smoother orientation.",
            ],
        ),
        (
            tabs[3],
            [
                "Each vertex moves toward the average position of its neighbors.",
                "Lambda controls how far it moves.",
            ],
            ["Apply one smoothing iteration."],
            ["Pointy or sharp regions relax."],
        ),
        (
            tabs[4],
            ["Repeated averaging smooths the mesh but can pull it inward."],
            ["Apply many iterations."],
            ["Surface area, bounding box size, or volume may decrease."],
        ),
        (
            tabs[5],
            [
                "Boundary edges belong to only one face.",
                "Preserving boundary vertices keeps borders fixed on open meshes.",
            ],
            [
                "Use the plane/grid mesh.",
                "Compare smoothing with boundary preservation on and off.",
            ],
            [
                "Without preservation, the border can move inward.",
                "With preservation, the border remains fixed.",
            ],
        ),
    ]

    for tab, explanation, action, observe in steps:
        with tab:
            _render_walkthrough_step(explanation, action, observe)


def _render_walkthrough_step(
    explanation: list[str],
    action: list[str],
    observe: list[str],
) -> None:
    """Render one concise walkthrough step."""
    st.markdown("**Short explanation**")
    st.markdown(_bullets(explanation))
    st.markdown("**Student action**")
    st.markdown(_bullets(action))
    st.markdown("**What to observe**")
    st.markdown(_bullets(observe))


def _render_how_to_use_lab() -> None:
    """Render the suggested student workflow."""
    st.subheader("How to use this lab")
    st.markdown(
        """
        1. Choose a built-in mesh.
        2. Switch between solid, wireframe, and points to identify vertices, edges, and faces.
        3. Toggle face normals and vertex normals.
        4. Apply one smoothing iteration.
        5. Apply many smoothing iterations.
        6. Switch to local / soft smoothing and choose a center vertex.
        7. Use the before/after comparison to inspect shrinkage.
        8. Compare boundary preservation on/off for the plane/grid.
        9. Reset and try another mesh.
        """
    )


def _render_lecture_notes_companion() -> None:
    """Render lecture concept notes mapped to app actions."""
    st.subheader("Lecture Notes Companion")
    st.markdown(
        """
        These notes connect lecture ideas to the visual experiments in the app.
        Each entry points to a control, an action, and the observation to make.
        """
    )

    concepts = [
        {
            "title": "Polygonal Mesh",
            "lecture_idea": [
                "A polygonal mesh is made of vertices, edges, and faces.",
            ],
            "in_app": [
                "Use points mode to see vertices.",
                "Use wireframe mode to see edges.",
                "Use shaded mode to see faces.",
            ],
            "observe": [
                "Changing display mode does not change the mesh.",
                "It only changes how the same data is visualized.",
            ],
        },
        {
            "title": "Mesh Data and Connectivity",
            "lecture_idea": [
                "Mesh data structures store geometry and connectivity.",
                "Connectivity lets us ask which vertices are connected to a given vertex.",
            ],
            "in_app": [
                "Inspect vertex, face, and edge counts.",
                "Use wireframe mode.",
                "Apply smoothing.",
            ],
            "observe": [
                "Smoothing depends on connectivity because each vertex moves according to its neighbors.",
            ],
        },
        {
            "title": "Face Normals",
            "lecture_idea": [
                "Face normals can be computed from face geometry.",
            ],
            "in_app": [
                "Enable face normals.",
                "Try the cube and low-poly sphere.",
            ],
            "observe": [
                "Face normals are attached to faces.",
                "They make the faceted structure clear.",
            ],
        },
        {
            "title": "Vertex Normals",
            "lecture_idea": [
                "Vertex normals can be estimated by averaging incident face normals.",
                "Area-weighted normals account for larger faces.",
            ],
            "in_app": [
                "Enable vertex normals.",
                "Switch between average and area-weighted mode.",
            ],
            "observe": [
                "Vertex normals approximate smooth surface orientation even when the mesh is polygonal.",
            ],
        },
        {
            "title": "Neighbor-Average Smoothing",
            "lecture_idea": [
                "Move pointy vertices to make the mesh smoother.",
                "The new vertex position is based on the average of neighboring vertex positions.",
            ],
            "in_app": [
                "Apply one smoothing iteration.",
                "Adjust lambda/strength.",
            ],
            "observe": [
                "Sharp or uneven regions relax.",
                "Connectivity stays the same.",
            ],
        },
        {
            "title": "Local / Soft Smoothing",
            "lecture_idea": [
                "Soft selection affects nearby vertices more than farther vertices.",
            ],
            "in_app": [
                "Choose Local / soft smoothing.",
                "Select a center vertex.",
                "Adjust graph radius and falloff type.",
            ],
            "observe": [
                "Only part of the mesh smooths strongly.",
                "Increasing radius affects more vertices.",
            ],
        },
        {
            "title": "Repeated Smoothing and Shrinkage",
            "lecture_idea": [
                "Repeated averaging causes mesh shrinkage.",
            ],
            "in_app": [
                "Apply many smoothing iterations.",
                "Watch the before/after comparison.",
                "Watch bounding box, surface area, and volume metrics.",
            ],
            "observe": [
                "The mesh becomes smoother.",
                "It can also become smaller.",
            ],
        },
        {
            "title": "Boundary Preservation",
            "lecture_idea": [
                "Boundary behavior matters on open meshes.",
            ],
            "in_app": [
                "Choose plane/grid.",
                "Compare smoothing with boundary preservation on and off.",
            ],
            "observe": [
                "Without preservation, the border can move inward.",
                "With preservation, border vertices remain fixed.",
            ],
        },
    ]

    for index, concept in enumerate(concepts):
        with st.expander(concept["title"], expanded=index == 0):
            _render_concept_mapping(
                lecture_idea=concept["lecture_idea"],
                in_app=concept["in_app"],
                observe=concept["observe"],
            )


def _render_concept_mapping(
    lecture_idea: list[str],
    in_app: list[str],
    observe: list[str],
) -> None:
    """Render one lecture-to-app concept mapping."""
    st.markdown("**Lecture idea**")
    st.markdown(_bullets(lecture_idea))
    st.markdown("**In the app**")
    st.markdown(_bullets(in_app))
    st.markdown("**Student should observe**")
    st.markdown(_bullets(observe))


def _render_scribe_notes_placeholder() -> None:
    """Render placeholder copy for future lecture scribe notes."""
    st.subheader("Scribe Notes Placeholder")
    st.info(
        "Future version: this area can include notes transcribed from the lecture "
        "recording, with each paragraph linked to the matching visual experiment."
    )


def _prepare_local_smoothing_state(mesh: MeshData) -> tuple[int, int]:
    """Clamp local smoothing widget state to the current mesh."""
    center_max = max(0, mesh.vertex_count - 1)
    current_center = int(st.session_state.get(LOCAL_CENTER_KEY, 0))
    if current_center < 0 or current_center > center_max:
        st.session_state[LOCAL_CENTER_KEY] = 0

    center_vertex = int(st.session_state.get(LOCAL_CENTER_KEY, 0))
    max_radius = _max_graph_radius(mesh, center_vertex)
    current_radius = int(st.session_state.get(LOCAL_RADIUS_KEY, min(2, max_radius)))
    if current_radius < 1 or current_radius > max_radius:
        st.session_state[LOCAL_RADIUS_KEY] = min(2, max_radius)

    return center_max, max_radius


def _max_graph_radius(mesh: MeshData, center_vertex: int) -> int:
    """Return a safe maximum graph radius for the selected center vertex."""
    distances = graph_distances_from_vertex(mesh, center_vertex)
    finite_distances = distances[np.isfinite(distances)]
    if finite_distances.size == 0:
        return 1
    return max(1, int(finite_distances.max()))


def _render_soft_selection_summary(
    mesh: MeshData,
    center_vertex: int,
    soft_radius: int,
    falloff_type: str,
    preserve_boundary: bool,
) -> None:
    """Render a compact text/table summary of the local affected region."""
    summary = affected_soft_selection_vertices(
        mesh,
        center_index=center_vertex,
        radius=soft_radius,
        falloff_type=falloff_type,
        preserve_boundary=preserve_boundary,
    )
    st.caption("Soft selection region summary")
    st.table(
        [
            {"Metric": "Center vertex", "Value": str(summary["center_vertex"])},
            {"Metric": "Graph radius", "Value": str(summary["radius"])},
            {"Metric": "Falloff", "Value": str(summary["falloff"])},
            {"Metric": "Affected vertices", "Value": str(summary["affected_vertices"])},
            {
                "Metric": "Movable affected vertices",
                "Value": str(summary["movable_affected_vertices"]),
            },
            {
                "Metric": "Max graph distance included",
                "Value": _format_value(summary["max_graph_distance_included"], digits=0),
            },
        ]
    )


def _render_before_after_comparison(
    original_mesh: MeshData,
    current_mesh: MeshData,
    display_mode: str,
    background_color: str,
    show_axes: bool,
) -> None:
    """Render original/current visual comparison controls and viewers."""
    st.subheader("Before / After Comparison")
    st.markdown(
        """
        Use this section to compare the original mesh with the current smoothed
        mesh. This makes smoothing and shrinkage easier to see visually.
        """
    )

    comparison_mode = st.selectbox("Comparison mode", COMPARISON_MODES)
    st.caption(
        "Look for inward motion, relaxed sharp features, boundary movement, and "
        "stable topology counts while geometry changes."
    )

    if not original_mesh.valid or not current_mesh.valid:
        st.error("Comparison is available only when both original and current meshes are valid.")
        return

    try:
        if comparison_mode == "Side-by-side":
            original_column, current_column = st.columns(2)
            with original_column:
                st.markdown("**Original mesh**")
                _render_mesh_plotter(
                    original_mesh,
                    display_mode=display_mode,
                    background_color=background_color,
                    show_axes=show_axes,
                    window_size=(500, 420),
                )
            with current_column:
                st.markdown("**Current mesh**")
                _render_mesh_plotter(
                    current_mesh,
                    display_mode=display_mode,
                    background_color=background_color,
                    show_axes=show_axes,
                    window_size=(500, 420),
                )
        elif comparison_mode == "Overlay":
            st.markdown("**Overlay: original wireframe over current mesh**")
            plotter = make_overlay_plotter(
                original_mesh,
                current_mesh,
                background_color=background_color,
                show_axes=show_axes,
                window_size=(820, 500),
            )
            _render_plotter(plotter)
        elif comparison_mode == "Original only":
            st.markdown("**Original mesh**")
            _render_mesh_plotter(
                original_mesh,
                display_mode=display_mode,
                background_color=background_color,
                show_axes=show_axes,
                window_size=(820, 500),
            )
        else:
            st.markdown("**Current mesh**")
            _render_mesh_plotter(
                current_mesh,
                display_mode=display_mode,
                background_color=background_color,
                show_axes=show_axes,
                window_size=(820, 500),
            )
    except ImportError:
        st.error(
            "The comparison viewer requires PyVista and Panel. Install the project "
            "dependencies with `pip install -r requirements.txt` and restart Streamlit."
        )
    except Exception as exc:
        st.error(f"Could not render the comparison view: {exc}")


def _render_mesh_plotter(
    mesh: MeshData,
    display_mode: str,
    background_color: str,
    show_axes: bool,
    window_size: tuple[int, int],
) -> None:
    """Render one mesh viewer without normal overlays."""
    plotter = make_plotter(
        mesh,
        display_mode=display_mode,
        background_color=background_color,
        show_axes=show_axes,
        window_size=window_size,
    )
    _render_plotter(plotter)


def _render_plotter(plotter) -> None:
    """Render a PyVista plotter into Streamlit and close the plotter."""
    try:
        viewer_html = plotter_to_html(plotter)
        st.iframe(
            viewer_html,
            height=plotter.window_size[1],
        )
    finally:
        close = getattr(plotter, "close", None)
        if callable(close):
            close()


def _render_smoothing_metrics(
    original_mesh: MeshData,
    current_mesh: MeshData,
    smoothing_steps: int,
) -> None:
    """Render the original/current comparison metrics."""
    metrics = compare_meshes(
        original_mesh,
        current_mesh,
        smoothing_iterations=smoothing_steps,
    )
    original = metrics["original"]
    current = metrics["current"]

    st.subheader("Smoothing Observation Metrics")
    st.caption(
        "Topology counts should stay stable. Geometry metrics show how smoothing "
        "changes size and shape."
    )

    st.metric("Smoothing iterations applied", smoothing_steps)

    topology_rows = [
        _comparison_row("Vertex count", original, current, "vertex_count"),
        _comparison_row("Face count", original, current, "face_count"),
        _comparison_row("Unique edge count", original, current, "unique_edge_count"),
    ]
    st.table(topology_rows)

    displacement_columns = st.columns(2)
    displacement_columns[0].metric(
        "Average vertex displacement",
        _format_value(metrics["average_displacement"]),
    )
    displacement_columns[1].metric(
        "Max vertex displacement",
        _format_value(metrics["max_displacement"]),
    )

    geometry_rows = [
        {
            "Metric": "Bounding box diagonal",
            "Original": _format_value(original["bounding_box_diagonal"]),
            "Current": _format_value(current["bounding_box_diagonal"]),
            "Change": _format_percent(metrics["bounding_box_percent_change"]),
        },
        {
            "Metric": "Surface area",
            "Original": _format_value(original["surface_area"]),
            "Current": _format_value(current["surface_area"]),
            "Change": _format_percent(metrics["surface_area_percent_change"]),
        },
        {
            "Metric": "Volume",
            "Original": _format_value(original["volume"]),
            "Current": _format_value(current["volume"]),
            "Change": _format_percent(metrics["volume_percent_change"]),
        },
    ]
    st.table(geometry_rows)
    if original["volume"] is None or current["volume"] is None:
        st.caption("Volume is N/A for open or non-watertight meshes.")


def _render_smoothing_history() -> None:
    """Render smoothing history as a table and compact trend chart."""
    st.subheader("Smoothing History")
    history = st.session_state.get(SMOOTHING_HISTORY_KEY, [])
    if not history:
        st.info("Apply smoothing to start the history table.")
        return

    st.table([_format_history_row(row) for row in history])

    chart_rows = []
    for row in history:
        chart_row = {"Total iterations": row["Total iterations"]}
        if row["Bounding box change (%)"] is not None:
            chart_row["Bounding box change (%)"] = row["Bounding box change (%)"]
        if row["Surface area change (%)"] is not None:
            chart_row["Surface area change (%)"] = row["Surface area change (%)"]
        if len(chart_row) > 1:
            chart_rows.append(chart_row)

    if len(chart_rows) >= 2:
        st.line_chart(chart_rows, x="Total iterations")


def _append_smoothing_history(
    original_mesh: MeshData,
    current_mesh: MeshData,
    total_iterations: int,
    smoothing_strength: float,
    preserve_boundary: bool,
    smoothing_mode: str,
    center_vertex: int | None = None,
    soft_radius: int | None = None,
    falloff_type: str | None = None,
) -> None:
    """Append one row for a completed smoothing action."""
    metrics = compare_meshes(
        original_mesh,
        current_mesh,
        smoothing_iterations=total_iterations,
    )
    current = metrics["current"]
    history = list(st.session_state.get(SMOOTHING_HISTORY_KEY, []))
    history.append(
        {
            "Step": len(history) + 1,
            "Total iterations": total_iterations,
            "Mode": smoothing_mode,
            "Center vertex": center_vertex,
            "Soft radius": soft_radius,
            "Falloff": falloff_type,
            "Lambda": float(smoothing_strength),
            "Preserve boundary": bool(preserve_boundary),
            "Average displacement": metrics["average_displacement"],
            "Max displacement": metrics["max_displacement"],
            "Bounding box diagonal": current["bounding_box_diagonal"],
            "Bounding box change (%)": metrics["bounding_box_percent_change"],
            "Surface area": current["surface_area"],
            "Surface area change (%)": metrics["surface_area_percent_change"],
            "Volume": current["volume"],
            "Volume change (%)": metrics["volume_percent_change"],
        }
    )
    st.session_state[SMOOTHING_HISTORY_KEY] = history


def _render_lecture_concept_cards() -> None:
    """Render concise concept cards for the lecture topic."""
    st.subheader("Lecture Concept Cards")
    concept_cards = [
        (
            "Polygonal Mesh",
            [
                "Vertices are the points of the shape.",
                "Edges connect pairs of vertices.",
                "Faces are polygon patches bounded by edges.",
                "Meshes may be triangle, quad, or mixed polygon meshes.",
            ],
        ),
        (
            "Mesh Connectivity",
            [
                "Connectivity tells us which vertices, edges, and faces touch.",
                "Neighboring vertices form a one-ring around a vertex.",
                "Smoothing needs these neighbor queries.",
            ],
        ),
        (
            "Normals",
            [
                "Face normals show one orientation per polygon face.",
                "Vertex normals average nearby face directions.",
                "Area-weighted normals give larger faces more influence.",
                "Normals help reveal how the surface is oriented.",
            ],
        ),
        (
            "Neighbor-Average Smoothing",
            [
                "Pointy vertices move toward their neighboring vertices.",
                "Each step uses the average neighbor position.",
                "The lambda slider controls how far vertices move each step.",
                "More iterations make the surface smoother.",
            ],
        ),
        (
            "Shrinkage",
            [
                "Repeated averaging often pulls vertices inward.",
                "Sharp details relax, but the overall shape can get smaller.",
                "Watch this by applying many iterations to the cube or sphere.",
            ],
        ),
        (
            "Boundary Preservation",
            [
                "A boundary edge belongs to only one face.",
                "Boundary vertices sit on the open border of a mesh.",
                "Preserving them can keep open meshes from collapsing at the border.",
                "Try this on the plane/grid.",
            ],
        ),
    ]

    left_column, right_column = st.columns(2)
    for index, (title, bullets) in enumerate(concept_cards):
        column = left_column if index % 2 == 0 else right_column
        with column:
            with st.expander(title, expanded=index == 0):
                st.markdown("\n".join(f"- {bullet}" for bullet in bullets))


def _render_observation_notes() -> None:
    """Render short notes connecting controls to visible outcomes."""
    st.markdown(
        """
        Use topology modes to separate vertices, edges, and faces. Use normal
        overlays to read surface orientation. Then apply neighbor-average
        smoothing and watch how the mesh relaxes, shrinks, or keeps its boundary.
        """
    )


def _bullets(items: list[str]) -> str:
    """Format short bullet lists for Streamlit markdown."""
    return "\n".join(f"- {item}" for item in items)


def _comparison_row(
    label: str,
    original: dict[str, object],
    current: dict[str, object],
    key: str,
) -> dict[str, object]:
    """Build one original/current topology row."""
    original_value = original[key]
    current_value = current[key]
    change = (
        int(current_value) - int(original_value)
        if isinstance(original_value, int) and isinstance(current_value, int)
        else "N/A"
    )
    return {
        "Metric": label,
        "Original": original_value,
        "Current": current_value,
        "Change": change,
    }


def _format_history_row(row: dict[str, object]) -> dict[str, object]:
    """Format one smoothing history row for display."""
    return {
        "Step": row["Step"],
        "Total iterations": row["Total iterations"],
        "Mode": row.get("Mode", "Global"),
        "Center": _format_optional_int(row.get("Center vertex")),
        "Radius": _format_optional_int(row.get("Soft radius")),
        "Falloff": row.get("Falloff") or "N/A",
        "Lambda": _format_value(row["Lambda"], digits=2),
        "Preserve boundary": row["Preserve boundary"],
        "Avg displacement": _format_value(row["Average displacement"]),
        "Max displacement": _format_value(row["Max displacement"]),
        "BBox diagonal": _format_value(row["Bounding box diagonal"]),
        "BBox change": _format_percent(row["Bounding box change (%)"]),
        "Surface area": _format_value(row["Surface area"]),
        "Area change": _format_percent(row["Surface area change (%)"]),
        "Volume": _format_value(row["Volume"]),
        "Volume change": _format_percent(row["Volume change (%)"]),
    }


def _format_optional_int(value: object) -> str:
    """Format an optional integer metric."""
    if value is None:
        return "N/A"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "N/A"


def _format_value(value: object, digits: int = 4) -> str:
    """Format a numeric metric or return N/A."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def _format_percent(value: object) -> str:
    """Format a percent metric or return N/A."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _mesh_source_key(prefix: str, name: str, file_bytes: bytes | None = None) -> str:
    """Create a stable session-state key for the currently selected mesh source."""
    if file_bytes is None:
        return f"{prefix}:{name}"
    digest = hashlib.sha1(file_bytes).hexdigest()[:12]
    return f"{prefix}:{name}:{len(file_bytes)}:{digest}"


def _sync_working_mesh(base_mesh: MeshData, source_key: str) -> None:
    """Reset original/working meshes whenever the selected source changes."""
    if st.session_state.get(MESH_SOURCE_KEY) == source_key:
        st.session_state.setdefault(SMOOTHING_HISTORY_KEY, [])
        return

    st.session_state[MESH_SOURCE_KEY] = source_key
    st.session_state[ORIGINAL_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[WORKING_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[SMOOTHING_STEPS_KEY] = 0
    st.session_state[SMOOTHING_HISTORY_KEY] = []
    st.session_state[LOCAL_CENTER_KEY] = _nearest_mesh_center_vertex(base_mesh)
    st.session_state[LOCAL_RADIUS_KEY] = 2


def _working_mesh() -> MeshData:
    """Return the current working mesh from Streamlit session state."""
    return st.session_state[WORKING_MESH_KEY]


def _nearest_mesh_center_vertex(mesh: MeshData) -> int:
    """Return the vertex index nearest the mesh bounding-box center."""
    if not mesh.valid or mesh.vertex_count == 0:
        return 0
    bbox_center = (mesh.vertices.min(axis=0) + mesh.vertices.max(axis=0)) / 2.0
    distances = np.linalg.norm(mesh.vertices - bbox_center, axis=1)
    return int(np.argmin(distances))


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Mesh Smoothing Lecture Lab",
        layout="wide",
    )

    st.title("Mesh Smoothing Lecture Lab")
    _render_lab_intro()
    _render_guided_walkthrough()

    base_mesh = create_sample_mesh("Cube")
    source_key = _mesh_source_key("sample", "Cube")

    with st.sidebar:
        st.header("Mesh source")
        source_kind = st.radio(
            "Choose source",
            ["Built-in sample mesh", "Upload OBJ file"],
            label_visibility="collapsed",
        )

        if source_kind == "Built-in sample mesh":
            selected_sample = st.selectbox("Sample mesh", sample_mesh_names())
            base_mesh = create_sample_mesh(selected_sample)
            source_key = _mesh_source_key("sample", selected_sample)
        else:
            uploaded_file = st.file_uploader("Upload OBJ file", type=["obj"])
            if uploaded_file is None:
                st.info("No OBJ uploaded. Showing the default cube.")
                base_mesh = create_sample_mesh("Cube")
                source_key = _mesh_source_key("fallback", "no-upload")
            else:
                uploaded_bytes = uploaded_file.getvalue()
                loaded_mesh = _load_uploaded_mesh(uploaded_bytes, uploaded_file.name)
                if loaded_mesh.valid:
                    base_mesh = loaded_mesh
                    source_key = _mesh_source_key("upload", uploaded_file.name, uploaded_bytes)
                    st.success(f"Loaded {uploaded_file.name}")
                else:
                    base_mesh = create_sample_mesh("Cube")
                    source_key = _mesh_source_key(
                        "fallback-invalid",
                        uploaded_file.name,
                        uploaded_bytes,
                    )
                    st.error(loaded_mesh.error_message)
                    st.info("Showing the default cube instead.")

        _sync_working_mesh(base_mesh, source_key)
        mesh = _working_mesh()

        st.header("Visualize topology")
        st.caption("Switch display modes to identify vertices, edges, and faces.")
        display_mode = st.selectbox("Display mode", DISPLAY_MODES)
        background_label = st.selectbox("Background", ["Light", "Dark"])
        show_axes = st.checkbox("Show axes", value=True)
        background_color = "white" if background_label == "Light" else "#1f2933"

        st.header("Visualize normals")
        st.caption("Normals reveal face and vertex orientation.")
        show_face_normals = st.checkbox("Show face normals", value=False)
        show_vertex_normals = st.checkbox("Show vertex normals", value=False)
        normal_length = st.slider("Normal length", 0.0, 1.0, 0.25, 0.05)
        vertex_normal_weighting = st.selectbox(
            "Vertex normal weighting",
            ["average", "area-weighted"],
            format_func=lambda value: (
                "Average incident face normals"
                if value == "average"
                else "Area-weighted incident face normals"
            ),
        )

        st.header("Run smoothing experiment")
        st.caption(
            "Apply neighbor-average smoothing once, then repeat to observe shrinkage."
        )
        smoothing_mode = st.selectbox("Smoothing mode", SMOOTHING_MODES)
        smoothing_iterations = st.slider("Smoothing iterations", 1, 20, 1)
        smoothing_strength = st.slider("Smoothing strength (lambda)", 0.0, 1.0, 0.3, 0.05)
        preserve_boundary = st.checkbox("Preserve boundary vertices", value=True)

        center_vertex: int | None = None
        soft_radius: int | None = None
        falloff_type: str | None = None
        if smoothing_mode == "Local / soft smoothing":
            st.caption(
                "Local / soft smoothing applies the same neighbor-average smoothing "
                "formula, but scales the movement by distance from a selected center "
                "vertex. Nearby vertices are affected more than far vertices."
            )
            center_max, max_radius = _prepare_local_smoothing_state(mesh)
            center_vertex = st.slider(
                "Center vertex index",
                0,
                center_max,
                value=int(st.session_state.get(LOCAL_CENTER_KEY, 0)),
                key=LOCAL_CENTER_KEY,
                help=f"Valid center range: 0 to {center_max}",
            )
            max_radius = _max_graph_radius(mesh, center_vertex)
            if st.session_state.get(LOCAL_RADIUS_KEY, 1) > max_radius:
                st.session_state[LOCAL_RADIUS_KEY] = min(2, max_radius)
            radius_value = int(st.session_state.get(LOCAL_RADIUS_KEY, min(2, max_radius)))
            if max_radius <= 1:
                soft_radius = 1
                st.session_state[LOCAL_RADIUS_KEY] = soft_radius
                st.caption(
                    "Soft selection radius is fixed at 1 graph step for this "
                    "center vertex on the current mesh."
                )
            else:
                soft_radius = st.slider(
                    "Soft selection radius (graph steps)",
                    1,
                    max_radius,
                    value=radius_value,
                    key=LOCAL_RADIUS_KEY,
                )
            falloff_type = st.selectbox("Falloff type", FALLOFF_TYPES)
            _render_soft_selection_summary(
                mesh,
                center_vertex=center_vertex,
                soft_radius=soft_radius,
                falloff_type=falloff_type,
                preserve_boundary=preserve_boundary,
            )

        if st.button("Apply smoothing"):
            if smoothing_mode == "Local / soft smoothing":
                st.session_state[WORKING_MESH_KEY] = laplacian_smooth_local(
                    _working_mesh(),
                    iterations=smoothing_iterations,
                    strength=smoothing_strength,
                    center_index=center_vertex or 0,
                    radius=soft_radius or 1,
                    falloff_type=falloff_type or "linear",
                    preserve_boundary=preserve_boundary,
                )
            else:
                st.session_state[WORKING_MESH_KEY] = laplacian_smooth(
                    _working_mesh(),
                    iterations=smoothing_iterations,
                    strength=smoothing_strength,
                    preserve_boundary=preserve_boundary,
                )
            st.session_state[SMOOTHING_STEPS_KEY] += smoothing_iterations
            mesh = _working_mesh()
            _append_smoothing_history(
                st.session_state[ORIGINAL_MESH_KEY],
                mesh,
                st.session_state[SMOOTHING_STEPS_KEY],
                smoothing_strength,
                preserve_boundary,
                smoothing_mode=(
                    "Local / soft"
                    if smoothing_mode == "Local / soft smoothing"
                    else "Global"
                ),
                center_vertex=center_vertex if smoothing_mode == "Local / soft smoothing" else None,
                soft_radius=soft_radius if smoothing_mode == "Local / soft smoothing" else None,
                falloff_type=falloff_type if smoothing_mode == "Local / soft smoothing" else None,
            )
            st.success(f"Applied {smoothing_iterations} smoothing iteration(s).")

        if st.button("Reset to original mesh"):
            st.session_state[WORKING_MESH_KEY] = clone_mesh(st.session_state[ORIGINAL_MESH_KEY])
            st.session_state[SMOOTHING_STEPS_KEY] = 0
            st.session_state[SMOOTHING_HISTORY_KEY] = []
            mesh = _working_mesh()
            st.success("Restored the original mesh.")

        st.header("Observe results")
        boundary_count = len(find_boundary_vertices(mesh))
        st.caption(f"Boundary vertices detected: {boundary_count}")
        if st.session_state[SMOOTHING_STEPS_KEY] > 0:
            st.caption(f"Smoothing iterations applied: {st.session_state[SMOOTHING_STEPS_KEY]}")

        st.subheader("Mesh statistics")
        _render_statistics(mesh)

        st.subheader("Control-to-result notes")
        _render_observation_notes()

    st.subheader(mesh.name)
    if not mesh.valid:
        st.error(mesh.error_message or "The selected mesh is not valid.")
        return

    try:
        plotter = make_plotter(
            mesh,
            display_mode=display_mode,
            background_color=background_color,
            show_axes=show_axes,
            show_face_normals=show_face_normals,
            show_vertex_normals=show_vertex_normals,
            normal_length=normal_length,
            vertex_normal_weighting=vertex_normal_weighting,
        )
        _render_plotter(plotter)
    except ImportError:
        st.error(
            "The 3D viewer requires PyVista and Panel. Install the project dependencies "
            "with `pip install -r requirements.txt` and restart Streamlit."
        )
    except Exception as exc:
        st.error(f"Could not render the mesh: {exc}")

    _render_before_after_comparison(
        st.session_state[ORIGINAL_MESH_KEY],
        mesh,
        display_mode=display_mode,
        background_color=background_color,
        show_axes=show_axes,
    )
    _render_smoothing_metrics(
        st.session_state[ORIGINAL_MESH_KEY],
        mesh,
        st.session_state[SMOOTHING_STEPS_KEY],
    )
    _render_smoothing_history()
    _render_lecture_notes_companion()
    _render_scribe_notes_placeholder()
    _render_how_to_use_lab()
    _render_lecture_concept_cards()


if __name__ == "__main__":
    main()
