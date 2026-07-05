"""Streamlit entry point for the Mesh Smoothing Lecture Lab."""

from __future__ import annotations

import hashlib

import numpy as np
import streamlit as st

from src.mesh_core import MeshData
from src.mesh_metrics import compare_meshes
from src.mesh_ops import (
    COTANGENT_LAPLACIAN,
    GLOBAL_SMOOTHING_METHODS,
    NOISE_ALONG_NORMALS,
    NOISE_MODES,
    TAUBIN,
    UNIFORM_LAPLACIAN,
    add_noise,
    affected_soft_selection_vertices,
    apply_global_smoothing,
    clone_mesh,
    compute_roughness_energy,
    find_boundary_vertices,
    graph_distances_from_vertex,
    inspect_cotangent_step,
    inspect_local_step,
    inspect_uniform_step,
    is_triangle_mesh,
    laplacian_smooth,
    laplacian_smooth_local,
)
from src.sample_meshes import create_sample_mesh, sample_mesh_names
from src.visualization import (
    DISPLAY_MODES,
    make_overlay_plotter,
    make_plotter,
    make_step_inspector_plotter,
    plotter_to_html,
)


MESH_SOURCE_KEY = "mesh_source_key"
ORIGINAL_MESH_KEY = "original_mesh"
WORKING_MESH_KEY = "working_mesh"
SMOOTHING_STEPS_KEY = "smoothing_steps"
SMOOTHING_HISTORY_KEY = "smoothing_history"
LOCAL_CENTER_KEY = "local_center_vertex"
LOCAL_RADIUS_KEY = "local_soft_radius"
NOISE_APPLIED_KEY = "noise_applied"
NOISE_INFO_KEY = "noise_info"
INSPECT_VERTEX_KEY = "inspect_vertex_index"
SOURCE_KIND_KEY = "source_kind"
SAMPLE_MESH_KEY = "sample_mesh"
DISPLAY_MODE_KEY = "display_mode"
BACKGROUND_KEY = "viewer_background"
SHOW_AXES_KEY = "show_axes"
SHOW_FACE_NORMALS_KEY = "show_face_normals"
SHOW_VERTEX_NORMALS_KEY = "show_vertex_normals"
NORMAL_LENGTH_KEY = "normal_length"
VERTEX_NORMAL_WEIGHTING_KEY = "vertex_normal_weighting"
LIVE_PREVIEW_KEY = "live_preview_enabled"
PREVIEW_MESH_KEY = "preview_mesh"
PREVIEW_NOTE_KEY = "preview_note"
NOISE_ENABLED_KEY = "noise_enabled"
NOISE_STRENGTH_KEY = "noise_strength"
NOISE_SEED_KEY = "noise_seed"
NOISE_MODE_KEY = "noise_mode"
SMOOTHING_MODE_KEY = "smoothing_mode"
SMOOTHING_ITERATIONS_KEY = "smoothing_iterations"
SMOOTHING_STRENGTH_KEY = "smoothing_strength"
SMOOTHING_METHOD_KEY = "smoothing_method"
PRESERVE_BOUNDARY_KEY = "preserve_boundary"
TAUBIN_MU_KEY = "taubin_mu"
FALLOFF_TYPE_KEY = "falloff_type"
PLAYGROUND_COMPARISON_KEY = "playground_comparison_mode"
PRESET_MESSAGE_KEY = "preset_message"
RESET_REQUESTED_KEY = "reset_requested"
COMPARISON_MODES = ["Side-by-side", "Overlay", "Original only", "Current only"]
PLAYGROUND_COMPARISON_MODES = ["Overlay", "Side-by-side", "Original only", "Current only"]
LEARNING_TABS = [
    "Playground",
    "Method Comparison",
    "Step Inspector",
    "Advanced Metrics",
]
SMOOTHING_MODES = ["Global smoothing", "Local / soft smoothing"]
FALLOFF_TYPES = ["linear", "smoothstep"]
TAUBIN_DEFAULT_MU = -0.53
LIVE_PREVIEW_VERTEX_LIMIT = 50000
LIVE_PREVIEW_WORK_LIMIT = 500000


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

        This lab is a focused deep dive into mesh smoothing:

        - A polygonal mesh is made of vertices, edges, and faces.
        - Smoothing moves each vertex toward the average of its neighbors.
        - Add controlled noise to build a clean -> noisy -> smoothed experiment.
        - Compare uniform Laplacian, Taubin, and cotangent-weighted smoothing.
        - Measure roughness energy and shrinkage, not just look at the shape.
        - Inspect the exact one-step computation for a single vertex.
        - See why repeated smoothing shrinks meshes and how boundaries behave.
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

    _render_roughness_metrics(original_mesh, current_mesh)


def _render_roughness_metrics(original_mesh: MeshData, current_mesh: MeshData) -> None:
    """Render roughness/smoothness energy for original vs current mesh."""
    original_roughness = compute_roughness_energy(original_mesh)
    current_roughness = compute_roughness_energy(current_mesh)

    st.markdown("**Roughness (smoothness) energy**")
    st.caption(
        "Roughness energy is the average distance from each vertex to the average "
        "of its neighbors. Lower usually means smoother geometry."
    )
    if original_roughness["mean"] is None and current_roughness["mean"] is None:
        st.caption("Roughness energy is N/A: no vertex adjacency is available.")
        return

    roughness_rows = [
        {
            "Metric": "Roughness energy (mean)",
            "Original": _format_value(original_roughness["mean"]),
            "Current": _format_value(current_roughness["mean"]),
            "Change": _format_percent(
                _percent_change(original_roughness["mean"], current_roughness["mean"])
            ),
        },
        {
            "Metric": "Max roughness",
            "Original": _format_value(original_roughness["max"]),
            "Current": _format_value(current_roughness["max"]),
            "Change": _format_percent(
                _percent_change(original_roughness["max"], current_roughness["max"])
            ),
        },
        {
            "Metric": "RMS roughness",
            "Original": _format_value(original_roughness["rms"]),
            "Current": _format_value(current_roughness["rms"]),
            "Change": _format_percent(
                _percent_change(original_roughness["rms"], current_roughness["rms"])
            ),
        },
    ]
    st.table(roughness_rows)
    st.caption(
        "A method can reduce roughness while also shrinking the mesh. Compare this "
        "table with the bounding-box and surface-area changes above."
    )


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
    method: str = UNIFORM_LAPLACIAN,
    mu: float | None = None,
    roughness_before: float | None = None,
    roughness_after: float | None = None,
    center_vertex: int | None = None,
    soft_radius: int | None = None,
    falloff_type: str | None = None,
    action: str = "Smoothing",
) -> None:
    """Append one row for a completed smoothing (or noise) action."""
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
            "Action": action,
            "Total iterations": total_iterations,
            "Mode": smoothing_mode,
            "Method": method,
            "Mu": mu,
            "Center vertex": center_vertex,
            "Soft radius": soft_radius,
            "Falloff": falloff_type,
            "Lambda": float(smoothing_strength),
            "Preserve boundary": bool(preserve_boundary),
            "Roughness before": roughness_before,
            "Roughness after": roughness_after,
            "Roughness change (%)": _percent_change(roughness_before, roughness_after),
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


