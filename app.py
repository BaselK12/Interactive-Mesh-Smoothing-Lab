"""Streamlit entry point for the Mesh Smoothing Lecture Lab."""

from __future__ import annotations

import hashlib

import streamlit as st
import streamlit.components.v1 as components

from src.mesh_core import MeshData
from src.mesh_metrics import compare_meshes
from src.mesh_ops import clone_mesh, find_boundary_vertices, laplacian_smooth
from src.sample_meshes import create_sample_mesh, sample_mesh_names
from src.visualization import DISPLAY_MODES, make_plotter, plotter_to_html


MESH_SOURCE_KEY = "mesh_source_key"
ORIGINAL_MESH_KEY = "original_mesh"
WORKING_MESH_KEY = "working_mesh"
SMOOTHING_STEPS_KEY = "smoothing_steps"
SMOOTHING_HISTORY_KEY = "smoothing_history"


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
        6. Compare boundary preservation on/off for the plane/grid.
        7. Reset and try another mesh.
        """
    )


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

    st.dataframe(
        [_format_history_row(row) for row in history],
        hide_index=True,
        use_container_width=True,
    )

    chart_rows = []
    for row in history:
        chart_row = {"Total iterations": row["Total iterations"]}
        if row["Bounding box change (%)"] is not None:
            chart_row["Bounding box change (%)"] = row["Bounding box change (%)"]
        if row["Surface area change (%)"] is not None:
            chart_row["Surface area change (%)"] = row["Surface area change (%)"]
        if len(chart_row) > 1:
            chart_rows.append(chart_row)

    if chart_rows:
        st.line_chart(chart_rows, x="Total iterations")


def _append_smoothing_history(
    original_mesh: MeshData,
    current_mesh: MeshData,
    total_iterations: int,
    smoothing_strength: float,
    preserve_boundary: bool,
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


def _working_mesh() -> MeshData:
    """Return the current working mesh from Streamlit session state."""
    return st.session_state[WORKING_MESH_KEY]


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
        smoothing_iterations = st.slider("Smoothing iterations", 1, 20, 1)
        smoothing_strength = st.slider("Smoothing strength (lambda)", 0.0, 1.0, 0.3, 0.05)
        preserve_boundary = st.checkbox("Preserve boundary vertices", value=True)

        if st.button("Apply smoothing"):
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
        viewer_html = plotter_to_html(plotter)
        components.html(
            viewer_html,
            height=plotter.window_size[1],
            scrolling=False,
        )
    except ImportError:
        st.error(
            "The 3D viewer requires PyVista and Panel. Install the project dependencies "
            "with `pip install -r requirements.txt` and restart Streamlit."
        )
    except Exception as exc:
        st.error(f"Could not render the mesh: {exc}")

    _render_smoothing_metrics(
        st.session_state[ORIGINAL_MESH_KEY],
        mesh,
        st.session_state[SMOOTHING_STEPS_KEY],
    )
    _render_smoothing_history()
    _render_how_to_use_lab()
    _render_lecture_concept_cards()


if __name__ == "__main__":
    main()