def _percent_change(before: float | None, after: float | None) -> float | None:
    """Return percent change from before to after, or None when undefined."""
    if before is None or after is None:
        return None
    try:
        before_value = float(before)
        after_value = float(after)
    except (TypeError, ValueError):
        return None
    if abs(before_value) <= 1.0e-12:
        return None
    return 100.0 * (after_value - before_value) / before_value


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
        "Action": row.get("Action", "Smoothing"),
        "Iterations": row["Total iterations"],
        "Mode": row.get("Mode", "Global"),
        "Method": row.get("Method", "N/A"),
        "Mu": _format_value(row.get("Mu"), digits=2),
        "Center": _format_optional_int(row.get("Center vertex")),
        "Radius": _format_optional_int(row.get("Soft radius")),
        "Falloff": row.get("Falloff") or "N/A",
        "Lambda": _format_value(row["Lambda"], digits=2),
        "Preserve boundary": row["Preserve boundary"],
        "Roughness before": _format_value(row.get("Roughness before")),
        "Roughness after": _format_value(row.get("Roughness after")),
        "Roughness change": _format_percent(row.get("Roughness change (%)")),
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
        st.session_state.setdefault(NOISE_APPLIED_KEY, False)
        st.session_state.setdefault(NOISE_INFO_KEY, None)
        st.session_state.setdefault(PREVIEW_MESH_KEY, None)
        st.session_state.setdefault(PREVIEW_NOTE_KEY, "")
        st.session_state.setdefault(INSPECT_VERTEX_KEY, 0)
        return

    st.session_state[MESH_SOURCE_KEY] = source_key
    st.session_state[ORIGINAL_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[WORKING_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[SMOOTHING_STEPS_KEY] = 0
    st.session_state[SMOOTHING_HISTORY_KEY] = []
    st.session_state[LOCAL_CENTER_KEY] = _nearest_mesh_center_vertex(base_mesh)
    st.session_state[LOCAL_RADIUS_KEY] = 2
    st.session_state[PREVIEW_MESH_KEY] = None
    st.session_state[PREVIEW_NOTE_KEY] = ""
    st.session_state[NOISE_APPLIED_KEY] = False
    st.session_state[NOISE_INFO_KEY] = None
    st.session_state[INSPECT_VERTEX_KEY] = 0
    st.session_state.pop("method_comparison_rows", None)
    st.session_state.pop("method_comparison_verts", None)
    st.session_state.pop("method_comparison_input_mesh", None)


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


def _render_noise_experiment_notes() -> None:
    """Explain the noisy-mesh experiment and show current noise status."""
    st.subheader("Noisy Mesh Experiment")
    st.markdown(
        """
        Real scanned or hand-built meshes often contain small geometric errors and
        surface roughness. This experiment lets you add controlled noise so you can
        see **why smoothing is useful**:

        - Noise simulates small geometric errors or roughness on the surface.
        - Smoothing attempts to reduce this roughness.
        - The clean original mesh is preserved, so you can always compare
          clean -> noisy -> smoothed.

        Use the sidebar **Noisy mesh experiment** controls to add noise along
        vertex normals (or as random 3D displacement), then apply a smoothing
        method and watch the roughness energy drop.
        """
    )
    noise_info = st.session_state.get(NOISE_INFO_KEY)
    if st.session_state.get(NOISE_APPLIED_KEY) and noise_info:
        st.info(
            f"Noise applied to the working mesh: mode = {noise_info['mode']}, "
            f"strength = {noise_info['strength']:.2f}, seed = {noise_info['seed']}. "
            "The clean original is still available in the comparison and via "
            "'Reset to clean original'."
        )


def _run_method_comparison(
    input_mesh: MeshData,
    iterations: int,
    lam: float,
    mu: float,
    preserve_boundary: bool,
) -> list[dict[str, object]]:
    """Run every global method on a copy of the input mesh and collect metrics.

    The input mesh is never mutated: :func:`apply_global_smoothing` operates on
    clones. Each row reports status, settings, displacement, size change, and
    roughness reduction so students can compare methods on identical input.
    """
    input_roughness = compute_roughness_energy(input_mesh)["mean"]
    rows: list[dict[str, object]] = []
    for method in GLOBAL_SMOOTHING_METHODS:
        result = apply_global_smoothing(
            input_mesh,
            method=method,
            iterations=iterations,
            lam=lam,
            mu=mu,
            preserve_boundary=preserve_boundary,
        )
        if not result.supported:
            rows.append(
                {
                    "Method": method,
                    "Status": "unsupported",
                    "Notes": result.note,
                    "Iterations": iterations,
                    "Lambda": lam,
                    "Mu": mu if method == TAUBIN else None,
                    "Avg displacement": None,
                    "Max displacement": None,
                    "BBox change (%)": None,
                    "Area change (%)": None,
                    "Volume change (%)": None,
                    "Roughness before": input_roughness,
                    "Roughness after": None,
                    "Roughness reduction (%)": None,
                    "Topology changed?": "no",
                    "Result mesh": None,
                }
            )
            continue

        metrics = compare_meshes(input_mesh, result.mesh, smoothing_iterations=iterations)
        result_roughness = compute_roughness_energy(result.mesh)["mean"]
        reduction = _percent_change(input_roughness, result_roughness)
        topology_changed = (
            metrics["current"]["vertex_count"] != metrics["original"]["vertex_count"]
            or metrics["current"]["face_count"] != metrics["original"]["face_count"]
            or metrics["current"]["unique_edge_count"] != metrics["original"]["unique_edge_count"]
        )
        rows.append(
            {
                "Method": method,
                "Status": "ok",
                "Notes": "",
                "Iterations": iterations,
                "Lambda": lam,
                "Mu": mu if method == TAUBIN else None,
                "Avg displacement": metrics["average_displacement"],
                "Max displacement": metrics["max_displacement"],
                "BBox change (%)": metrics["bounding_box_percent_change"],
                "Area change (%)": metrics["surface_area_percent_change"],
                "Volume change (%)": metrics["volume_percent_change"],
                "Roughness before": input_roughness,
                "Roughness after": result_roughness,
                "Roughness reduction (%)": (-reduction if reduction is not None else None),
                "Topology changed?": "yes" if topology_changed else "no",
                "Result mesh": clone_mesh(result.mesh),
            }
        )
    return rows


def _render_method_comparison_lab(mesh: MeshData) -> None:
    """Render the Phase 6 method comparison lab."""
    st.subheader("Smoothing Method Comparison")
    st.markdown(
        """
        Run every available smoothing method on the **same** starting mesh (a copy
        of the current working mesh) and compare the results side by side.

        - The same noisy mesh can be smoothed with different methods.
        - Good smoothing is a tradeoff between reducing roughness and preserving
          shape.
        - Lower roughness is not always better if the mesh shrinks too much.

        This comparison does **not** change your current working mesh.
        """
    )

    columns = st.columns(4)
    comp_iterations = columns[0].slider("Comparison iterations", 1, 30, 10, key="comp_iters")
    comp_lambda = columns[1].slider("Comparison lambda", 0.0, 1.0, 0.5, 0.05, key="comp_lambda")
    comp_mu = columns[2].slider("Comparison Taubin mu", -0.95, -0.05, TAUBIN_DEFAULT_MU, 0.01, key="comp_mu")
    comp_boundary = columns[3].checkbox("Preserve boundary", value=True, key="comp_boundary")

    if st.button("Run comparison from current mesh"):
        if not mesh.valid:
            st.error("The current mesh is not valid; comparison is unavailable.")
            return
        comparison_input = clone_mesh(mesh)
        st.session_state["method_comparison_rows"] = _run_method_comparison(
            comparison_input,
            iterations=comp_iterations,
            lam=comp_lambda,
            mu=comp_mu,
            preserve_boundary=comp_boundary,
        )
        st.session_state["method_comparison_input_mesh"] = comparison_input
        st.session_state["method_comparison_verts"] = mesh.vertex_count

    rows = st.session_state.get("method_comparison_rows")
    if not rows:
        st.info("Press 'Run comparison from current mesh' to build the comparison table.")
        return

    comparison_input = st.session_state.get("method_comparison_input_mesh")
    if comparison_input is not None:
        _render_method_comparison_visuals(comparison_input, rows)

    st.table([_format_comparison_row(row) for row in rows])
    _render_comparison_ranking(rows)
    st.caption(
        "Displacement, bounding-box, area, and volume changes are measured "
        "relative to the comparison input mesh. Volume change is N/A for open "
        "or non-watertight meshes."
    )


def _render_method_comparison_visuals(input_mesh: MeshData, rows: list[dict[str, object]]) -> None:
    """Render visual previews for each method-comparison result."""
    st.markdown("**Visual comparison**")
    st.caption("Each card overlays the comparison input wireframe on that method's result.")
    columns = st.columns(3)
    for index, row in enumerate(rows):
        with columns[index % 3]:
            with st.container(border=True):
                st.markdown(f"**{row['Method']}**")
                result_mesh = row.get("Result mesh")
                if row.get("Status") != "ok" or not isinstance(result_mesh, MeshData):
                    st.warning(row.get("Notes") or "Unsupported for this mesh.")
                    continue
                try:
                    plotter = make_overlay_plotter(
                        input_mesh,
                        result_mesh,
                        background_color="white",
                        show_axes=False,
                        window_size=(300, 260),
                    )
                    _render_plotter(plotter)
                except ImportError:
                    st.error("Visual comparison requires PyVista and Panel.")
                except Exception as exc:
                    st.error(f"Could not render comparison visual: {exc}")
                st.caption(
                    f"Roughness reduction: {_format_percent(row.get('Roughness reduction (%)'))} | "
                    f"BBox: {_format_percent(row.get('BBox change (%)'))}"
                )


def _format_comparison_row(row: dict[str, object]) -> dict[str, object]:
    """Format one method-comparison row for display."""
    return {
        "Method": row["Method"],
        "Status": row["Status"],
        "Notes": row["Notes"] or "",
        "Iters": row["Iterations"],
        "Lambda": _format_value(row["Lambda"], digits=2),
        "Mu": _format_value(row["Mu"], digits=2),
        "Avg disp": _format_value(row["Avg displacement"]),
        "Max disp": _format_value(row["Max displacement"]),
        "BBox change": _format_percent(row["BBox change (%)"]),
        "Area change": _format_percent(row["Area change (%)"]),
        "Volume change": _format_percent(row["Volume change (%)"]),
        "Rough before": _format_value(row["Roughness before"]),
        "Rough after": _format_value(row["Roughness after"]),
        "Rough reduction": _format_percent(row["Roughness reduction (%)"]),
        "Topology changed?": row["Topology changed?"],
    }


def _render_comparison_ranking(rows: list[dict[str, object]]) -> None:
    """Render short ranking notes for the comparison table."""
    supported = [row for row in rows if row["Status"] == "ok"]
    unsupported = [row for row in rows if row["Status"] != "ok"]
    notes: list[str] = []

    def _abs_bbox(row: dict[str, object]) -> float:
        value = row["BBox change (%)"]
        return abs(float(value)) if value is not None else float("inf")

    def _reduction(row: dict[str, object]) -> float:
        value = row["Roughness reduction (%)"]
        return float(value) if value is not None else float("-inf")

    if supported:
        least_shrink = min(supported, key=_abs_bbox)
        most_smooth = max(supported, key=_reduction)
        notes.append(f"**Least shrinkage (bounding box):** {least_shrink['Method']}")
        notes.append(f"**Largest roughness reduction:** {most_smooth['Method']}")
    for row in unsupported:
        notes.append(f"**Unsupported for this mesh:** {row['Method']}")

    if notes:
        st.markdown("\n".join(f"- {note}" for note in notes))


def _render_step_inspector(mesh: MeshData) -> None:
    """Render the Phase 7 one-step smoothing computation inspector."""
    st.subheader("Smoothing Step Inspector")
    st.markdown(
        """
        Inspect exactly what happens to **one vertex** during a single smoothing
        step. This makes the smoothing formula visible: each vertex moves toward
        the (weighted) average of its neighbors.
        """
    )
    if not mesh.valid or mesh.vertex_count == 0:
        st.info("The current mesh has no vertices to inspect.")
        return

    max_index = mesh.vertex_count - 1
    current_index = int(st.session_state.get(INSPECT_VERTEX_KEY, 0))
    if current_index < 0 or current_index > max_index:
        st.session_state[INSPECT_VERTEX_KEY] = 0

    columns = st.columns(2)
    if max_index == 0:
        vertex_index = 0
        columns[0].caption("Only one vertex is available to inspect.")
    else:
        vertex_index = columns[0].slider(
            "Vertex index to inspect",
            0,
            max_index,
            key=INSPECT_VERTEX_KEY,
            help=f"Valid range: 0 to {max_index}",
        )
    inspect_methods = ["Uniform Laplacian"]
    if is_triangle_mesh(mesh):
        inspect_methods.append("Cotangent weights")
    if st.session_state.get("inspect_method") not in inspect_methods:
        st.session_state["inspect_method"] = inspect_methods[0]
    inspect_method = columns[1].selectbox("Inspection method", inspect_methods, key="inspect_method")
    inspect_lambda = st.slider("Inspection lambda / strength", 0.0, 1.0, 0.5, 0.05, key="inspect_lambda")

    if inspect_method == "Cotangent weights":
        _render_cotangent_inspection(mesh, vertex_index, inspect_lambda)
    else:
        _render_uniform_inspection(mesh, vertex_index, inspect_lambda)


def _render_uniform_inspection(mesh: MeshData, vertex_index: int, lam: float) -> None:
    """Render the uniform one-step computation for a single vertex."""
    info = inspect_uniform_step(mesh, vertex_index, lam=lam)
    st.markdown(
        f"**Vertex {info['vertex_index']}** — valence (neighbor count): "
        f"**{info['valence']}**"
    )
    _render_step_inspector_visual(
        mesh,
        int(info["vertex_index"]),
        [int(neighbor) for neighbor in info.get("neighbors", [])],
        info.get("predicted_position"),
    )
    st.write("Current position:", _format_vector(info["current_position"]))

    if info["valence"] == 0:
        st.warning("This vertex has no neighbors, so smoothing would not move it.")
        return

    neighbor_rows = [
        {
            "Neighbor index": int(neighbor),
            "Position": _format_vector(position),
        }
        for neighbor, position in zip(info["neighbors"], info["neighbor_positions"])
    ]
    st.table(neighbor_rows)

    st.table(
        [
            {"Quantity": "Neighbor average", "Value": _format_vector(info["neighbor_average"])},
            {"Quantity": "Displacement (avg - current)", "Value": _format_vector(info["displacement"])},
            {"Quantity": "Lambda", "Value": _format_value(info["lambda"], digits=2)},
            {
                "Quantity": "Predicted new position (one step)",
                "Value": _format_vector(info["predicted_position"]),
            },
        ]
    )
    st.caption(
        "Predicted position = current + lambda x (neighbor average - current)."
    )


def _render_cotangent_inspection(mesh: MeshData, vertex_index: int, strength: float) -> None:
    """Render the cotangent-weighted one-step computation for a single vertex."""
    info = inspect_cotangent_step(mesh, vertex_index, strength=strength)
    if not info.get("supported"):
        st.warning(info.get("note", "Cotangent weights are unavailable for this mesh."))
        return

    st.markdown(f"**Vertex {info['vertex_index']}** cotangent-weighted neighborhood")
    _render_step_inspector_visual(
        mesh,
        int(info["vertex_index"]),
        [int(neighbor) for neighbor in info.get("neighbors", [])],
        info.get("predicted_position"),
    )
    st.write("Current position:", _format_vector(info["current_position"]))

    neighbors = info["neighbors"]
    if not neighbors:
        st.warning("This vertex has no cotangent neighbors.")
        return

    weight_rows = [
        {
            "Neighbor index": int(neighbor),
            "Weight": _format_value(weight, digits=4),
            "Normalized weight": _format_value(norm_weight, digits=4),
        }
        for neighbor, weight, norm_weight in zip(
            neighbors, info["weights"], info["normalized_weights"]
        )
    ]
    st.table(weight_rows)
    st.table(
        [
            {"Quantity": "Sum of weights", "Value": _format_value(info["weight_sum"], digits=4)},
            {"Quantity": "Weighted target", "Value": _format_vector(info["weighted_target"])},
            {"Quantity": "Strength", "Value": _format_value(info["strength"], digits=2)},
            {
                "Quantity": "Predicted new position (one step)",
                "Value": _format_vector(info["predicted_position"]),
            },
        ]
    )
    if info.get("note"):
        st.caption(info["note"])
    st.caption(
        "Cotangent smoothing weights neighbors using triangle geometry, so the "
        "target is a weighted average rather than a plain average."
    )


def _render_step_inspector_visual(
    mesh: MeshData,
    vertex_index: int,
    neighbors: list[int],
    predicted_position: object | None,
) -> None:
    """Render the selected vertex, neighbors, and predicted one-step move."""
    try:
        plotter = make_step_inspector_plotter(
            mesh,
            vertex_index=vertex_index,
            neighbors=neighbors,
            predicted_position=predicted_position,
            background_color="white",
            show_axes=True,
            window_size=(760, 380),
        )
        _render_plotter(plotter)
        st.caption("Red = selected vertex, orange = neighbors, green = predicted one-step position.")
    except ImportError:
        st.error("The inspector visual requires PyVista and Panel.")
    except Exception as exc:
        st.error(f"Could not render inspector visual: {exc}")


def _format_vector(vector: object) -> str:
    """Format a 3D vector for compact display, or N/A."""
    if vector is None:
        return "N/A"
    array = np.asarray(vector, dtype=float).ravel()
    if array.size < 3:
        return "N/A"
    return f"({array[0]:.4f}, {array[1]:.4f}, {array[2]:.4f})"


def _render_learning_summary(
    mesh: MeshData,
    smoothing_mode: str,
    smoothing_method: str,
    smoothing_iterations: int,
    smoothing_strength: float,
    preserve_boundary: bool,
) -> None:
    """Render the Phase 9 learning summary and Markdown download."""
    st.subheader("Learning Summary")
    st.markdown(
        "A snapshot of your current experiment. Use it to write up what you "
        "observed about smoothing, roughness, and shrinkage."
    )

    original_mesh = st.session_state[ORIGINAL_MESH_KEY]
    total_iterations = st.session_state[SMOOTHING_STEPS_KEY]
    metrics = compare_meshes(original_mesh, mesh, smoothing_iterations=total_iterations)
    current = metrics["current"]
    roughness_current = compute_roughness_energy(mesh)["mean"]
    roughness_original = compute_roughness_energy(original_mesh)["mean"]
    noise_info = st.session_state.get(NOISE_INFO_KEY)

    settings_rows = [
        {"Setting": "Mesh", "Value": mesh.name},
        {"Setting": "Mesh type", "Value": mesh.mesh_type},
        {"Setting": "Smoothing mode", "Value": smoothing_mode},
        {"Setting": "Selected method", "Value": smoothing_method if smoothing_mode == "Global smoothing" else "Uniform (soft-weighted)"},
        {"Setting": "Iterations per apply", "Value": str(smoothing_iterations)},
        {"Setting": "Total iterations applied", "Value": str(total_iterations)},
        {"Setting": "Lambda", "Value": _format_value(smoothing_strength, digits=2)},
        {"Setting": "Preserve boundary", "Value": str(bool(preserve_boundary))},
        {"Setting": "Noise applied", "Value": ("yes" if st.session_state.get(NOISE_APPLIED_KEY) else "no")},
    ]
    st.table(settings_rows)

    interpretation = _build_interpretation(metrics, roughness_original, roughness_current)
    st.markdown(interpretation)

    markdown = _build_summary_markdown(
        mesh,
        original_mesh,
        smoothing_mode,
        smoothing_method,
        smoothing_iterations,
        total_iterations,
        smoothing_strength,
        preserve_boundary,
        metrics,
        roughness_original,
        roughness_current,
        current,
        noise_info,
    )
    st.download_button(
        "Download Markdown Summary",
        data=markdown,
        file_name="mesh_smoothing_summary.md",
        mime="text/markdown",
    )


def _build_interpretation(
    metrics: dict[str, object],
    roughness_original: float | None,
    roughness_current: float | None,
) -> str:
    """Build a short interpretation sentence from the current metrics."""
    parts: list[str] = []
    reduction = _percent_change(roughness_original, roughness_current)
    if reduction is None:
        parts.append("Roughness change is not available for this mesh.")
    elif reduction < 0:
        parts.append(f"Roughness energy decreased by {abs(reduction):.1f}% versus the original (smoother).")
    elif reduction > 0:
        parts.append(f"Roughness energy increased by {reduction:.1f}% versus the original (rougher).")
    else:
        parts.append("Roughness energy is unchanged versus the original.")

    bbox = metrics["bounding_box_percent_change"]
    if bbox is not None:
        if bbox < -0.05:
            parts.append(f"The bounding box shrank by {abs(bbox):.1f}% (shrinkage).")
        elif bbox > 0.05:
            parts.append(f"The bounding box grew by {bbox:.1f}%.")
        else:
            parts.append("The bounding box size is essentially unchanged.")
    return "**Interpretation:** " + " ".join(parts)


def _build_summary_markdown(
    mesh: MeshData,
    original_mesh: MeshData,
    smoothing_mode: str,
    smoothing_method: str,
    iterations_per_apply: int,
    total_iterations: int,
    smoothing_strength: float,
    preserve_boundary: bool,
    metrics: dict[str, object],
    roughness_original: float | None,
    roughness_current: float | None,
    current: dict[str, object],
    noise_info: dict[str, object] | None,
) -> str:
    """Build the downloadable Markdown learning summary (no local paths/secrets)."""
    lines = [
        "# Mesh Smoothing Learning Summary",
        "",
        "## Experiment settings",
        f"- Mesh: {mesh.name}",
        f"- Mesh type: {mesh.mesh_type}",
        f"- Smoothing mode: {smoothing_mode}",
        f"- Selected method: {smoothing_method}",
        f"- Iterations per apply: {iterations_per_apply}",
        f"- Total iterations applied: {total_iterations}",
        f"- Lambda: {smoothing_strength:.2f}",
        f"- Preserve boundary: {bool(preserve_boundary)}",
    ]
    if noise_info:
        lines.append(
            f"- Noise: mode={noise_info['mode']}, strength={noise_info['strength']:.2f}, "
            f"seed={noise_info['seed']}"
        )
    lines += [
        "",
        "## Metrics (original vs current)",
        "| Metric | Original | Current | Change |",
        "| --- | --- | --- | --- |",
        f"| Vertices | {metrics['original']['vertex_count']} | {current['vertex_count']} | "
        f"{current['vertex_count'] - metrics['original']['vertex_count']} |",
        f"| Faces | {metrics['original']['face_count']} | {current['face_count']} | "
        f"{current['face_count'] - metrics['original']['face_count']} |",
        f"| Bounding box diagonal | {_format_value(metrics['original']['bounding_box_diagonal'])} | "
        f"{_format_value(current['bounding_box_diagonal'])} | {_format_percent(metrics['bounding_box_percent_change'])} |",
        f"| Surface area | {_format_value(metrics['original']['surface_area'])} | "
        f"{_format_value(current['surface_area'])} | {_format_percent(metrics['surface_area_percent_change'])} |",
        f"| Volume | {_format_value(metrics['original']['volume'])} | "
        f"{_format_value(current['volume'])} | {_format_percent(metrics['volume_percent_change'])} |",
        f"| Roughness energy | {_format_value(roughness_original)} | "
        f"{_format_value(roughness_current)} | {_format_percent(_percent_change(roughness_original, roughness_current))} |",
        "",
        "## Smoothing history",
    ]
    history = st.session_state.get(SMOOTHING_HISTORY_KEY, [])
    if history:
        lines.append("| Step | Action | Method | Iters | Lambda | Rough before | Rough after | BBox change |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in history:
            lines.append(
                f"| {row['Step']} | {row.get('Action', 'Smoothing')} | {row.get('Method', 'N/A')} | "
                f"{row['Total iterations']} | {_format_value(row['Lambda'], digits=2)} | "
                f"{_format_value(row.get('Roughness before'))} | {_format_value(row.get('Roughness after'))} | "
                f"{_format_percent(row['Bounding box change (%)'])} |"
            )
    else:
        lines.append("No smoothing actions recorded yet.")
    lines += [
        "",
        "## What the metrics mean",
        "- **Roughness energy**: average distance from each vertex to the average of its neighbors. Lower is smoother.",
        "- **Bounding box / surface area / volume change**: how much the mesh shrank or grew. Negative usually means shrinkage.",
        "- **Displacement**: how far vertices moved from the original.",
        "",
        "## Limitations",
        "- Uniform Laplacian smoothing shrinks meshes; Taubin reduces this.",
        "- Cotangent smoothing supports triangle meshes only.",
        "- Volume is available only for closed, watertight meshes.",
        "- Local soft regions use graph distance, not Euclidean distance.",
    ]
    return "\n".join(lines)


def _ensure_ui_defaults() -> None:
    """Initialize widget state so presets can safely update controls."""
    defaults = {
        SOURCE_KIND_KEY: "Built-in sample mesh",
        SAMPLE_MESH_KEY: "Cube",
        DISPLAY_MODE_KEY: "Wireframe + shaded mesh",
        BACKGROUND_KEY: "Light",
        SHOW_AXES_KEY: True,
        SHOW_FACE_NORMALS_KEY: False,
        SHOW_VERTEX_NORMALS_KEY: False,
        NORMAL_LENGTH_KEY: 0.25,
        VERTEX_NORMAL_WEIGHTING_KEY: "average",
        LIVE_PREVIEW_KEY: True,
        NOISE_ENABLED_KEY: False,
        NOISE_STRENGTH_KEY: 0.4,
        NOISE_SEED_KEY: 42,
        NOISE_MODE_KEY: NOISE_ALONG_NORMALS,
        SMOOTHING_MODE_KEY: "Global smoothing",
        SMOOTHING_ITERATIONS_KEY: 1,
        SMOOTHING_STRENGTH_KEY: 0.3,
        SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
        PRESERVE_BOUNDARY_KEY: True,
        TAUBIN_MU_KEY: TAUBIN_DEFAULT_MU,
        FALLOFF_TYPE_KEY: "linear",
        PLAYGROUND_COMPARISON_KEY: "Side-by-side",
        PRESET_MESSAGE_KEY: "",
        RESET_REQUESTED_KEY: False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _inject_layout_css() -> None:
    """Add small layout rules for the visual playground."""
    st.markdown(
        """
        <style>
        div[data-testid="stColumn"]:has(.sticky-preview-marker) {
            position: sticky;
            top: 4.25rem;
            align-self: flex-start;
            z-index: 5;
            background: var(--background-color);
            padding-bottom: 0.5rem;
        }
        .sticky-preview-marker {
            height: 0;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_mesh_source_sidebar() -> tuple[MeshData, str]:
    """Render global mesh source controls and return the selected base mesh."""
    st.header("Mesh source")
    source_kind = st.radio(
        "Choose source",
        ["Built-in sample mesh", "Upload OBJ file"],
        key=SOURCE_KIND_KEY,
        label_visibility="collapsed",
    )

    if source_kind == "Built-in sample mesh":
        selected_sample = st.selectbox(
            "Sample mesh",
            sample_mesh_names(),
            key=SAMPLE_MESH_KEY,
        )
        return create_sample_mesh(selected_sample), _mesh_source_key("sample", selected_sample)

    uploaded_file = st.file_uploader("Upload OBJ file", type=["obj"], key="uploaded_obj")
    if uploaded_file is None:
        st.info("No OBJ uploaded. Showing the default cube.")
        return create_sample_mesh("Cube"), _mesh_source_key("fallback", "no-upload")

    uploaded_bytes = uploaded_file.getvalue()
    loaded_mesh = _load_uploaded_mesh(uploaded_bytes, uploaded_file.name)
    if loaded_mesh.valid:
        st.success(f"Loaded {uploaded_file.name}")
        return loaded_mesh, _mesh_source_key("upload", uploaded_file.name, uploaded_bytes)

    st.error(loaded_mesh.error_message)
    st.info("Showing the default cube instead.")
    return (
        create_sample_mesh("Cube"),
        _mesh_source_key("fallback-invalid", uploaded_file.name, uploaded_bytes),
    )


def _render_viewer_sidebar(mesh: MeshData) -> dict[str, object]:
    """Render viewer controls shared by the learning tabs."""
    st.header("Viewer")
    display_mode = st.selectbox("Display mode", DISPLAY_MODES, key=DISPLAY_MODE_KEY)
    background_label = st.selectbox("Background", ["Light", "Dark"], key=BACKGROUND_KEY)
    show_axes = st.checkbox("Show axes", key=SHOW_AXES_KEY)

    with st.expander("Normals", expanded=False):
        show_face_normals = st.checkbox("Show face normals", key=SHOW_FACE_NORMALS_KEY)
        show_vertex_normals = st.checkbox("Show vertex normals", key=SHOW_VERTEX_NORMALS_KEY)
        normal_length = st.slider("Normal length", 0.0, 1.0, key=NORMAL_LENGTH_KEY, step=0.05)
        vertex_normal_weighting = st.selectbox(
            "Vertex normal weighting",
            ["average", "area-weighted"],
            key=VERTEX_NORMAL_WEIGHTING_KEY,
            format_func=lambda value: (
                "Average incident face normals"
                if value == "average"
                else "Area-weighted incident face normals"
            ),
        )

    st.header("Committed mesh")
    _render_statistics(mesh)
    st.caption(f"Boundary vertices detected: {len(find_boundary_vertices(mesh))}")
    if st.session_state.get(SMOOTHING_STEPS_KEY, 0) > 0:
        st.caption(f"Smoothing iterations committed: {st.session_state[SMOOTHING_STEPS_KEY]}")

    return {
        "display_mode": display_mode,
        "background_color": "white" if background_label == "Light" else "#1f2933",
        "show_axes": bool(show_axes),
        "show_face_normals": bool(show_face_normals),
        "show_vertex_normals": bool(show_vertex_normals),
        "normal_length": float(normal_length),
        "vertex_normal_weighting": vertex_normal_weighting,
    }


def _apply_preset(name: str) -> None:
    """Set session controls for one visual learning preset."""
    common = {
        LIVE_PREVIEW_KEY: True,
        PLAYGROUND_COMPARISON_KEY: "Side-by-side",
        NOISE_MODE_KEY: NOISE_ALONG_NORMALS,
        TAUBIN_MU_KEY: TAUBIN_DEFAULT_MU,
        PRESERVE_BOUNDARY_KEY: True,
        FALLOFF_TYPE_KEY: "linear",
    }
    preset_values = {
        "See shrinkage": {
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 6,
            SMOOTHING_STRENGTH_KEY: 0.35,
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh: repeated uniform averaging should show shrinkage without switching mesh source.",
        },
        "Remove noise": {
            NOISE_ENABLED_KEY: True,
            NOISE_STRENGTH_KEY: 0.4,
            NOISE_SEED_KEY: 42,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 8,
            SMOOTHING_STRENGTH_KEY: 0.35,
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh: noise makes the surface rough, and smoothing should reduce the roughness card.",
        },
        "Uniform vs Taubin": {
            NOISE_ENABLED_KEY: True,
            NOISE_STRENGTH_KEY: 0.4,
            NOISE_SEED_KEY: 42,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 10,
            SMOOTHING_STRENGTH_KEY: 0.45,
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh: switch to Method Comparison to run Uniform, Taubin, and Cotangent on this same setup.",
        },
        "Boundary preservation": {
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 8,
            SMOOTHING_STRENGTH_KEY: 0.5,
            PRESERVE_BOUNDARY_KEY: True,
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh. Boundary preservation is most visible on open meshes such as Plane/grid.",
        },
        "Local soft smoothing": {
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Local / soft smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 8,
            SMOOTHING_STRENGTH_KEY: 0.45,
            LOCAL_CENTER_KEY: 0,
            LOCAL_RADIUS_KEY: 1,
            FALLOFF_TYPE_KEY: "smoothstep",
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh: local smoothing moves nearby vertices more than vertices outside the radius.",
        },
        "Inspect one vertex": {
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 1,
            SMOOTHING_STRENGTH_KEY: 0.5,
            INSPECT_VERTEX_KEY: 0,
            PRESET_MESSAGE_KEY: "Control preset applied to the current mesh: open Step Inspector to connect the visible movement to one vertex formula.",
        },
    }
    values = preset_values.get(name, {})
    for key, value in {**common, **values}.items():
        st.session_state[key] = value
    st.session_state[RESET_REQUESTED_KEY] = True


def _reset_experiment() -> None:
    """Restore the working mesh to the clean original and clear derived state."""
    if ORIGINAL_MESH_KEY not in st.session_state:
        return
    original = st.session_state[ORIGINAL_MESH_KEY]
    st.session_state[WORKING_MESH_KEY] = clone_mesh(original)
    st.session_state[SMOOTHING_STEPS_KEY] = 0
    st.session_state[SMOOTHING_HISTORY_KEY] = []
    st.session_state[PREVIEW_MESH_KEY] = None
    st.session_state[PREVIEW_NOTE_KEY] = ""
    st.session_state[NOISE_APPLIED_KEY] = False
    st.session_state[NOISE_INFO_KEY] = None
    st.session_state[INSPECT_VERTEX_KEY] = 0
    st.session_state.pop("method_comparison_rows", None)
    st.session_state.pop("method_comparison_verts", None)
    st.session_state.pop("method_comparison_input_mesh", None)


def _render_preset_buttons() -> None:
    """Render the preset launcher buttons."""
    st.markdown("**Experiment presets**")
    rows = [
        ("See shrinkage", "Remove noise"),
        ("Uniform vs Taubin", "Boundary preservation"),
        ("Local soft smoothing", "Inspect one vertex"),
    ]
    for left_label, right_label in rows:
        left, right = st.columns(2)
        left.button(left_label, use_container_width=True, on_click=_apply_preset, args=(left_label,))
        right.button(right_label, use_container_width=True, on_click=_apply_preset, args=(right_label,))

    message = st.session_state.get(PRESET_MESSAGE_KEY)
    if message:
        st.info(message)


def _render_playground_controls(mesh: MeshData) -> dict[str, object]:
    """Render live preview controls and return normalized values."""
    _render_preset_buttons()
    st.divider()

    live_preview = st.checkbox("Live Preview", key=LIVE_PREVIEW_KEY)
    st.caption(
        "On: controls update a temporary preview. Off: use the apply buttons to change the working mesh."
    )

    st.markdown("**Noise**")
    noise_enabled = st.checkbox("Noise enabled", key=NOISE_ENABLED_KEY)
    noise_strength = st.slider("Noise strength", 0.0, 1.0, key=NOISE_STRENGTH_KEY, step=0.05)
    noise_seed = st.number_input(
        "Noise seed",
        min_value=0,
        max_value=999999,
        key=NOISE_SEED_KEY,
        step=1,
    )
    noise_mode = st.selectbox("Noise mode", NOISE_MODES, key=NOISE_MODE_KEY)

    st.markdown("**Smoothing**")
    smoothing_mode = st.selectbox("Smoothing mode", SMOOTHING_MODES, key=SMOOTHING_MODE_KEY)
    smoothing_iterations = st.slider(
        "Smoothing iterations",
        0,
        30,
        key=SMOOTHING_ITERATIONS_KEY,
        help="Use 0 to preview noise without smoothing.",
    )
    smoothing_strength = st.slider(
        "Smoothing strength (lambda)",
        0.0,
        1.0,
        key=SMOOTHING_STRENGTH_KEY,
        step=0.05,
    )
    preserve_boundary = st.checkbox("Preserve boundary vertices", key=PRESERVE_BOUNDARY_KEY)

    smoothing_method = UNIFORM_LAPLACIAN
    taubin_mu = float(st.session_state.get(TAUBIN_MU_KEY, TAUBIN_DEFAULT_MU))
    center_vertex: int | None = None
    soft_radius: int | None = None
    falloff_type: str | None = None

    if smoothing_mode == "Global smoothing":
        smoothing_method = st.selectbox(
            "Smoothing method",
            GLOBAL_SMOOTHING_METHODS,
            key=SMOOTHING_METHOD_KEY,
        )
        if smoothing_method == TAUBIN:
            taubin_mu = st.slider(
                "Taubin mu (negative correction)",
                -0.95,
                -0.05,
                key=TAUBIN_MU_KEY,
                step=0.01,
            )
        elif smoothing_method == COTANGENT_LAPLACIAN and not is_triangle_mesh(mesh):
            st.warning(
                "Cotangent smoothing supports triangle meshes only. Try Low-poly sphere or pyramid.obj."
            )
    else:
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
            st.caption("Soft selection radius is fixed at 1 graph step for this center vertex.")
        else:
            soft_radius = st.slider(
                "Soft selection radius (graph steps)",
                1,
                max_radius,
                value=radius_value,
                key=LOCAL_RADIUS_KEY,
            )
        falloff_type = st.selectbox("Falloff type", FALLOFF_TYPES, key=FALLOFF_TYPE_KEY)
        _render_soft_selection_summary(
            mesh,
            center_vertex=center_vertex,
            soft_radius=soft_radius,
            falloff_type=falloff_type,
            preserve_boundary=preserve_boundary,
        )

    return {
        "live_preview": bool(live_preview),
        "noise_enabled": bool(noise_enabled),
        "noise_strength": float(noise_strength),
        "noise_seed": int(noise_seed),
        "noise_mode": noise_mode,
        "smoothing_mode": smoothing_mode,
        "smoothing_iterations": int(smoothing_iterations),
        "smoothing_strength": float(smoothing_strength),
        "preserve_boundary": bool(preserve_boundary),
        "smoothing_method": smoothing_method,
        "taubin_mu": float(taubin_mu),
        "center_vertex": center_vertex,
        "soft_radius": soft_radius,
        "falloff_type": falloff_type,
    }


def _live_preview_guard(mesh: MeshData, controls: dict[str, object]) -> str | None:
    """Return a warning when live preview should be skipped for responsiveness."""
    iterations = max(1, int(controls["smoothing_iterations"]))
    if mesh.vertex_count > LIVE_PREVIEW_VERTEX_LIMIT:
        return (
            f"Live preview is paused for this {mesh.vertex_count}-vertex mesh. "
            "Turn Live Preview off and use Apply smoothing."
        )
    if mesh.vertex_count * iterations > LIVE_PREVIEW_WORK_LIMIT:
        return (
            "Live preview is paused for this mesh/iteration count to keep the app responsive. "
            "Lower iterations or commit with Live Preview off."
        )
    return None


def _build_preview_mesh(
    working_mesh: MeshData,
    controls: dict[str, object],
) -> tuple[MeshData, dict[str, object]]:
    """Compute the temporary preview mesh without mutating the working mesh."""
    info: dict[str, object] = {
        "supported": True,
        "note": "",
        "noise_applied": False,
        "smoothing_applied": False,
        "changed": False,
    }
    if not controls["live_preview"]:
        return working_mesh, info

    guard_note = _live_preview_guard(working_mesh, controls)
    if guard_note:
        info["supported"] = False
        info["note"] = guard_note
        return working_mesh, info

    preview = clone_mesh(working_mesh)
    if controls["noise_enabled"] and controls["noise_strength"] > 0.0:
        preview = add_noise(
            preview,
            strength=float(controls["noise_strength"]),
            seed=int(controls["noise_seed"]),
            mode=str(controls["noise_mode"]),
        )
        info["noise_applied"] = True
        info["changed"] = True

    iterations = int(controls["smoothing_iterations"])
    if iterations <= 0:
        st.session_state[PREVIEW_MESH_KEY] = preview
        st.session_state[PREVIEW_NOTE_KEY] = str(info["note"])
        return preview, info

    if controls["smoothing_mode"] == "Local / soft smoothing":
        preview = laplacian_smooth_local(
            preview,
            iterations=iterations,
            strength=float(controls["smoothing_strength"]),
            center_index=int(controls["center_vertex"] or 0),
            radius=int(controls["soft_radius"] or 1),
            falloff_type=str(controls["falloff_type"] or "linear"),
            preserve_boundary=bool(controls["preserve_boundary"]),
        )
        info["smoothing_applied"] = True
        info["changed"] = True
    else:
        result = apply_global_smoothing(
            preview,
            method=str(controls["smoothing_method"]),
            iterations=iterations,
            lam=float(controls["smoothing_strength"]),
            mu=float(controls["taubin_mu"]),
            preserve_boundary=bool(controls["preserve_boundary"]),
        )
        if result.supported:
            preview = result.mesh
            info["smoothing_applied"] = True
            info["changed"] = True
        else:
            info["supported"] = False
            info["note"] = result.note

    st.session_state[PREVIEW_MESH_KEY] = preview
    st.session_state[PREVIEW_NOTE_KEY] = str(info["note"])
    return preview, info


def _method_label(controls: dict[str, object]) -> str:
    """Return the method label used in history and summaries."""
    if controls["smoothing_mode"] == "Local / soft smoothing":
        return "Uniform (soft-weighted)"
    return str(controls["smoothing_method"])


def _commit_preview_mesh(
    working_mesh: MeshData,
    preview_mesh: MeshData,
    controls: dict[str, object],
    preview_info: dict[str, object],
) -> None:
    """Promote the preview mesh to the committed working mesh."""
    if not preview_info.get("supported", True):
        st.warning(preview_info.get("note") or "Preview is not supported for this mesh.")
        return
    if not preview_info.get("changed"):
        st.info("No preview changes to commit.")
        return

    roughness_before = compute_roughness_energy(working_mesh)["mean"]
    committed = clone_mesh(preview_mesh)
    st.session_state[WORKING_MESH_KEY] = committed

    added_iterations = (
        int(controls["smoothing_iterations"]) if preview_info.get("smoothing_applied") else 0
    )
    st.session_state[SMOOTHING_STEPS_KEY] += added_iterations
    roughness_after = compute_roughness_energy(committed)["mean"]

    if preview_info.get("noise_applied"):
        st.session_state[NOISE_APPLIED_KEY] = True
        st.session_state[NOISE_INFO_KEY] = {
            "strength": float(controls["noise_strength"]),
            "seed": int(controls["noise_seed"]),
            "mode": controls["noise_mode"],
        }

    is_local = controls["smoothing_mode"] == "Local / soft smoothing"
    _append_smoothing_history(
        st.session_state[ORIGINAL_MESH_KEY],
        committed,
        st.session_state[SMOOTHING_STEPS_KEY],
        float(controls["smoothing_strength"]),
        bool(controls["preserve_boundary"]),
        smoothing_mode=("Local / soft" if is_local else "Global"),
        method=_method_label(controls),
        mu=float(controls["taubin_mu"])
        if (not is_local and controls["smoothing_method"] == TAUBIN)
        else None,
        roughness_before=roughness_before,
        roughness_after=roughness_after,
        center_vertex=int(controls["center_vertex"]) if is_local else None,
        soft_radius=int(controls["soft_radius"]) if is_local else None,
        falloff_type=str(controls["falloff_type"]) if is_local else None,
        action="Commit preview",
    )
    st.success("Committed preview as the current working mesh.")
    st.rerun()


def _add_noise_to_working(controls: dict[str, object]) -> None:
    """Apply noise directly to the committed working mesh when live preview is off."""
    source_mesh = _working_mesh()
    roughness_before = compute_roughness_energy(source_mesh)["mean"]
    noisy = add_noise(
        source_mesh,
        strength=float(controls["noise_strength"]),
        seed=int(controls["noise_seed"]),
        mode=str(controls["noise_mode"]),
    )
    st.session_state[WORKING_MESH_KEY] = noisy
    roughness_after = compute_roughness_energy(noisy)["mean"]
    st.session_state[NOISE_APPLIED_KEY] = True
    st.session_state[NOISE_INFO_KEY] = {
        "strength": float(controls["noise_strength"]),
        "seed": int(controls["noise_seed"]),
        "mode": controls["noise_mode"],
    }
    _append_smoothing_history(
        st.session_state[ORIGINAL_MESH_KEY],
        noisy,
        st.session_state[SMOOTHING_STEPS_KEY],
        smoothing_strength=0.0,
        preserve_boundary=False,
        smoothing_mode="Noise",
        method=f"Noise ({controls['noise_mode']})",
        roughness_before=roughness_before,
        roughness_after=roughness_after,
        action="Add noise",
    )
    st.success("Noise added to the current working mesh.")
    st.rerun()


def _apply_smoothing_to_working(controls: dict[str, object]) -> None:
    """Apply smoothing directly to the working mesh when live preview is off."""
    iterations = int(controls["smoothing_iterations"])
    if iterations <= 0:
        st.info("Set iterations above 0 to apply smoothing.")
        return

    source_mesh = _working_mesh()
    roughness_before = compute_roughness_energy(source_mesh)["mean"]
    is_local = controls["smoothing_mode"] == "Local / soft smoothing"
    applied = True

    if is_local:
        next_mesh = laplacian_smooth_local(
            source_mesh,
            iterations=iterations,
            strength=float(controls["smoothing_strength"]),
            center_index=int(controls["center_vertex"] or 0),
            radius=int(controls["soft_radius"] or 1),
            falloff_type=str(controls["falloff_type"] or "linear"),
            preserve_boundary=bool(controls["preserve_boundary"]),
        )
    else:
        result = apply_global_smoothing(
            source_mesh,
            method=str(controls["smoothing_method"]),
            iterations=iterations,
            lam=float(controls["smoothing_strength"]),
            mu=float(controls["taubin_mu"]),
            preserve_boundary=bool(controls["preserve_boundary"]),
        )
        if result.supported:
            next_mesh = result.mesh
        else:
            applied = False
            st.warning(result.note or "This method is not supported for the current mesh.")

    if not applied:
        return

    st.session_state[WORKING_MESH_KEY] = next_mesh
    st.session_state[SMOOTHING_STEPS_KEY] += iterations
    roughness_after = compute_roughness_energy(next_mesh)["mean"]
    _append_smoothing_history(
        st.session_state[ORIGINAL_MESH_KEY],
        next_mesh,
        st.session_state[SMOOTHING_STEPS_KEY],
        float(controls["smoothing_strength"]),
        bool(controls["preserve_boundary"]),
        smoothing_mode=("Local / soft" if is_local else "Global"),
        method=_method_label(controls),
        mu=float(controls["taubin_mu"])
        if (not is_local and controls["smoothing_method"] == TAUBIN)
        else None,
        roughness_before=roughness_before,
        roughness_after=roughness_after,
        center_vertex=int(controls["center_vertex"]) if is_local else None,
        soft_radius=int(controls["soft_radius"]) if is_local else None,
        falloff_type=str(controls["falloff_type"]) if is_local else None,
    )
    st.success(f"Applied {iterations} smoothing iteration(s).")
    st.rerun()


def _render_commit_controls(
    working_mesh: MeshData,
    active_mesh: MeshData,
    controls: dict[str, object],
    preview_info: dict[str, object],
) -> None:
    """Render commit, manual apply, and reset actions."""
    st.divider()
    if controls["live_preview"]:
        if preview_info.get("note"):
            st.warning(str(preview_info["note"]))
        if st.button(
            "Commit preview as current mesh",
            use_container_width=True,
            disabled=not bool(preview_info.get("changed")) or not bool(preview_info.get("supported", True)),
        ):
            _commit_preview_mesh(working_mesh, active_mesh, controls, preview_info)
    else:
        st.caption("Live Preview is off. These buttons mutate the committed working mesh.")
        if st.button("Add noise to current mesh", use_container_width=True):
            _add_noise_to_working(controls)
        if st.button("Apply smoothing", use_container_width=True):
            _apply_smoothing_to_working(controls)

    if st.button("Reset experiment", use_container_width=True):
        _reset_experiment()
        st.success("Restored the clean original mesh.")
        st.rerun()


def _render_playground_viewer(
    original_mesh: MeshData,
    active_mesh: MeshData,
    controls: dict[str, object],
    viewer_options: dict[str, object],
) -> None:
    """Render the primary visual preview area."""
    mesh_label = "Preview mesh" if controls["live_preview"] else "Working mesh"
    st.markdown(f"**{mesh_label}: {active_mesh.name}**")
    comparison_mode = st.selectbox(
        "Playground view",
        PLAYGROUND_COMPARISON_MODES,
        key=PLAYGROUND_COMPARISON_KEY,
    )

    if not original_mesh.valid or not active_mesh.valid:
        st.error(active_mesh.error_message or "The selected mesh is not valid.")
        return

    try:
        if comparison_mode == "Overlay":
            plotter = make_overlay_plotter(
                original_mesh,
                active_mesh,
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                window_size=(760, 560),
            )
            _render_plotter(plotter)
        elif comparison_mode == "Side-by-side":
            original_column, active_column = st.columns(2)
            with original_column:
                st.caption("Original clean mesh")
                _render_mesh_plotter(
                    original_mesh,
                    display_mode=str(viewer_options["display_mode"]),
                    background_color=str(viewer_options["background_color"]),
                    show_axes=bool(viewer_options["show_axes"]),
                    window_size=(360, 420),
                )
            with active_column:
                st.caption(mesh_label)
                _render_mesh_plotter(
                    active_mesh,
                    display_mode=str(viewer_options["display_mode"]),
                    background_color=str(viewer_options["background_color"]),
                    show_axes=bool(viewer_options["show_axes"]),
                    window_size=(360, 420),
                )
        elif comparison_mode == "Original only":
            _render_mesh_plotter(
                original_mesh,
                display_mode=str(viewer_options["display_mode"]),
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                window_size=(760, 560),
            )
        else:
            plotter = make_plotter(
                active_mesh,
                display_mode=str(viewer_options["display_mode"]),
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                show_face_normals=bool(viewer_options["show_face_normals"]),
                show_vertex_normals=bool(viewer_options["show_vertex_normals"]),
                normal_length=float(viewer_options["normal_length"]),
                vertex_normal_weighting=str(viewer_options["vertex_normal_weighting"]),
                window_size=(760, 560),
            )
            _render_plotter(plotter)
    except ImportError:
        st.error(
            "The 3D viewer requires PyVista and Panel. Install dependencies with "
            "`pip install -r requirements.txt` and restart Streamlit."
        )
    except Exception as exc:
        st.error(f"Could not render the mesh: {exc}")


def _render_dynamic_explanation(
    mesh: MeshData,
    controls: dict[str, object],
    preview_info: dict[str, object],
) -> None:
    """Render the short explanation panel for the current controls."""
    st.subheader("What you are seeing")
    bullets: list[str] = []

    if preview_info.get("note"):
        bullets.append(str(preview_info["note"]))

    if controls["smoothing_mode"] == "Local / soft smoothing":
        bullets.extend(
            [
                "Smoothing strength depends on graph distance from the selected center.",
                "Nearby vertices move more; vertices outside the radius stay unchanged.",
                "Increase the radius to widen the soft selection region.",
            ]
        )
    elif controls["smoothing_method"] == UNIFORM_LAPLACIAN:
        bullets.extend(
            [
                "Each vertex moves toward the average of its neighbors.",
                "Roughness usually decreases as sharp changes relax.",
                "Repeated averaging can shrink the mesh; compare the wireframe to the shaded result.",
            ]
        )
    elif controls["smoothing_method"] == TAUBIN:
        bullets.extend(
            [
                "Taubin alternates smoothing with a negative correction step.",
                "The correction is intended to reduce shrinkage.",
                "Compare the shrinkage card to Uniform Laplacian.",
            ]
        )
    elif controls["smoothing_method"] == COTANGENT_LAPLACIAN:
        if is_triangle_mesh(mesh):
            bullets.extend(
                [
                    "Cotangent smoothing uses triangle angles to weight neighbors.",
                    "The result depends on geometry, not only connectivity.",
                    "It is defined here only for triangle meshes.",
                ]
            )
        else:
            bullets.append("Cotangent smoothing is unsupported here because this mesh is not triangle-only.")

    if controls["preserve_boundary"]:
        boundary_count = len(find_boundary_vertices(mesh))
        if boundary_count > 0:
            bullets.append("Boundary vertices are fixed, which helps open meshes like the plane/grid keep their border.")
        else:
            bullets.append("Boundary preservation is on, but this closed mesh has no boundary vertices to pin.")
    if controls["noise_enabled"]:
        bullets.append("Noise creates rough geometry; smoothing attempts to reduce that roughness.")
    if not controls["live_preview"]:
        bullets.append("Live Preview is off, so the viewer shows only committed working-mesh changes.")

    st.markdown(_bullets(bullets[:7]))


def _metric_card(label: str, value: str, interpretation: str) -> None:
    """Render one compact metric card."""
    with st.container(border=True):
        st.metric(label, value)
        st.caption(interpretation)


def _render_metric_cards(original_mesh: MeshData, active_mesh: MeshData) -> None:
    """Render simple metric cards for the visual playground."""
    st.subheader("Quick metrics")
    metrics = compare_meshes(original_mesh, active_mesh, smoothing_iterations=0)
    rough_original = compute_roughness_energy(original_mesh)["mean"]
    rough_active = compute_roughness_energy(active_mesh)["mean"]
    rough_change = _percent_change(rough_original, rough_active)
    original = metrics["original"]
    current = metrics["current"]
    topology_changed = (
        original["vertex_count"] != current["vertex_count"]
        or original["face_count"] != current["face_count"]
        or original["unique_edge_count"] != current["unique_edge_count"]
    )

    if rough_change is None:
        rough_value = "N/A"
        rough_text = "Roughness needs comparable vertices with neighbor adjacency."
    else:
        rough_value = _format_percent(rough_change)
        rough_text = "Negative means vertices are closer to their neighbor averages."

    if metrics["bounding_box_percent_change"] is None:
        shrink_value = "N/A"
        shrink_text = "Bounding box change is unavailable for this mesh."
    else:
        shrink_value = f"{_format_percent(metrics['bounding_box_percent_change'])} bbox"
        shrink_text = "Negative means the mesh got smaller."

    if metrics["surface_area_percent_change"] is None:
        area_value = "N/A"
        area_text = "Surface area needs usable faces."
    else:
        area_value = _format_percent(metrics["surface_area_percent_change"])
        area_text = "Area often drops when smoothing removes detail."

    if metrics["average_displacement"] is None:
        movement_value = "N/A"
        movement_text = "Movement needs the same vertex count as the original."
    else:
        movement_value = _format_value(metrics["average_displacement"])
        movement_text = "Average distance each vertex moved from the original."

    topology_value = "Yes" if topology_changed else "No"
    topology_text = "Smoothing should move vertices without changing faces or edges."

    _metric_card("Roughness change", rough_value, rough_text)
    _metric_card("Shrinkage", shrink_value, shrink_text)
    _metric_card("Surface area change", area_value, area_text)
    _metric_card("Average movement", movement_value, movement_text)
    _metric_card("Topology changed?", topology_value, topology_text)


def _render_playground(working_mesh: MeshData, viewer_options: dict[str, object]) -> tuple[MeshData, dict[str, object]]:
    """Render the visual-first playground tab."""
    original_mesh = st.session_state[ORIGINAL_MESH_KEY]
    left_column, center_column, right_column = st.columns([0.29, 0.46, 0.25], gap="large")

    with left_column:
        controls = _render_playground_controls(working_mesh)
        active_mesh, preview_info = _build_preview_mesh(working_mesh, controls)
        _render_commit_controls(working_mesh, active_mesh, controls, preview_info)

    with center_column:
        st.markdown('<div class="sticky-preview-marker"></div>', unsafe_allow_html=True)
        _render_playground_viewer(original_mesh, active_mesh, controls, viewer_options)

    with right_column:
        _render_dynamic_explanation(working_mesh, controls, preview_info)
        _render_metric_cards(original_mesh, active_mesh)

    return active_mesh, controls


def _render_advanced_metrics_tab(mesh: MeshData, controls: dict[str, object] | None) -> None:
    """Render detailed committed-mesh metrics and summary."""
    st.subheader("Advanced Metrics")
    st.caption(
        "Detailed tables use the committed working mesh. Playground cards show the live preview."
    )
    _render_smoothing_metrics(
        st.session_state[ORIGINAL_MESH_KEY],
        mesh,
        st.session_state[SMOOTHING_STEPS_KEY],
    )
    _render_smoothing_history()
    if controls is None:
        controls = {
            "smoothing_mode": st.session_state.get(SMOOTHING_MODE_KEY, "Global smoothing"),
            "smoothing_method": st.session_state.get(SMOOTHING_METHOD_KEY, UNIFORM_LAPLACIAN),
            "smoothing_iterations": st.session_state.get(SMOOTHING_ITERATIONS_KEY, 1),
            "smoothing_strength": st.session_state.get(SMOOTHING_STRENGTH_KEY, 0.3),
            "preserve_boundary": st.session_state.get(PRESERVE_BOUNDARY_KEY, True),
        }
    _render_learning_summary(
        mesh,
        str(controls["smoothing_mode"]),
        str(controls["smoothing_method"]),
        int(controls["smoothing_iterations"]),
        float(controls["smoothing_strength"]),
        bool(controls["preserve_boundary"]),
    )


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Mesh Smoothing Lecture Lab",
        layout="wide",
    )
    _inject_layout_css()
    _ensure_ui_defaults()

    st.title("Mesh Smoothing Lecture Lab")
    st.caption(
        "A visual playground for mesh smoothing: change controls, watch the mesh update, "
        "then inspect the math and metrics when needed."
    )

    with st.sidebar:
        base_mesh, source_key = _render_mesh_source_sidebar()

    _sync_working_mesh(base_mesh, source_key)
    if st.session_state.pop(RESET_REQUESTED_KEY, False):
        _reset_experiment()

    working_mesh = _working_mesh()
    with st.sidebar:
        viewer_options = _render_viewer_sidebar(working_mesh)

    active_mesh: MeshData = working_mesh
    controls: dict[str, object] | None = None

    playground_tab, method_tab, inspector_tab, metrics_tab = st.tabs(LEARNING_TABS)

    with playground_tab:
        active_mesh, controls = _render_playground(working_mesh, viewer_options)

    with method_tab:
        _render_method_comparison_lab(_working_mesh())

    with inspector_tab:
        _render_step_inspector(_working_mesh())

    with metrics_tab:
        _render_advanced_metrics_tab(_working_mesh(), controls)


if __name__ == "__main__":
    main()
