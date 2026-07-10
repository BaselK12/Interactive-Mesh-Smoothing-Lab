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
    compute_soft_selection_weights,
    copy_with_vertices,
    compute_roughness_energy,
    find_boundary_vertices,
    graph_distances_from_vertex,
    inspect_cotangent_step,
    inspect_uniform_step,
    is_triangle_mesh,
    laplacian_smooth_local,
    taubin_stability,
)
from src.sample_meshes import create_sample_mesh, sample_mesh_names
from src.visualization import (
    DISPLAY_MODES,
    make_overlay_plotter,
    make_plotter,
    make_side_by_side_plotter,
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
PREVIEW_NOISY_STAGE_KEY = "preview_noisy_stage"
WORKING_VERSION_KEY = "working_mesh_version"
FLASH_MESSAGE_KEY = "flash_message"
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
PRESET_SOURCE_SWITCH_KEY = "preset_source_switch"
DEMO_MODIFIER_KEY = "demo_modifier"
DEMO_NONE = "None"
DEMO_GRID_BUMP = "Grid bump preview"
COMPARISON_INPUT_KEY = "method_comparison_input_choice"
ACTIVE_SECTION_KEY = "active_learning_section"
INSPECT_BOUNDARY_KEY = "inspect_preserve_boundary"
PLAYGROUND_COMPARISON_MODES = ["Overlay", "Side-by-side", "Original only", "Current only"]
LEARNING_SECTIONS = [
    "Playground",
    "Method Comparison",
    "Step Inspector",
    "Guided Learning",
    "Student Exercises",
    "Advanced Metrics",
]
SMOOTHING_MODES = ["Global smoothing", "Local / soft smoothing"]
FALLOFF_TYPES = ["linear", "smoothstep"]
TAUBIN_DEFAULT_MU = -0.53
TAUBIN_STABLE_LAMBDA = 0.5
LIVE_PREVIEW_VERTEX_LIMIT = 50000
LIVE_PREVIEW_WORK_LIMIT = 500000
ROUGHNESS_LABEL = "Roughness (mean neighbor distance)"
ROUGHNESS_CAPTION = (
    "Roughness here is the mean distance from each vertex to the average of its "
    "neighbors, in mesh length units. It is scale-dependent: uniformly shrinking "
    "a mesh also lowers this number, so always read it together with the size "
    "metrics."
)
COMPARISON_INPUT_WORKING = "Committed working mesh"
COMPARISON_INPUT_ORIGINAL = "Source original"
COMPARISON_INPUT_NOISY = "Noisy preview stage (before smoothing)"
COMPARISON_INPUT_PREVIEW = "Current live preview"


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
            "7. Local",
            "8. Compare",
        ]
    )

    steps = [
        (
            tabs[0],
            [
                "A mesh stores geometry (vertex positions) and connectivity (which vertices form each edge and face).",
                "The same connectivity can be drawn as points, wireframe, or shaded faces.",
            ],
            [
                "Set the Playground view to 'Current only', then switch Display mode in the sidebar.",
            ],
            [
                "Points show vertices.",
                "Wireframe shows edges.",
                "Solid view shows faces and surface shape.",
                "Changing the display never changes the mesh data itself.",
            ],
        ),
        (
            tabs[1],
            [
                "Connectivity answers 'which vertices touch this one?'",
                "The neighbors connected to a vertex by an edge form its one-ring.",
                "Smoothing is built entirely on these one-ring neighbor queries.",
            ],
            ["Open Step Inspector and pick any vertex to see its one-ring neighbors highlighted in orange."],
            ["Different meshes give the same vertex different neighbor counts (valence)."],
        ),
        (
            tabs[2],
            [
                "A face normal is the direction a face points; it follows the face's winding order.",
                "Vertex normals are estimated by averaging incident face normals (optionally weighted by face area).",
                "Degenerate (zero-area) faces have no meaningful normal and are skipped.",
            ],
            [
                "Set the Playground view to 'Current only' (normal overlays draw only in that view), then toggle face and vertex normals in the sidebar.",
            ],
            [
                "Cube face normals are faceted.",
                "Vertex normals approximate smoother orientation.",
            ],
        ),
        (
            tabs[3],
            [
                "One smoothing step moves each vertex toward the average position of its one-ring neighbors.",
                "For the Uniform neighbor-average step, lambda controls the fraction of that move (0 = no movement, 1 = all the way).",
                "All vertices update simultaneously from the old positions (a synchronous update).",
            ],
            ["Set smoothing iterations to 1 with lambda about 0.5."],
            ["Pointy or sharp regions relax first; in Uniform mode, lambda 0 moves nothing."],
        ),
        (
            tabs[4],
            [
                "Repeated neighbor averaging smooths the surface, but on closed shapes it usually also pulls vertices inward.",
                "Lower roughness alone is not success: a collapsing mesh also reports lower roughness because the metric has length units.",
            ],
            ["Use the 'See shrinkage' preset (14 Uniform iterations) and watch the Overlay."],
            ["The AABB-diagonal change becomes strongly negative. Check surface area and, when available, volume in Advanced Metrics separately."],
        ),
        (
            tabs[5],
            [
                "A boundary edge belongs to exactly one face; vertices on such edges form the open border.",
                "Preserving boundary vertices pins the border in place. It does not prevent the interior from moving or collapsing.",
            ],
            [
                "Use the 'Boundary preservation' preset, then toggle 'Preserve boundary vertices' off and on.",
            ],
            [
                "Off: the border slides inward.",
                "On: the border stays fixed while the interior bump relaxes.",
            ],
        ),
        (
            tabs[6],
            [
                "Local smoothing behaves like a soft brush centered on one vertex.",
                "Influence fades with graph distance: 1 graph step = crossing one edge.",
                "Vertices exactly at the chosen radius get weight 0 (the soft edge of the brush).",
            ],
            ["Use the Local soft smoothing preset and change the radius; at radius 3+ also switch the falloff curve."],
            [
                "The orange nonzero-weight region grows as the radius increases; the zero-weight radius ring is not highlighted or moved.",
                "Vertices outside the soft selection stay unchanged.",
            ],
        ),
        (
            tabs[7],
            [
                "Different smoothing methods trade roughness reduction against shape preservation differently.",
                "Taubin adds a negative correction step. A positive pass-band (lambda < |mu|) is useful, but the app also checks sampled gain; unsuitable pairs can expand the mesh.",
                "Cotangent weighting uses triangle geometry and is supported here only on triangle-only meshes.",
            ],
            ["Open Method Comparison, choose an input baseline, and run it."],
            [
                "Roughness reduction and size change do not always rank methods the same way.",
                "One Taubin iteration does two Laplacian passes, so equal iteration counts are not equal work.",
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
    """Render the suggested student workflow (matches the live-preview UI)."""
    st.subheader("How to use this lab")
    st.markdown(
        """
        1. In **Playground**, click the **See shrinkage** preset for your first experiment.
        2. Watch the Overlay: the black wireframe is the source original, the blue shaded
           surface is the live preview.
        3. Change **Smoothing iterations** and **lambda** and watch the preview and the
           metric strip under the viewer update immediately.
        4. Click **Commit preview as current mesh** only when you want the preview to
           become the committed working mesh (this is what Method Comparison and the
           Step Inspector read).
        5. Click **Reset experiment** at any time to return to the clean original.
        6. Then explore the other presets: noise removal, boundary preservation, and
           local soft smoothing.
        """
    )
    st.caption(
        "Lecture core ideas: mesh anatomy, connectivity, normals, neighbor-average "
        "smoothing, shrinkage, boundaries. Project extensions beyond the lecture: "
        "Taubin smoothing, cotangent weighting, synthetic noise, and the numeric "
        "metrics."
    )


def _render_guided_learning_tab() -> None:
    """Render the guided learning content."""
    _render_how_to_use_lab()
    st.divider()
    _render_guided_walkthrough()
    st.divider()
    with st.expander("Key terms (quick reference)", expanded=False):
        _render_lecture_concept_cards()


def _render_student_exercises() -> None:
    """Render the in-app exercise set from the student guide."""
    st.subheader("Student Exercises")
    st.caption(
        "Each exercise is short: set up the mesh, make one change, then check the viewer and metric cards."
    )
    exercises = [
        (
            "Exercise 1 - Topology counts stay fixed",
            "Load Cube. Set Uniform Laplacian, 5 iterations, then Commit the preview.",
            "Vertex, face, and edge counts stay fixed while geometry moves.",
            "Smoothing changes positions, not connectivity.",
        ),
        (
            "Exercise 2 - Shrinkage",
            "Click the 'See shrinkage' preset (Low-poly sphere, 14 Uniform iterations, lambda 0.5).",
            "The AABB diagonal drops sharply in the metric strip; the Overlay shows the preview inside the original wireframe. Surface area is listed under More metrics.",
            "Repeated averaging pulls closed shapes inward.",
        ),
        (
            "Exercise 3 - Boundary preservation",
            "Use the 'Boundary preservation' preset. Toggle 'Preserve boundary vertices' off and on.",
            "The grid border moves when preservation is off and stays pinned when it is on ('Boundary moved?' card flips).",
            "Boundary edges belong to only one face, so open meshes need special handling.",
        ),
        (
            "Exercise 4 - Noise removal",
            "Click the 'Remove noise' preset, then read the clean -> noisy -> smoothed roughness line in the explanation panel.",
            "The smoothed roughness is well below the noisy stage and close to the clean value, while the size stays similar. Now try lambda 0.2: the pair becomes unstable and the app warns.",
            "Denoising is a tradeoff between smoothing away noise and preserving shape. Lambda < |mu| gives a positive pass-band, but use the app's sampled-gain warning rather than treating that condition alone as stable.",
        ),
        (
            "Exercise 5 - Method comparison",
            "Click 'Uniform vs Taubin', open Method Comparison, set the comparison input to 'Noisy preview stage (before smoothing)', and run it.",
            "All methods start from the same noisy sphere. At the shown settings, compare the displayed AABB changes: Uniform is more negative while Taubin is closer to the input size.",
            "A fair comparison needs the same input; even then, equal iterations are not equal work.",
        ),
        (
            "Exercise 6 - Local soft smoothing",
            "Use 'Local soft smoothing'. Try radius 1, then radius 3, and at radius 3 switch the falloff curve.",
            "The orange nonzero-weight region and the ring-weight table grow with radius; the falloff choice changes the middle-ring weights only at radius 3 or more.",
            "Soft selection localizes edits through graph distance; the outer radius ring has weight 0, so it is neither moved nor included in the orange highlight.",
        ),
        (
            "Exercise 7 - Step inspector",
            "Open Step Inspector on Plane/grid. Inspect vertex 0 (a corner), then an interior vertex like 12.",
            "The corner is reported as a pinned boundary vertex (no motion) while the interior vertex moves toward its neighbor average.",
            "The inspector shows the real update rule when its boundary checkbox matches the smoothing operation.",
        ),
    ]
    for title, setup, expected, why in exercises:
        with st.expander(title, expanded=False):
            st.markdown(f"**Try:** {setup}")
            st.markdown(f"**Expected:** {expected}")
            st.markdown(f"**Why:** {why}")


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
    st.caption("Soft selection region summary (1 graph step = crossing one edge)")
    st.table(
        [
            {"Metric": "Center vertex", "Value": str(summary["center_vertex"])},
            {"Metric": "Graph radius", "Value": str(summary["radius"])},
            {"Metric": "Falloff", "Value": str(summary["falloff"])},
            {"Metric": "Nonzero-weight vertices", "Value": str(summary["affected_vertices"])},
            {
                "Metric": "Movable nonzero-weight vertices",
                "Value": str(summary["movable_affected_vertices"]),
            },
            {
                "Metric": "Farthest nonzero-weight distance",
                "Value": _format_value(summary["max_graph_distance_included"], digits=0),
            },
        ]
    )
    st.table(_soft_selection_ring_rows(soft_radius, falloff_type))
    st.caption(
        "Vertices exactly at the radius get weight 0 (the soft edge of the brush), "
        "so they do not move and are not included in the orange nonzero-weight highlight."
    )


def _soft_selection_ring_rows(radius: int, falloff_type: str) -> list[dict[str, str]]:
    """Build the weight-per-graph-distance rows for the current falloff."""
    rows: list[dict[str, str]] = []
    safe_radius = max(1, int(radius))
    for distance in range(0, min(safe_radius, 6) + 1):
        t = distance / safe_radius
        if falloff_type == "smoothstep":
            weight = 1.0 - (3.0 * t**2 - 2.0 * t**3)
        else:
            weight = max(0.0, 1.0 - t)
        rows.append(
            {
                "Graph distance": str(distance),
                "Weight": f"{weight:.3f}",
            }
        )
    return rows


def _render_mesh_plotter(
    mesh: MeshData,
    display_mode: str,
    background_color: str,
    show_axes: bool,
    window_size: tuple[int, int],
    highlight_vertices: list[int] | None = None,
    center_vertex: int | None = None,
) -> None:
    """Render one mesh viewer without normal overlays."""
    plotter = make_plotter(
        mesh,
        display_mode=display_mode,
        background_color=background_color,
        show_axes=show_axes,
        window_size=window_size,
        highlight_vertices=highlight_vertices,
        center_vertex=center_vertex,
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

    st.subheader("Committed-Mesh Observation Metrics")
    st.caption(
        "Baseline: source original -> committed working mesh. Counts show only "
        "topology counts; geometric values may reflect noise, the teaching bump, "
        "or smoothing as well as size and shape change."
    )

    st.metric("Committed smoothing iterations (requested)", smoothing_steps)
    st.caption(
        "This is the cumulative requested iteration count for committed smoothing "
        "actions; a Taubin iteration contains two Laplacian passes, and noise is not counted."
    )

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
    st.caption(
        "Displacements are distances in mesh length units from the source original "
        "to the committed working mesh and require matching vertex indices."
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
    st.caption(
        "AABB values use mesh length units, area uses squared mesh units, and "
        "volume uses cubed mesh units; area and volume use fan-triangulated faces. "
        "Volume is shown only when Trimesh reports a watertight, winding-consistent, "
        "nonzero-volume mesh; it is an aggregate signed-volume magnitude, so "
        "disconnected components with opposing orientation can still cancel."
    )

    _render_roughness_metrics(original_mesh, current_mesh)


def _render_roughness_metrics(original_mesh: MeshData, current_mesh: MeshData) -> None:
    """Render the neighbor-distance roughness metric for original vs current."""
    original_roughness = compute_roughness_energy(original_mesh)
    current_roughness = compute_roughness_energy(current_mesh)

    st.markdown(f"**{ROUGHNESS_LABEL}**")
    st.caption(ROUGHNESS_CAPTION)
    if original_roughness["mean"] is None and current_roughness["mean"] is None:
        st.caption("Roughness is N/A: no vertex adjacency is available.")
        return

    roughness_rows = [
        {
            "Metric": "Mean neighbor distance",
            "Original": _format_value(original_roughness["mean"]),
            "Current": _format_value(current_roughness["mean"]),
            "Change": _format_percent(
                _percent_change(original_roughness["mean"], current_roughness["mean"])
            ),
        },
        {
            "Metric": "Max neighbor distance",
            "Original": _format_value(original_roughness["max"]),
            "Current": _format_value(current_roughness["max"]),
            "Change": _format_percent(
                _percent_change(original_roughness["max"], current_roughness["max"])
            ),
        },
        {
            "Metric": "RMS neighbor distance",
            "Original": _format_value(original_roughness["rms"]),
            "Current": _format_value(current_roughness["rms"]),
            "Change": _format_percent(
                _percent_change(original_roughness["rms"], current_roughness["rms"])
            ),
        },
    ]
    st.table(roughness_rows)
    st.caption(
        "A method can lower this metric while also shrinking the mesh (collapse "
        "is not good smoothing). Always compare with the bounding-box and "
        "surface-area changes above."
    )


def _render_smoothing_history() -> None:
    """Render smoothing history as a table and compact trend chart."""
    st.subheader("Committed Action History")
    history = st.session_state.get(SMOOTHING_HISTORY_KEY, [])
    if not history:
        st.info("Commit a preview, add noise, or apply smoothing to start the history table.")
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
    noise_strength: float | None = None,
    noise_seed: int | None = None,
    noise_mode: str | None = None,
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
            "Noise strength": noise_strength,
            "Noise seed": noise_seed,
            "Noise mode": noise_mode,
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
                "Each step moves every vertex toward the average of its one-ring neighbors.",
                "All vertices update simultaneously from the old positions (synchronous update).",
                "For this neighbor-average step, lambda controls the fraction of the move (0 = none, 1 = all the way).",
                "More iterations relax the surface further, and on closed shapes usually shrink it too.",
            ],
        ),
        (
            "Shrinkage",
            [
                "Repeated averaging often pulls vertices inward on closed shapes.",
                "Sharp details relax, but the overall shape can get smaller.",
                "The roughness metric also falls when the whole mesh shrinks, so read it with the size metrics.",
            ],
        ),
        (
            "Boundary Preservation",
            [
                "A boundary edge belongs to only one face.",
                "Boundary vertices sit on the open border of a mesh.",
                "Preserving them pins the border in place; the interior can still move or collapse.",
                "Try this on the plane/grid with the Boundary preservation preset.",
            ],
        ),
    ]

    left_column, right_column = st.columns(2)
    for index, (title, bullets) in enumerate(concept_cards):
        column = left_column if index % 2 == 0 else right_column
        with column:
            with st.expander(title, expanded=index == 0):
                st.markdown("\n".join(f"- {bullet}" for bullet in bullets))


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
        "Noise strength": _format_value(row.get("Noise strength"), digits=2),
        "Noise seed": _format_optional_int(row.get("Noise seed")),
        "Noise mode": row.get("Noise mode") or "N/A",
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


def _bump_working_version() -> None:
    """Advance the working-mesh version counter used for staleness checks."""
    st.session_state[WORKING_VERSION_KEY] = int(st.session_state.get(WORKING_VERSION_KEY, 0)) + 1


def _clear_method_comparison() -> None:
    """Discard comparison snapshots after their working-state baseline changes."""
    for key in (
        "method_comparison_rows",
        "method_comparison_input_mesh",
        "method_comparison_input_label",
    ):
        st.session_state.pop(key, None)


def _sync_working_mesh(base_mesh: MeshData, source_key: str) -> None:
    """Reset original/working meshes whenever the selected source changes."""
    if st.session_state.get(MESH_SOURCE_KEY) == source_key:
        # A preset can request a reset without changing its source.  Consume
        # this one-shot marker here so it cannot leak into a later *manual*
        # source switch and preserve active experiment controls by mistake.
        st.session_state.pop(PRESET_SOURCE_SWITCH_KEY, None)
        st.session_state.setdefault(SMOOTHING_HISTORY_KEY, [])
        st.session_state.setdefault(NOISE_APPLIED_KEY, False)
        st.session_state.setdefault(NOISE_INFO_KEY, None)
        st.session_state.setdefault(PREVIEW_MESH_KEY, None)
        st.session_state.setdefault(PREVIEW_NOISY_STAGE_KEY, None)
        st.session_state.setdefault(INSPECT_VERTEX_KEY, 0)
        return

    from_preset = bool(st.session_state.pop(PRESET_SOURCE_SWITCH_KEY, False))
    first_load = st.session_state.get(MESH_SOURCE_KEY) is None

    st.session_state[MESH_SOURCE_KEY] = source_key
    st.session_state[ORIGINAL_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[WORKING_MESH_KEY] = clone_mesh(base_mesh)
    st.session_state[SMOOTHING_STEPS_KEY] = 0
    st.session_state[SMOOTHING_HISTORY_KEY] = []
    default_center = _nearest_mesh_center_vertex(base_mesh)
    requested_center = st.session_state.get(LOCAL_CENTER_KEY, default_center)
    try:
        requested_center = int(requested_center)
    except (TypeError, ValueError):
        requested_center = default_center
    if not from_preset:
        requested_center = default_center
    center_limit = max(0, base_mesh.vertex_count - 1)
    local_center = min(max(0, requested_center), center_limit)
    st.session_state[LOCAL_CENTER_KEY] = local_center

    requested_radius = st.session_state.get(LOCAL_RADIUS_KEY, 2)
    try:
        requested_radius = int(requested_radius)
    except (TypeError, ValueError):
        requested_radius = 2
    if not from_preset:
        requested_radius = 2
    max_radius = max(1, _max_graph_radius(base_mesh, local_center))
    st.session_state[LOCAL_RADIUS_KEY] = min(max(1, requested_radius), max_radius)
    st.session_state[PREVIEW_MESH_KEY] = None
    st.session_state[PREVIEW_NOISY_STAGE_KEY] = None
    st.session_state[NOISE_APPLIED_KEY] = False
    st.session_state[NOISE_INFO_KEY] = None
    st.session_state[INSPECT_VERTEX_KEY] = 0
    _clear_method_comparison()
    _bump_working_version()

    # A manual source switch starts the new mesh in a neutral experiment state
    # so stale noise/smoothing settings cannot silently transform it. Presets
    # intentionally carry their own control values, so they skip this.
    if not from_preset and not first_load:
        st.session_state[NOISE_ENABLED_KEY] = False
        st.session_state[SMOOTHING_ITERATIONS_KEY] = 0
        st.session_state[DEMO_MODIFIER_KEY] = DEMO_NONE
        st.session_state[PRESET_MESSAGE_KEY] = ""
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "New mesh source loaded. Noise and smoothing controls were reset to "
            "neutral so the first view is the unmodified mesh.",
        )


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
                    "Topology counts changed?": "no",
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
                "Topology counts changed?": "yes" if topology_changed else "no",
                "Result mesh": clone_mesh(result.mesh),
            }
        )
    return rows


def _comparison_input_candidates(working_mesh: MeshData) -> dict[str, MeshData]:
    """Return the named input meshes the comparison can start from."""
    candidates: dict[str, MeshData] = {
        COMPARISON_INPUT_WORKING: working_mesh,
        COMPARISON_INPUT_ORIGINAL: st.session_state[ORIGINAL_MESH_KEY],
    }
    noisy_stage = st.session_state.get(PREVIEW_NOISY_STAGE_KEY)
    if isinstance(noisy_stage, MeshData) and noisy_stage.valid:
        candidates[COMPARISON_INPUT_NOISY] = noisy_stage
    preview = st.session_state.get(PREVIEW_MESH_KEY)
    if (
        isinstance(preview, MeshData)
        and preview.valid
        and not _meshes_have_same_vertices(preview, working_mesh)
    ):
        candidates[COMPARISON_INPUT_PREVIEW] = preview
    return candidates


def _render_method_comparison_lab(working_mesh: MeshData) -> None:
    """Render the method comparison lab with an explicit, named input baseline."""
    st.subheader("Smoothing Method Comparison")
    st.markdown(
        """
        Run every available smoothing method on the **same** starting mesh and
        compare the results side by side. Pick the input baseline explicitly, so
        you always know what the methods started from.

        This comparison does **not** change your current working mesh.
        """
    )

    candidates = _comparison_input_candidates(working_mesh)
    options = list(candidates.keys())
    current_choice = st.session_state.get(COMPARISON_INPUT_KEY)
    if current_choice not in options:
        current_choice = options[0]
        st.session_state[COMPARISON_INPUT_KEY] = current_choice
    # Pass index= explicitly: this radio is only mounted once the user
    # navigates to this section (lazy rendering), so on its first-ever mount
    # in the browser it may carry a session_state value set by an earlier
    # preset click. Relying on key= alone to seed the visual selection is not
    # reliable for a widget mounted for the first time with a pre-set value;
    # index= makes the rendered selection match the value deterministically.
    input_label = st.radio(
        "Comparison input",
        options,
        index=options.index(current_choice),
        key=COMPARISON_INPUT_KEY,
        horizontal=True,
        help=(
            "'Noisy preview stage' appears when the Playground preview currently "
            "includes noise: it is the noisy mesh before smoothing, which is the "
            "right input for a denoising comparison."
        ),
    )
    selected_input = candidates[input_label]
    input_roughness = compute_roughness_energy(selected_input)["mean"]
    st.caption(
        f"Selected input: **{input_label}** — {selected_input.vertex_count} vertices, "
        f"{ROUGHNESS_LABEL.lower()} {_format_value(input_roughness)}."
    )

    columns = st.columns(4)
    comp_iterations = columns[0].slider("Comparison iterations", 1, 30, 10, key="comp_iters")
    comp_lambda = columns[1].slider("Comparison lambda", 0.0, 1.0, 0.5, 0.05, key="comp_lambda")
    comp_mu = columns[2].slider("Comparison Taubin mu", -0.95, -0.05, TAUBIN_DEFAULT_MU, 0.01, key="comp_mu")
    comp_boundary = columns[3].checkbox("Preserve boundary", value=True, key="comp_boundary")
    comp_stability = taubin_stability(comp_lambda, comp_mu)
    if not comp_stability["stable"]:
        st.warning(
            f"The Taubin pair lambda={comp_lambda:.2f}, mu={comp_mu:.2f} amplifies some "
            f"frequencies (max gain {comp_stability['max_gain']:.3f} per iteration), so its "
            "row may expand instead of smoothing. Lambda < |mu| gives a positive pass-band "
            "but is not sufficient by itself; lambda=0.5, mu=-0.53 passes this app's "
            "sampled-gain check."
        )

    if st.button("Run comparison from the selected input"):
        if not selected_input.valid:
            st.error("The selected input mesh is not valid; comparison is unavailable.")
            return
        comparison_input = clone_mesh(selected_input)
        st.session_state["method_comparison_rows"] = _run_method_comparison(
            comparison_input,
            iterations=comp_iterations,
            lam=comp_lambda,
            mu=comp_mu,
            preserve_boundary=comp_boundary,
        )
        st.session_state["method_comparison_input_mesh"] = comparison_input
        st.session_state["method_comparison_input_label"] = input_label

    rows = st.session_state.get("method_comparison_rows")
    if not rows:
        st.info("Press 'Run comparison from the selected input' to build the comparison table.")
        return

    comparison_input = st.session_state.get("method_comparison_input_mesh")
    stored_label = str(st.session_state.get("method_comparison_input_label", COMPARISON_INPUT_WORKING))
    stored_candidate = candidates.get(stored_label)
    if comparison_input is not None:
        if stored_candidate is None or not _meshes_have_same_vertices(comparison_input, stored_candidate):
            st.warning(
                f"These stored results describe an earlier snapshot of '{stored_label}'. "
                "The mesh has changed since the comparison ran — re-run it to compare "
                "the current state."
            )
        stored_roughness = compute_roughness_energy(comparison_input)["mean"]
        st.caption(
            f"Results below start from the stored snapshot of **{stored_label}** "
            f"({ROUGHNESS_LABEL.lower()} {_format_value(stored_roughness)})."
        )
        _render_method_comparison_visuals(comparison_input, rows)

    st.table([_format_comparison_row(row) for row in rows])
    _render_comparison_observations(rows)
    st.caption(
        "Displacement, AABB, area, and volume changes use the stored comparison "
        "input as baseline. Distances use mesh length units; area and volume use "
        "squared and cubed mesh units. Positive roughness reduction means this "
        "scale-dependent residual fell; it is not a quality ranking. Volume is N/A "
        "unless Trimesh reports a watertight, winding-consistent, nonzero-volume "
        "mesh. One Taubin iteration performs two Laplacian passes, so equal iteration "
        "counts are the same input, not equal work."
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
        "Topology counts changed?": row["Topology counts changed?"],
    }


def _render_comparison_observations(rows: list[dict[str, object]]) -> None:
    """Render literal, metric-named observations instead of winner rankings."""
    supported = [row for row in rows if row["Status"] == "ok"]
    unsupported = [row for row in rows if row["Status"] != "ok"]
    notes: list[str] = []

    def _abs_bbox(row: dict[str, object]) -> float:
        value = row["BBox change (%)"]
        return abs(float(value)) if value is not None else float("inf")

    if supported:
        sizes = [row for row in supported if row["BBox change (%)"] is not None]
        if sizes:
            smallest = min(sizes, key=_abs_bbox)
            notes.append(
                f"**Smallest absolute AABB-diagonal change:** {smallest['Method']} "
                f"({_format_percent(smallest['BBox change (%)'])}). Note: a large "
                "*positive* change means expansion, which is not shape preservation."
            )
        reducers = [
            row
            for row in supported
            if row["Roughness reduction (%)"] is not None and float(row["Roughness reduction (%)"]) > 0.0
        ]
        if reducers:
            reducers.sort(key=lambda row: float(row["Roughness reduction (%)"]), reverse=True)
            listing = ", ".join(
                f"{row['Method']} ({_format_percent(row['Roughness reduction (%)'])})"
                for row in reducers
            )
            notes.append(f"**Methods that reduced roughness on this input:** {listing}.")
        else:
            notes.append(
                "**No method reduced roughness on this input with these settings.** "
                "Try different iterations/lambda before drawing conclusions."
            )
        notes.append(
            "These observations describe this input and these settings only; they "
            "are not general method rankings."
        )
    for row in unsupported:
        notes.append(f"**Unsupported for this mesh:** {row['Method']} — {row['Notes']}")

    if notes:
        st.markdown("\n".join(f"- {note}" for note in notes))


def _render_step_inspector(mesh: MeshData) -> None:
    """Render the one-step smoothing computation inspector."""
    st.subheader("Smoothing Step Inspector")
    st.markdown(
        """
        Inspect what happens to **one vertex** during a single smoothing step,
        including the boundary-pinning rule selected for this inspection. Each
        movable vertex moves toward the (weighted) average of its neighbors.
        """
    )
    st.caption(
        "The inspector shows one Uniform or Cotangent step with synchronous "
        "updates (every vertex reads its neighbors' OLD positions). Set the "
        "boundary checkbox to the setting you want to model; Taubin's second "
        "negative pass and local soft weights are not shown here."
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
    st.session_state.setdefault(
        INSPECT_BOUNDARY_KEY, bool(st.session_state.get(PRESERVE_BOUNDARY_KEY, True))
    )
    inspect_boundary = st.checkbox(
        "Preserve boundary vertices for this inspection",
        key=INSPECT_BOUNDARY_KEY,
        help=(
            "When on, boundary vertices are pinned exactly as the smoothing "
            "algorithms pin them. Set it to the same choice as the smoothing "
            "operation when comparing this prediction with that operation."
        ),
    )

    if inspect_method == "Cotangent weights":
        _render_cotangent_inspection(mesh, vertex_index, inspect_lambda, inspect_boundary)
    else:
        _render_uniform_inspection(mesh, vertex_index, inspect_lambda, inspect_boundary)


def _render_pinned_banner(info: dict[str, object]) -> None:
    """Explain the boundary status of the inspected vertex."""
    if info.get("pinned"):
        st.warning(
            f"Vertex {info['vertex_index']} is a **boundary vertex** and boundary "
            "preservation is ON, so smoothing pins it: **predicted movement is "
            "zero** and the predicted position equals the current position. The "
            "unconstrained target below is shown for reference only."
        )
    elif info.get("is_boundary_vertex"):
        st.info(
            f"Vertex {info['vertex_index']} is a boundary vertex, but boundary "
            "preservation is OFF here, so it moves like any other vertex."
        )


def _render_uniform_inspection(
    mesh: MeshData, vertex_index: int, lam: float, preserve_boundary: bool
) -> None:
    """Render the uniform one-step computation for a single vertex."""
    info = inspect_uniform_step(mesh, vertex_index, lam=lam, preserve_boundary=preserve_boundary)
    st.markdown(
        f"**Vertex {info['vertex_index']}** — valence (neighbor count): "
        f"**{info['valence']}**"
    )
    _render_pinned_banner(info)
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

    quantity_rows = [
        {"Quantity": "Neighbor average", "Value": _format_vector(info["neighbor_average"])},
        {"Quantity": "Displacement (avg - current)", "Value": _format_vector(info["displacement"])},
        {"Quantity": "Lambda", "Value": _format_value(info["lambda"], digits=2)},
    ]
    if info.get("pinned"):
        quantity_rows.append(
            {
                "Quantity": "Unconstrained target (reference only)",
                "Value": _format_vector(info.get("unconstrained_position")),
            }
        )
    quantity_rows.append(
        {
            "Quantity": "Predicted new position (one step)",
            "Value": _format_vector(info["predicted_position"]),
        }
    )
    st.table(quantity_rows)
    if info.get("pinned"):
        st.caption("Pinned boundary vertex: predicted position = current position.")
    else:
        st.caption("Predicted position = current + lambda x (neighbor average - current).")


def _render_cotangent_inspection(
    mesh: MeshData, vertex_index: int, strength: float, preserve_boundary: bool
) -> None:
    """Render the cotangent-weighted one-step computation for a single vertex."""
    info = inspect_cotangent_step(
        mesh, vertex_index, strength=strength, preserve_boundary=preserve_boundary
    )
    if not info.get("supported"):
        st.warning(info.get("note", "Cotangent weights are unavailable for this mesh."))
        return

    st.markdown(f"**Vertex {info['vertex_index']}** cotangent-weighted neighborhood")
    _render_pinned_banner(info)
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
    quantity_rows = [
        {"Quantity": "Sum of weights", "Value": _format_value(info["weight_sum"], digits=4)},
        {"Quantity": "Weighted target", "Value": _format_vector(info["weighted_target"])},
        {"Quantity": "Strength", "Value": _format_value(info["strength"], digits=2)},
    ]
    if info.get("pinned"):
        quantity_rows.append(
            {
                "Quantity": "Unconstrained target (reference only)",
                "Value": _format_vector(info.get("unconstrained_position")),
            }
        )
    quantity_rows.append(
        {
            "Quantity": "Predicted new position (one step)",
            "Value": _format_vector(info["predicted_position"]),
        }
    )
    st.table(quantity_rows)
    if info.get("note"):
        st.caption(info["note"])
    st.caption(
        "Cotangent smoothing weights neighbors using the starting triangle "
        "geometry (weights are computed once and reused across iterations), so "
        "the target is a weighted average rather than a plain average."
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


def _last_committed_action_rows(history: list[dict[str, object]]) -> list[dict[str, str]]:
    """Build the settings table from the last committed history action."""
    if not history:
        return [
            {
                "Setting": "Last committed action",
                "Value": "None yet - commit a preview or apply an action first",
            }
        ]
    last = history[-1]
    rows = [
        {"Setting": "Last committed action", "Value": str(last.get("Action", "Smoothing"))},
        {"Setting": "Method", "Value": str(last.get("Method", "N/A"))},
        {"Setting": "Mode", "Value": str(last.get("Mode", "Global"))},
        {"Setting": "Lambda", "Value": _format_value(last.get("Lambda"), digits=2)},
        {"Setting": "Taubin mu", "Value": _format_value(last.get("Mu"), digits=2)},
        {"Setting": "Preserve boundary", "Value": str(last.get("Preserve boundary"))},
        {"Setting": "Total committed iterations", "Value": str(last.get("Total iterations"))},
    ]
    if last.get("Center vertex") is not None:
        rows.append({"Setting": "Local center vertex", "Value": str(last.get("Center vertex"))})
        rows.append({"Setting": "Local radius", "Value": str(last.get("Soft radius"))})
        rows.append({"Setting": "Local falloff", "Value": str(last.get("Falloff") or "N/A")})
    if last.get("Noise strength") is not None:
        rows.append(
            {
                "Setting": "Noise strength",
                "Value": _format_value(last.get("Noise strength"), digits=2),
            }
        )
        rows.append(
            {
                "Setting": "Noise seed",
                "Value": _format_optional_int(last.get("Noise seed")),
            }
        )
        rows.append(
            {
                "Setting": "Noise mode",
                "Value": str(last.get("Noise mode") or "N/A"),
            }
        )
    return rows


def _render_learning_summary(mesh: MeshData) -> None:
    """Render the learning summary and Markdown download from committed state.

    Every value comes from the committed working mesh and the committed action
    history. Current uncommitted widget positions are deliberately excluded so a
    downloaded report can never attribute settings to geometry they did not
    produce.
    """
    st.subheader("Learning Summary")
    st.markdown(
        "A snapshot of the **committed** experiment (working mesh + committed "
        "action history). Uncommitted preview controls are not included."
    )

    original_mesh = st.session_state[ORIGINAL_MESH_KEY]
    total_iterations = st.session_state[SMOOTHING_STEPS_KEY]
    metrics = compare_meshes(original_mesh, mesh, smoothing_iterations=total_iterations)
    current = metrics["current"]
    roughness_current = compute_roughness_energy(mesh)["mean"]
    roughness_original = compute_roughness_energy(original_mesh)["mean"]
    history = list(st.session_state.get(SMOOTHING_HISTORY_KEY, []))

    settings_rows = [
        {"Setting": "Mesh", "Value": mesh.name},
        {"Setting": "Summary state", "Value": "Committed working mesh"},
        {"Setting": "Mesh type", "Value": mesh.mesh_type},
        {
            "Setting": "Noise committed",
            "Value": ("yes" if st.session_state.get(NOISE_APPLIED_KEY) else "no"),
        },
    ] + _last_committed_action_rows(history)
    st.table(settings_rows)

    interpretation = _build_interpretation(metrics, roughness_original, roughness_current)
    st.markdown(interpretation)

    markdown = _build_summary_markdown(
        mesh,
        total_iterations,
        metrics,
        roughness_original,
        roughness_current,
        current,
        history,
    )
    st.download_button(
        "Download committed experiment summary (.md)",
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
        parts.append(
            f"Mean neighbor distance (roughness) decreased by {abs(reduction):.1f}% versus the source original."
        )
    elif reduction > 0:
        parts.append(
            f"Mean neighbor distance (roughness) increased by {reduction:.1f}% versus the source original."
        )
    else:
        parts.append("Mean neighbor distance (roughness) is unchanged versus the source original.")

    bbox = metrics["bounding_box_percent_change"]
    if bbox is not None:
        if bbox < -0.05:
            parts.append(f"The AABB diagonal shrank by {abs(bbox):.1f}%.")
        elif bbox > 0.05:
            parts.append(f"The AABB diagonal grew by {bbox:.1f}%.")
        else:
            parts.append("The AABB diagonal is essentially unchanged.")
    if reduction is not None and bbox is not None and reduction < 0 and bbox < -1.0:
        parts.append(
            "Part of the roughness drop comes from the size change itself, because "
            "the metric has length units."
        )
    return "**Interpretation:** " + " ".join(parts)


def _build_summary_markdown(
    mesh: MeshData,
    total_iterations: int,
    metrics: dict[str, object],
    roughness_original: float | None,
    roughness_current: float | None,
    current: dict[str, object],
    history: list[dict[str, object]],
) -> str:
    """Build the downloadable Markdown summary from committed state only."""
    lines = [
        "# Mesh Smoothing Learning Summary",
        "",
        "All settings below come from the committed action history; geometry and",
        "metrics come from the committed working mesh. Uncommitted preview",
        "controls are not included.",
        "",
        "## Committed experiment settings",
        f"- Mesh: {mesh.name}",
        "- Summary state: committed working mesh",
        f"- Mesh type: {mesh.mesh_type}",
        f"- Total committed smoothing iterations (requested): {total_iterations}",
    ]
    for row in _last_committed_action_rows(history):
        lines.append(f"- {row['Setting']}: {row['Value']}")
    lines += [
        "",
        "## Metrics (source original vs committed working mesh)",
        "| Metric | Original | Current | Change |",
        "| --- | --- | --- | --- |",
        f"| Vertices | {metrics['original']['vertex_count']} | {current['vertex_count']} | "
        f"{current['vertex_count'] - metrics['original']['vertex_count']} |",
        f"| Faces | {metrics['original']['face_count']} | {current['face_count']} | "
        f"{current['face_count'] - metrics['original']['face_count']} |",
        f"| AABB (bounding box) diagonal | {_format_value(metrics['original']['bounding_box_diagonal'])} | "
        f"{_format_value(current['bounding_box_diagonal'])} | {_format_percent(metrics['bounding_box_percent_change'])} |",
        f"| Surface area | {_format_value(metrics['original']['surface_area'])} | "
        f"{_format_value(current['surface_area'])} | {_format_percent(metrics['surface_area_percent_change'])} |",
        f"| Volume | {_format_value(metrics['original']['volume'])} | "
        f"{_format_value(current['volume'])} | {_format_percent(metrics['volume_percent_change'])} |",
        f"| Roughness (mean neighbor distance) | {_format_value(roughness_original)} | "
        f"{_format_value(roughness_current)} | {_format_percent(_percent_change(roughness_original, roughness_current))} |",
        "",
        "## Committed action history",
    ]
    if history:
        lines.append(
            "| Step | Action | Method | Total iters | Lambda | Mu | Noise strength | Noise seed | Noise mode | Rough before | Rough after | BBox change |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for row in history:
            lines.append(
                f"| {row['Step']} | {row.get('Action', 'Smoothing')} | {row.get('Method', 'N/A')} | "
                f"{row['Total iterations']} | {_format_value(row['Lambda'], digits=2)} | "
                f"{_format_value(row.get('Mu'), digits=2)} | "
                f"{_format_value(row.get('Noise strength'), digits=2)} | "
                f"{_format_optional_int(row.get('Noise seed'))} | "
                f"{row.get('Noise mode') or 'N/A'} | "
                f"{_format_value(row.get('Roughness before'))} | {_format_value(row.get('Roughness after'))} | "
                f"{_format_percent(row['Bounding box change (%)'])} |"
            )
    else:
        lines.append("No committed actions recorded yet.")
    lines += [
        "",
        "## What the metrics mean",
        "- **Roughness (mean neighbor distance)**: average distance from each vertex to the "
        "average of its neighbors, in mesh length units. It is scale-dependent: uniformly "
        "shrinking a mesh also lowers it, so read it together with the size metrics.",
        "- **AABB diagonal**: an axis-aligned size proxy in mesh length units; its percentage "
        "change is relative to the source original, not a full shape measure.",
        "- **Surface area**: fan-triangulated area in squared mesh units. It can change for "
        "many reasons and is not a direct detail-removed or size score.",
        "- **Volume**: an aggregate signed-volume magnitude after fan triangulation. It is shown "
        "only when Trimesh reports a watertight, winding-consistent, nonzero-volume mesh.",
        "- **Displacement**: per-vertex distance in mesh length units from the source original "
        "(same vertex indices).",
        "- History roughness before/after compares the mesh immediately before and after each "
        "committed action; size metrics compare against the source original.",
        "",
        "## Limitations",
        "- Uniform Laplacian smoothing usually shrinks closed meshes.",
        "- Taubin can reduce shrinkage for parameter pairs that pass this app's sampled-gain "
        "check. Lambda < |mu| gives a positive pass-band but is not sufficient by itself; "
        "unsuitable pairs can expand or destabilize the mesh.",
        "- Cotangent smoothing supports triangle meshes only; this implementation freezes the "
        "weights at the starting geometry and clamps negative weights (a teaching simplification).",
        "- The volume gate does not validate outward orientation of each disconnected component; "
        "oppositely oriented components can cancel in the aggregate value.",
        "- Local soft regions use graph distance (edge hops), not Euclidean distance; vertices "
        "exactly at the radius have zero weight and are not included in the orange highlight.",
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
        SMOOTHING_ITERATIONS_KEY: 0,
        SMOOTHING_STRENGTH_KEY: 0.3,
        SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
        PRESERVE_BOUNDARY_KEY: True,
        TAUBIN_MU_KEY: TAUBIN_DEFAULT_MU,
        FALLOFF_TYPE_KEY: "linear",
        PLAYGROUND_COMPARISON_KEY: "Current only",
        PRESET_MESSAGE_KEY: "",
        RESET_REQUESTED_KEY: False,
        PRESET_SOURCE_SWITCH_KEY: False,
        DEMO_MODIFIER_KEY: DEMO_NONE,
        WORKING_VERSION_KEY: 0,
        ACTIVE_SECTION_KEY: LEARNING_SECTIONS[0],
        COMPARISON_INPUT_KEY: COMPARISON_INPUT_WORKING,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _inject_layout_css() -> None:
    """Add layout rules: sticky viewer column and a responsive stacking breakpoint."""
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
        /* Keep button labels from breaking mid-word in narrow columns. */
        div[data-testid="stButton"] button p {
            word-break: normal;
            overflow-wrap: normal;
            hyphens: none;
        }
        /* Responsive breakpoint: stack the top-level playground rails instead
           of squeezing three unusable columns into a narrow viewport. Nested
           column pairs (preset buttons, metric strip) keep sharing a row. */
        @media (max-width: 1100px) {
            div[data-testid="stMain"] div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
            }
            div[data-testid="stMain"] div[data-testid="stHorizontalBlock"]
                > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 100% !important;
            }
            div[data-testid="stMain"] div[data-testid="stColumn"]
                div[data-testid="stHorizontalBlock"]
                > div[data-testid="stColumn"] {
                flex: 1 1 40% !important;
                width: auto !important;
                min-width: 150px !important;
            }
            div[data-testid="stColumn"]:has(.sticky-preview-marker) {
                position: static;
            }
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
    """Render viewer controls, disabling those the current view mode ignores.

    Overlay uses a fixed rendering (current shaded + original wireframe), so
    display mode and normal overlays do nothing there; Side-by-side and
    Original-only honor the display mode but not the normal overlays. Instead
    of silently ignoring those controls (the audited no-op behavior), they are
    disabled with an explanation.
    """
    view_mode = str(st.session_state.get(PLAYGROUND_COMPARISON_KEY, "Current only"))
    display_scoped = view_mode == "Overlay"
    normals_scoped = view_mode != "Current only"

    st.header("Viewer")
    display_mode = st.selectbox(
        "Display mode",
        DISPLAY_MODES,
        key=DISPLAY_MODE_KEY,
        disabled=display_scoped,
    )
    if display_scoped:
        st.caption(
            "Display mode is unavailable in Overlay: it always draws the current "
            "mesh shaded with the original as a wireframe."
        )
    background_label = st.selectbox("Background", ["Light", "Dark"], key=BACKGROUND_KEY)
    show_axes = st.checkbox("Show axes", key=SHOW_AXES_KEY)

    with st.expander("Normals", expanded=False):
        if normals_scoped:
            st.caption(
                f"Normal overlays draw only in the 'Current only' Playground view "
                f"(current view: {view_mode})."
            )
        show_face_normals = st.checkbox(
            "Show face normals", key=SHOW_FACE_NORMALS_KEY, disabled=normals_scoped
        )
        show_vertex_normals = st.checkbox(
            "Show vertex normals", key=SHOW_VERTEX_NORMALS_KEY, disabled=normals_scoped
        )
        normals_off = not (
            st.session_state.get(SHOW_FACE_NORMALS_KEY) or st.session_state.get(SHOW_VERTEX_NORMALS_KEY)
        )
        normal_length = st.slider(
            "Normal length",
            0.0,
            1.0,
            key=NORMAL_LENGTH_KEY,
            step=0.05,
            disabled=normals_scoped or normals_off,
        )
        vertex_normal_weighting = st.selectbox(
            "Vertex normal weighting",
            ["average", "area-weighted"],
            key=VERTEX_NORMAL_WEIGHTING_KEY,
            disabled=normals_scoped or not st.session_state.get(SHOW_VERTEX_NORMALS_KEY),
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
        SOURCE_KIND_KEY: "Built-in sample mesh",
        LIVE_PREVIEW_KEY: True,
        PLAYGROUND_COMPARISON_KEY: "Overlay",
        NOISE_MODE_KEY: NOISE_ALONG_NORMALS,
        TAUBIN_MU_KEY: TAUBIN_DEFAULT_MU,
        PRESERVE_BOUNDARY_KEY: True,
        FALLOFF_TYPE_KEY: "linear",
        DEMO_MODIFIER_KEY: DEMO_NONE,
    }
    preset_values = {
        "See shrinkage": {
            SAMPLE_MESH_KEY: "Low-poly sphere",
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 14,
            SMOOTHING_STRENGTH_KEY: 0.5,
            PRESET_MESSAGE_KEY: "Preset loaded Low-poly sphere with repeated Uniform Laplacian smoothing. Look at the Overlay: the blue preview sits well inside the black original wireframe, and the AABB metric drops sharply.",
        },
        # Taubin pair validated by tests/test_presets.py: lambda=0.5, mu=-0.53
        # reduces the seed-42 noisy sphere's roughness by ~19% while changing
        # the AABB diagonal by only a few percent. (The earlier lambda=0.35
        # pair amplified mid frequencies and made the mesh rougher AND larger.)
        "Remove noise": {
            SAMPLE_MESH_KEY: "Low-poly sphere",
            NOISE_ENABLED_KEY: True,
            NOISE_STRENGTH_KEY: 0.35,
            NOISE_SEED_KEY: 42,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: TAUBIN,
            SMOOTHING_ITERATIONS_KEY: 10,
            SMOOTHING_STRENGTH_KEY: TAUBIN_STABLE_LAMBDA,
            PRESET_MESSAGE_KEY: "Preset loaded a noisy Low-poly sphere (seed 42) smoothed with Taubin lambda 0.5, mu -0.53, which passes the app's sampled-gain check. Read the clean -> noisy -> smoothed roughness line in the explanation panel: the smoothed stage is much less rough than the noisy stage while the size changes only a few percent.",
        },
        "Uniform vs Taubin": {
            SAMPLE_MESH_KEY: "Low-poly sphere",
            NOISE_ENABLED_KEY: True,
            NOISE_STRENGTH_KEY: 0.35,
            NOISE_SEED_KEY: 42,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 0,
            SMOOTHING_STRENGTH_KEY: 0.45,
            COMPARISON_INPUT_KEY: COMPARISON_INPUT_NOISY,
            PRESET_MESSAGE_KEY: "Preset created a noisy sphere preview (seed 42). Open Method Comparison: the comparison input is already set to 'Noisy preview stage', so Uniform, Taubin, and Cotangent all start from this exact noisy mesh.",
        },
        "Boundary preservation": {
            SAMPLE_MESH_KEY: "Plane/grid",
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 12,
            SMOOTHING_STRENGTH_KEY: 0.7,
            PRESERVE_BOUNDARY_KEY: True,
            DEMO_MODIFIER_KEY: DEMO_GRID_BUMP,
            PRESET_MESSAGE_KEY: "Preset loaded Plane/grid with a temporary raised bump. Toggle 'Preserve boundary vertices' off and on and watch the outer border: pinned when on, sliding inward when off.",
        },
        "Local soft smoothing": {
            SAMPLE_MESH_KEY: "Plane/grid",
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Local / soft smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 10,
            SMOOTHING_STRENGTH_KEY: 0.65,
            LOCAL_CENTER_KEY: 12,
            LOCAL_RADIUS_KEY: 3,
            FALLOFF_TYPE_KEY: "smoothstep",
            DEMO_MODIFIER_KEY: DEMO_GRID_BUMP,
            PLAYGROUND_COMPARISON_KEY: "Current only",
            PRESET_MESSAGE_KEY: "Preset loaded Plane/grid with a raised bump and a radius-3 soft selection (red = center, orange = affected region). Change the radius to grow the region; at radius 3+ the falloff curve also changes the middle-ring weights.",
        },
        "Inspect one vertex": {
            SAMPLE_MESH_KEY: "Low-poly sphere",
            NOISE_ENABLED_KEY: False,
            SMOOTHING_MODE_KEY: "Global smoothing",
            SMOOTHING_METHOD_KEY: UNIFORM_LAPLACIAN,
            SMOOTHING_ITERATIONS_KEY: 1,
            SMOOTHING_STRENGTH_KEY: 0.5,
            INSPECT_VERTEX_KEY: 0,
            PLAYGROUND_COMPARISON_KEY: "Current only",
            PRESET_MESSAGE_KEY: "Preset loaded Low-poly sphere with one smoothing iteration. Open Step Inspector to connect one visible vertex move to the smoothing formula.",
        },
    }
    values = preset_values.get(name, {})
    for key, value in {**common, **values}.items():
        st.session_state[key] = value
    st.session_state[RESET_REQUESTED_KEY] = True
    st.session_state[PRESET_SOURCE_SWITCH_KEY] = True


def _reset_experiment() -> None:
    """Restore the working mesh to the clean original and clear derived state."""
    if ORIGINAL_MESH_KEY not in st.session_state:
        return
    original = st.session_state[ORIGINAL_MESH_KEY]
    st.session_state[WORKING_MESH_KEY] = clone_mesh(original)
    st.session_state[SMOOTHING_STEPS_KEY] = 0
    st.session_state[SMOOTHING_HISTORY_KEY] = []
    st.session_state[PREVIEW_MESH_KEY] = None
    st.session_state[PREVIEW_NOISY_STAGE_KEY] = None
    st.session_state[NOISE_APPLIED_KEY] = False
    st.session_state[NOISE_INFO_KEY] = None
    st.session_state[INSPECT_VERTEX_KEY] = 0
    _clear_method_comparison()
    _bump_working_version()


def _reset_experiment_and_controls() -> None:
    """Reset button callback: restore state AND neutralize experiment widgets.

    This runs as an ``on_click`` callback, which Streamlit executes before any
    widget of the next run is instantiated, so writing widget-backed session
    keys here is legal. Writing them inline after the button (the previous
    implementation) raised ``StreamlitAPIException`` because the widgets had
    already been created in the same run.
    """
    _reset_experiment()
    st.session_state[NOISE_ENABLED_KEY] = False
    st.session_state[SMOOTHING_ITERATIONS_KEY] = 0
    st.session_state[DEMO_MODIFIER_KEY] = DEMO_NONE
    st.session_state[PRESET_MESSAGE_KEY] = ""
    st.session_state[PLAYGROUND_COMPARISON_KEY] = "Current only"
    st.session_state[LIVE_PREVIEW_KEY] = True
    st.session_state[FLASH_MESSAGE_KEY] = (
        "success",
        "Restored the clean original mesh and reset the experiment controls.",
    )


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
    if st.session_state.get(DEMO_MODIFIER_KEY) == DEMO_GRID_BUMP:
        st.caption("This preset adds a temporary preview bump to Plane/grid so the smoothing effect is visible.")


def _render_playground_controls(mesh: MeshData) -> dict[str, object]:
    """Render live preview controls and return normalized values."""
    if st.session_state.get(DEMO_MODIFIER_KEY) == DEMO_GRID_BUMP and mesh.name != "Plane/grid":
        st.session_state[DEMO_MODIFIER_KEY] = DEMO_NONE

    _render_preset_buttons()
    st.divider()

    live_preview = st.checkbox("Live Preview", key=LIVE_PREVIEW_KEY)
    st.caption(
        "On: controls update a temporary preview. Off: use the apply buttons to change the working mesh."
    )

    st.markdown("**Noise**")
    noise_enabled = st.checkbox("Noise enabled", key=NOISE_ENABLED_KEY)
    noise_controls_disabled = not noise_enabled
    if noise_controls_disabled:
        st.caption(
            "Enable noise to edit its settings; the saved strength, seed, and mode are retained."
        )
    noise_strength = st.slider(
        "Noise strength",
        0.0,
        1.0,
        key=NOISE_STRENGTH_KEY,
        step=0.05,
        disabled=noise_controls_disabled,
    )
    noise_seed = st.number_input(
        "Noise seed",
        min_value=0,
        max_value=999999,
        key=NOISE_SEED_KEY,
        step=1,
        disabled=noise_controls_disabled,
    )
    noise_mode = st.selectbox(
        "Noise mode",
        NOISE_MODES,
        key=NOISE_MODE_KEY,
        disabled=noise_controls_disabled,
    )

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
                help=(
                    "Lambda < |mu| gives a positive pass-band 1/lambda + 1/mu, "
                    "but it is not sufficient for stability. The app samples the "
                    "transfer-function gain; lambda 0.5, mu -0.53 passes that check."
                ),
            )
            stability = taubin_stability(float(smoothing_strength), float(taubin_mu))
            if int(smoothing_iterations) > 0 and not stability["stable"]:
                iterations_hint = max(1, int(smoothing_iterations))
                st.warning(
                    f"Unstable Taubin pair: lambda={float(smoothing_strength):.2f}, "
                    f"mu={float(taubin_mu):.2f} amplifies some frequencies by x"
                    f"{stability['max_gain']:.3f} per iteration (about x"
                    f"{stability['max_gain'] ** iterations_hint:.1f} after "
                    f"{iterations_hint} iterations). Expect the mesh to expand or "
                    "roughen instead of smoothing. Lambda < |mu| alone does not "
                    "guarantee this check; try lambda 0.5 with mu -0.53."
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
            key=LOCAL_CENTER_KEY,
            help=f"Valid center range: 0 to {center_max}",
        )
        max_radius = _max_graph_radius(mesh, center_vertex)
        if st.session_state.get(LOCAL_RADIUS_KEY, 1) > max_radius:
            st.session_state[LOCAL_RADIUS_KEY] = min(2, max_radius)
        if max_radius <= 1:
            soft_radius = 1
            st.session_state[LOCAL_RADIUS_KEY] = soft_radius
            st.caption("Soft selection radius is fixed at 1 graph step for this center vertex.")
        else:
            soft_radius = st.slider(
                "Soft selection radius (graph steps)",
                1,
                max_radius,
                key=LOCAL_RADIUS_KEY,
                help="1 graph step = crossing one edge from the center vertex.",
            )
        falloff_locked = int(soft_radius) < 3
        falloff_type = st.selectbox(
            "Falloff type",
            FALLOFF_TYPES,
            key=FALLOFF_TYPE_KEY,
            disabled=falloff_locked,
            help=(
                "How the smoothing weight fades from 1 at the center to 0 at the "
                "radius ring."
            ),
        )
        if falloff_locked:
            st.caption(
                "Falloff is locked at radius 1-2: with integer graph distances, "
                "linear and smoothstep produce exactly the same weights there. "
                "Use radius 3 or more to see the curves differ."
            )
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
        "demo_modifier": st.session_state.get(DEMO_MODIFIER_KEY, DEMO_NONE),
    }


def _apply_demo_modifier(
    mesh: MeshData,
    controls: dict[str, object],
) -> tuple[MeshData, bool]:
    """Apply preview-only teaching geometry for demos that need a visible feature."""
    if controls.get("demo_modifier") != DEMO_GRID_BUMP:
        return mesh, False
    if not mesh.valid or mesh.name != "Plane/grid":
        return mesh, False

    vertices = mesh.vertices.astype(float, copy=True)
    xy = vertices[:, :2]
    minimum = xy.min(axis=0)
    maximum = xy.max(axis=0)
    center = 0.5 * (minimum + maximum)
    span = np.maximum(maximum - minimum, 1.0e-9)
    normalized_distance = np.linalg.norm((xy - center) / span, axis=1)
    edge_distance = np.minimum.reduce(
        [
            xy[:, 0] - minimum[0],
            maximum[0] - xy[:, 0],
            xy[:, 1] - minimum[1],
            maximum[1] - xy[:, 1],
        ]
    )
    edge_fade = np.clip(edge_distance / (0.25 * float(span.min())), 0.0, 1.0)
    bump = 0.55 * np.exp(-((normalized_distance / 0.32) ** 2)) * edge_fade**2
    vertices[:, 2] += bump
    return copy_with_vertices(mesh, vertices, name=f"{mesh.name} teaching bump"), True


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
    """Compute the temporary preview mesh without mutating the working mesh.

    Every stage flag (``demo_applied``, ``noise_applied``, ``smoothing_applied``,
    ``changed``) reflects an ACTUAL vertex change, verified by comparing the
    geometry before and after the stage — never merely "the operation was
    requested". The noisy intermediate stage is stored in session state so the
    Method Comparison lab can use it as a named input baseline.
    """
    info: dict[str, object] = {
        "supported": True,
        "note": "",
        "demo_applied": False,
        "noise_applied": False,
        "smoothing_applied": False,
        "changed": False,
        "stage_roughness": {},
        "stage_bbox": {},
    }
    if not controls["live_preview"]:
        st.session_state[PREVIEW_MESH_KEY] = None
        st.session_state[PREVIEW_NOISY_STAGE_KEY] = None
        return working_mesh, info

    guard_note = _live_preview_guard(working_mesh, controls)
    if guard_note:
        info["supported"] = False
        info["note"] = guard_note
        st.session_state[PREVIEW_MESH_KEY] = None
        st.session_state[PREVIEW_NOISY_STAGE_KEY] = None
        return working_mesh, info

    def _stage_metrics(mesh: MeshData) -> tuple[float | None, float | None]:
        roughness = compute_roughness_energy(mesh)["mean"]
        vertices = mesh.vertices
        if vertices.size == 0:
            return roughness, None
        diagonal = float(np.linalg.norm(vertices.max(axis=0) - vertices.min(axis=0)))
        return roughness, diagonal

    rough, bbox = _stage_metrics(working_mesh)
    info["stage_roughness"]["working"] = rough
    info["stage_bbox"]["working"] = bbox

    preview = clone_mesh(working_mesh)
    bumped, demo_requested = _apply_demo_modifier(preview, controls)
    if demo_requested and not _meshes_have_same_vertices(preview, bumped):
        preview = bumped
        info["demo_applied"] = True

    noisy_stage: MeshData | None = None
    if controls["noise_enabled"] and controls["noise_strength"] > 0.0:
        noised = add_noise(
            preview,
            strength=float(controls["noise_strength"]),
            seed=int(controls["noise_seed"]),
            mode=str(controls["noise_mode"]),
        )
        if not _meshes_have_same_vertices(preview, noised):
            preview = noised
            info["noise_applied"] = True
            noisy_stage = clone_mesh(preview)
            rough, bbox = _stage_metrics(preview)
            info["stage_roughness"]["noisy"] = rough
            info["stage_bbox"]["noisy"] = bbox

    iterations = int(controls["smoothing_iterations"])
    if iterations > 0:
        pre_smoothing = preview
        if controls["smoothing_mode"] == "Local / soft smoothing":
            smoothed = laplacian_smooth_local(
                preview,
                iterations=iterations,
                strength=float(controls["smoothing_strength"]),
                center_index=int(controls["center_vertex"] or 0),
                radius=int(controls["soft_radius"] or 1),
                falloff_type=str(controls["falloff_type"] or "linear"),
                preserve_boundary=bool(controls["preserve_boundary"]),
            )
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
                smoothed = result.mesh
            else:
                smoothed = pre_smoothing
                info["supported"] = False
                info["note"] = result.note
        if info["supported"] and not _meshes_have_same_vertices(pre_smoothing, smoothed):
            preview = smoothed
            info["smoothing_applied"] = True

    info["changed"] = not _meshes_have_same_vertices(working_mesh, preview)
    rough, bbox = _stage_metrics(preview)
    info["stage_roughness"]["preview"] = rough
    info["stage_bbox"]["preview"] = bbox

    st.session_state[PREVIEW_MESH_KEY] = preview if info["changed"] else None
    st.session_state[PREVIEW_NOISY_STAGE_KEY] = noisy_stage
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
    """Commit-button callback: promote the preview to the working mesh.

    Runs as an ``on_click`` callback so it may also clear the one-shot noise and
    smoothing controls; without that clearing, the very next rerun would apply
    the same operation again on top of the freshly committed mesh (the
    double-preview bug).
    """
    if not preview_info.get("supported", True):
        st.session_state[FLASH_MESSAGE_KEY] = (
            "warning",
            preview_info.get("note") or "Preview is not supported for this mesh.",
        )
        return
    if not preview_info.get("changed") or _meshes_have_same_vertices(working_mesh, preview_mesh):
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "The preview geometry is identical to the working mesh; nothing was committed.",
        )
        return

    roughness_before = compute_roughness_energy(working_mesh)["mean"]
    committed = clone_mesh(preview_mesh)
    st.session_state[WORKING_MESH_KEY] = committed
    _clear_method_comparison()

    smoothing_moved = bool(preview_info.get("smoothing_applied"))
    noise_moved = bool(preview_info.get("noise_applied"))
    demo_applied = bool(preview_info.get("demo_applied"))
    added_iterations = int(controls["smoothing_iterations"]) if smoothing_moved else 0
    st.session_state[SMOOTHING_STEPS_KEY] += added_iterations
    roughness_after = compute_roughness_energy(committed)["mean"]

    if noise_moved:
        st.session_state[NOISE_APPLIED_KEY] = True
        st.session_state[NOISE_INFO_KEY] = {
            "strength": float(controls["noise_strength"]),
            "seed": int(controls["noise_seed"]),
            "mode": controls["noise_mode"],
        }

    # Record what actually happened, not what the widgets happened to show.
    is_local = controls["smoothing_mode"] == "Local / soft smoothing"
    committed_parts: list[str] = []
    if demo_applied:
        committed_parts.append("teaching bump")
    if noise_moved:
        committed_parts.append(f"noise ({controls['noise_mode']}, strength {float(controls['noise_strength']):.2f}, seed {int(controls['noise_seed'])})")
    if smoothing_moved:
        committed_parts.append(f"{_method_label(controls)} x{added_iterations}")
    if smoothing_moved:
        method_label = _method_label(controls)
        recorded_lambda = float(controls["smoothing_strength"])
    elif noise_moved:
        method_label = f"Noise ({controls['noise_mode']})"
        recorded_lambda = 0.0
    else:
        method_label = "Teaching bump"
        recorded_lambda = 0.0
    _append_smoothing_history(
        st.session_state[ORIGINAL_MESH_KEY],
        committed,
        st.session_state[SMOOTHING_STEPS_KEY],
        recorded_lambda,
        bool(controls["preserve_boundary"]) if smoothing_moved else False,
        smoothing_mode=("Local / soft" if (is_local and smoothing_moved) else ("Global" if smoothing_moved else "Noise/preview")),
        method=method_label,
        mu=float(controls["taubin_mu"])
        if (smoothing_moved and not is_local and controls["smoothing_method"] == TAUBIN)
        else None,
        roughness_before=roughness_before,
        roughness_after=roughness_after,
        center_vertex=int(controls["center_vertex"]) if (is_local and smoothing_moved) else None,
        soft_radius=int(controls["soft_radius"]) if (is_local and smoothing_moved) else None,
        falloff_type=str(controls["falloff_type"]) if (is_local and smoothing_moved) else None,
        noise_strength=float(controls["noise_strength"]) if noise_moved else None,
        noise_seed=int(controls["noise_seed"]) if noise_moved else None,
        noise_mode=str(controls["noise_mode"]) if noise_moved else None,
        action="Commit preview",
    )
    _bump_working_version()

    # One-shot semantics: the committed operation must not immediately rebuild
    # itself as the next preview (legal here because this is an on_click
    # callback, executed before the widgets are instantiated).
    st.session_state[NOISE_ENABLED_KEY] = False
    st.session_state[SMOOTHING_ITERATIONS_KEY] = 0
    st.session_state[DEMO_MODIFIER_KEY] = DEMO_NONE
    st.session_state[FLASH_MESSAGE_KEY] = (
        "success",
        "Committed to the working mesh: " + "; ".join(committed_parts) + ". "
        "Noise and iteration controls were reset to neutral so the viewer now "
        "shows exactly the committed state.",
    )


def _add_noise_to_working(controls: dict[str, object]) -> None:
    """Manual-mode callback: apply noise directly to the working mesh."""
    if not controls["noise_enabled"] or float(controls["noise_strength"]) <= 0.0:
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "Noise is disabled or its strength is 0, so no noise was applied.",
        )
        return
    source_mesh = _working_mesh()
    roughness_before = compute_roughness_energy(source_mesh)["mean"]
    noisy = add_noise(
        source_mesh,
        strength=float(controls["noise_strength"]),
        seed=int(controls["noise_seed"]),
        mode=str(controls["noise_mode"]),
    )
    if _meshes_have_same_vertices(source_mesh, noisy):
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "These noise settings did not move any vertex; nothing was recorded.",
        )
        return
    st.session_state[WORKING_MESH_KEY] = noisy
    _clear_method_comparison()
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
        noise_strength=float(controls["noise_strength"]),
        noise_seed=int(controls["noise_seed"]),
        noise_mode=str(controls["noise_mode"]),
        action="Add noise",
    )
    _bump_working_version()
    st.session_state[FLASH_MESSAGE_KEY] = (
        "success",
        "Noise added to the current working mesh.",
    )


def _apply_smoothing_to_working(controls: dict[str, object]) -> None:
    """Manual-mode callback: apply smoothing directly to the working mesh."""
    iterations = int(controls["smoothing_iterations"])
    if iterations <= 0:
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "Set iterations above 0 to apply smoothing.",
        )
        return

    source_mesh = _working_mesh()
    roughness_before = compute_roughness_energy(source_mesh)["mean"]
    is_local = controls["smoothing_mode"] == "Local / soft smoothing"

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
        if not result.supported:
            st.session_state[FLASH_MESSAGE_KEY] = (
                "warning",
                result.note or "This method is not supported for the current mesh.",
            )
            return
        next_mesh = result.mesh

    if _meshes_have_same_vertices(source_mesh, next_mesh):
        st.session_state[FLASH_MESSAGE_KEY] = (
            "info",
            "These settings did not move any vertex (for example, the affected "
            "region may be fully pinned), so no smoothing was recorded.",
        )
        return

    st.session_state[WORKING_MESH_KEY] = next_mesh
    _clear_method_comparison()
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
    _bump_working_version()
    st.session_state[FLASH_MESSAGE_KEY] = (
        "success",
        f"Applied {iterations} smoothing iteration(s).",
    )


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
        commit_disabled = not bool(preview_info.get("changed")) or not bool(
            preview_info.get("supported", True)
        )
        if commit_disabled and preview_info.get("supported", True):
            st.caption("Commit is disabled because the preview geometry equals the working mesh.")
        st.button(
            "Commit preview as current mesh",
            use_container_width=True,
            disabled=commit_disabled,
            on_click=_commit_preview_mesh,
            args=(working_mesh, active_mesh, controls, preview_info),
        )
    else:
        st.caption("Live Preview is off. These buttons mutate the committed working mesh.")
        noise_blocked = not controls["noise_enabled"] or float(controls["noise_strength"]) <= 0.0
        if noise_blocked:
            st.caption(
                "'Add noise' is disabled: enable the 'Noise enabled' checkbox and set "
                "a strength above 0."
            )
        st.button(
            "Add noise to current mesh",
            use_container_width=True,
            disabled=noise_blocked,
            on_click=_add_noise_to_working,
            args=(controls,),
        )
        lambda_is_noop = (
            float(controls["smoothing_strength"]) <= 0.0
            and controls["smoothing_method"] != TAUBIN
        )
        smoothing_blocked = int(controls["smoothing_iterations"]) <= 0 or lambda_is_noop
        if smoothing_blocked:
            st.caption(
                "'Apply smoothing' is disabled: set iterations above 0 and lambda "
                "above 0 (with these settings no vertex would move)."
            )
        st.button(
            "Apply smoothing",
            use_container_width=True,
            disabled=smoothing_blocked,
            on_click=_apply_smoothing_to_working,
            args=(controls,),
        )

    st.button(
        "Reset experiment",
        use_container_width=True,
        on_click=_reset_experiment_and_controls,
    )


def _meshes_have_same_vertices(first: MeshData, second: MeshData, tolerance: float = 1.0e-9) -> bool:
    """Return True when two meshes have matching vertex positions."""
    if (
        not first.valid
        or not second.valid
        or first.vertex_count == 0
        or first.vertex_count != second.vertex_count
    ):
        return False
    return bool(np.allclose(first.vertices, second.vertices, atol=tolerance, rtol=0.0))


def _local_highlight_options(
    mesh: MeshData,
    controls: dict[str, object],
) -> dict[str, list[int] | int | None]:
    """Return local-smoothing highlight data for the current viewer."""
    if controls["smoothing_mode"] != "Local / soft smoothing":
        return {"highlight_vertices": None, "center_vertex": None}
    soft = compute_soft_selection_weights(
        mesh,
        center_index=int(controls["center_vertex"] or 0),
        radius=int(controls["soft_radius"] or 1),
        falloff_type=str(controls["falloff_type"] or "linear"),
    )
    affected = np.flatnonzero(soft.weights > 0.0).astype(int).tolist()
    return {"highlight_vertices": affected, "center_vertex": int(soft.center_index)}


def _playground_status_text(
    original_mesh: MeshData,
    active_mesh: MeshData,
    controls: dict[str, object],
    preview_info: dict[str, object],
) -> str:
    """Build a concise explanation of the mesh state currently in the viewer."""
    if preview_info.get("note"):
        return f"Preview paused: {preview_info['note']}"

    if not controls["live_preview"]:
        if _meshes_have_same_vertices(original_mesh, active_mesh):
            return "Working mesh: clean original. Live Preview is off, so use the apply buttons to change it."
        return "Working mesh: committed mesh state. Live Preview is off, so controls do not update the viewer until applied."

    if not preview_info.get("changed") and _meshes_have_same_vertices(original_mesh, active_mesh):
        return "Current state: clean original. Choose a preset, add noise, or raise smoothing iterations to create a preview."

    parts: list[str] = []
    if preview_info.get("demo_applied"):
        parts.append("teaching bump")
    if preview_info.get("noise_applied"):
        parts.append(
            f"noise strength {_format_value(controls['noise_strength'], digits=2)}"
        )
    if preview_info.get("smoothing_applied"):
        method = _method_label(controls)
        parts.append(
            f"{method}, {int(controls['smoothing_iterations'])} iterations, "
            f"lambda {_format_value(controls['smoothing_strength'], digits=2)}"
        )
        if controls["smoothing_mode"] == "Local / soft smoothing":
            summary = affected_soft_selection_vertices(
                active_mesh,
                center_index=int(controls["center_vertex"] or 0),
                radius=int(controls["soft_radius"] or 1),
                falloff_type=str(controls["falloff_type"] or "linear"),
                preserve_boundary=bool(controls["preserve_boundary"]),
            )
            parts.append(
                f"{summary['movable_affected_vertices']} movable affected vertices"
            )

    if parts:
        text = "Preview: " + "; ".join(parts) + "."
        stage_line = _stage_roughness_line(preview_info)
        if stage_line:
            text += " " + stage_line
        return text
    return "Preview: current controls do not move vertices yet."


def _stage_roughness_line(preview_info: dict[str, object]) -> str:
    """Describe the start -> noisy -> preview roughness sequence when known."""
    stages = preview_info.get("stage_roughness", {})
    if not isinstance(stages, dict):
        return ""
    start = stages.get("working")
    noisy = stages.get("noisy")
    preview = stages.get("preview")
    if start is None or preview is None:
        return ""
    if noisy is not None:
        final_stage = "smoothed" if preview_info.get("smoothing_applied") else "preview"
        return (
            f"Roughness start -> noisy -> {final_stage}: {start:.4f} -> {noisy:.4f} -> "
            f"{preview:.4f}."
        )
    if abs(preview - start) > 1.0e-12:
        return f"Roughness start -> preview: {start:.4f} -> {preview:.4f}."
    return ""


def _viewer_heading_and_legend(
    comparison_mode: str,
    active_label: str,
    active_mesh: MeshData,
    original_mesh: MeshData,
) -> tuple[str, str]:
    """Return the mode-true viewer heading and the color legend for the mode."""
    if comparison_mode == "Overlay":
        return (
            f"Viewer: original + {active_label.lower()} overlay",
            "Legend: black wireframe = source original; blue shaded = "
            f"{active_label.lower()}; orange lines = sampled vertex displacement.",
        )
    if comparison_mode == "Side-by-side":
        return (
            f"Viewer: original (left) vs {active_label.lower()} (right)",
            "Legend: both meshes share ONE scene and camera, so a size difference "
            "on screen is a real size difference. Left (grey) = source original; "
            "right (blue) = " + active_label.lower() + ".",
        )
    if comparison_mode == "Original only":
        return (
            f"Viewer: source original ({original_mesh.name})",
            "Legend: the viewer shows only the untouched source original. The "
            "status and metric cards still describe the "
            + active_label.lower()
            + ", which is hidden in this view.",
        )
    return (
        f"Viewer: {active_label.lower()} ({active_mesh.name})",
        "Legend: the viewer shows the "
        + active_label.lower()
        + ". Display mode and normal overlays apply in this view.",
    )


def _render_expansion_warning(preview_info: dict[str, object]) -> None:
    """Warn when the preview grew substantially versus the working mesh."""
    bbox = preview_info.get("stage_bbox", {})
    start = bbox.get("working")
    end = bbox.get("preview")
    if start and end and start > 0 and (end - start) / start > 0.15:
        st.warning(
            f"The preview EXPANDED the bounding-box diagonal by "
            f"{100.0 * (end - start) / start:.1f}%. A large AABB increase can "
            "signal an unstable Taubin pair; synthetic noise can also change the "
            "AABB. Check the current method and metrics before interpreting it."
        )


def _render_playground_viewer(
    original_mesh: MeshData,
    active_mesh: MeshData,
    controls: dict[str, object],
    viewer_options: dict[str, object],
    preview_info: dict[str, object],
) -> None:
    """Render the primary visual preview area."""
    active_label = "Live preview" if controls["live_preview"] else "Working mesh"
    comparison_mode = st.selectbox(
        "Playground view",
        PLAYGROUND_COMPARISON_MODES,
        key=PLAYGROUND_COMPARISON_KEY,
    )
    heading, legend = _viewer_heading_and_legend(
        comparison_mode, active_label, active_mesh, original_mesh
    )
    st.markdown(f"**{heading}**")
    status_prefix = (
        f"{active_label} state (NOT shown in this view): "
        if comparison_mode == "Original only"
        else ""
    )
    st.info(status_prefix + _playground_status_text(original_mesh, active_mesh, controls, preview_info))
    _render_expansion_warning(preview_info)
    if (
        comparison_mode in {"Overlay", "Side-by-side"}
        and _meshes_have_same_vertices(original_mesh, active_mesh)
    ):
        st.caption("Original and current mesh are identical right now; the comparison will look unchanged until a preview or commit moves vertices.")

    if not original_mesh.valid or not active_mesh.valid:
        st.error(active_mesh.error_message or "The selected mesh is not valid.")
        return

    highlight_options = _local_highlight_options(active_mesh, controls)
    highlight_vertices = highlight_options["highlight_vertices"]
    center_vertex = highlight_options["center_vertex"]

    try:
        if comparison_mode == "Overlay":
            plotter = make_overlay_plotter(
                original_mesh,
                active_mesh,
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                window_size=(760, 520),
                highlight_vertices=highlight_vertices,
                center_vertex=center_vertex,
            )
            _render_plotter(plotter)
        elif comparison_mode == "Side-by-side":
            plotter = make_side_by_side_plotter(
                original_mesh,
                active_mesh,
                display_mode=str(viewer_options["display_mode"]),
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                window_size=(760, 460),
                highlight_vertices=highlight_vertices,
                center_vertex=center_vertex,
            )
            _render_plotter(plotter)
        elif comparison_mode == "Original only":
            _render_mesh_plotter(
                original_mesh,
                display_mode=str(viewer_options["display_mode"]),
                background_color=str(viewer_options["background_color"]),
                show_axes=bool(viewer_options["show_axes"]),
                window_size=(760, 520),
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
                window_size=(760, 520),
                highlight_vertices=highlight_vertices,
                center_vertex=center_vertex,
            )
            _render_plotter(plotter)
        st.caption(legend)
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

    if not preview_info.get("changed") and controls["live_preview"]:
        if _meshes_have_same_vertices(mesh, st.session_state[ORIGINAL_MESH_KEY]):
            bullets.append("The viewer is showing the clean original because the current settings did not move any vertices.")
        else:
            bullets.append("The current controls do not change the committed working mesh, so the viewer shows that committed state.")

    if preview_info.get("demo_applied"):
        bullets.append("The preset starts this preview from a raised grid bump so boundary and local smoothing have a visible feature to relax.")

    if controls["noise_enabled"]:
        bullets.append(
            "Noise draws a Gaussian offset per vertex: sigma is strength times "
            "the current mesh's median edge length, capped at half an edge. It "
            "uses vertex-normal or random-3D directions; degenerate normals fall "
            "back to random 3D. The same input mesh, mode, and seed reproduce it."
        )
        stage_line = _stage_roughness_line(preview_info)
        if stage_line:
            bullets.append(stage_line + " For this synthetic-noise experiment, read a lower final residual together with the size metrics rather than as a general quality score.")

    if controls["smoothing_mode"] == "Local / soft smoothing":
        summary = affected_soft_selection_vertices(
            mesh,
            center_index=int(controls["center_vertex"] or 0),
            radius=int(controls["soft_radius"] or 1),
            falloff_type=str(controls["falloff_type"] or "linear"),
            preserve_boundary=bool(controls["preserve_boundary"]),
        )
        bullets.extend(
            [
                "Local smoothing behaves like a soft brush: red is the center vertex and orange marks vertices with nonzero weight.",
                f"Radius {summary['radius']} assigns nonzero weight to {summary['affected_vertices']} vertices, with {summary['movable_affected_vertices']} movable after boundary rules.",
                "Increase the radius to widen the nonzero-weight region; change falloff to alter how quickly the effect fades. The radius ring itself has zero weight.",
            ]
        )
    elif controls["smoothing_method"] == UNIFORM_LAPLACIAN:
        bullets.extend(
            [
                "Each vertex moves toward the average of its neighbors (lambda sets the fraction; 0 moves nothing).",
                "Watch the Overlay: on closed shapes the preview usually pulls inside the original wireframe (shrinkage).",
                "If roughness falls with a large size drop, shrinkage is contributing to that metric change; it is not evidence of a better result by itself.",
            ]
        )
    elif controls["smoothing_method"] == TAUBIN:
        bullets.extend(
            [
                "Taubin alternates a positive smoothing step (lambda) with a negative correction step (mu).",
                "Lambda < |mu| gives a positive pass-band, but the app's sampled-gain check is the stability warning to use. The 0.5 / -0.53 pair passes that check.",
                "Pairs that fail the check can amplify some frequencies, expand, or roughen the mesh.",
            ]
        )
    elif controls["smoothing_method"] == COTANGENT_LAPLACIAN:
        if is_triangle_mesh(mesh):
            bullets.extend(
                [
                    "Cotangent smoothing weights each neighbor by the triangle angles opposite the shared edge.",
                    "This implementation requires a triangulation, computes the weights once from the starting shape, and clamps negative weights (a stability simplification).",
                    "Compare it with Uniform on the same mesh: its target uses the starting triangle angles instead of equal neighbor weights.",
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
    elif len(find_boundary_vertices(mesh)) > 0:
        bullets.append("Boundary preservation is off, so open borders may slide inward during smoothing.")

    if not controls["live_preview"]:
        bullets.append("Live Preview is off, so the viewer shows only committed working-mesh changes.")

    st.markdown(_bullets(bullets[:7]))


def _metric_card(label: str, value: str, interpretation: str) -> None:
    """Render one compact metric card."""
    with st.container(border=True):
        st.metric(label, value)
        st.caption(interpretation)


def _boundary_motion_summary(
    original_mesh: MeshData,
    active_mesh: MeshData,
) -> dict[str, float | int | bool] | None:
    """Measure boundary and interior movement for comparable open meshes."""
    if (
        not original_mesh.valid
        or not active_mesh.valid
        or original_mesh.vertex_count == 0
        or original_mesh.vertex_count != active_mesh.vertex_count
    ):
        return None
    boundary = sorted(find_boundary_vertices(original_mesh))
    if not boundary:
        return None

    displacement = np.linalg.norm(active_mesh.vertices - original_mesh.vertices, axis=1)
    boundary_indices = np.asarray(boundary, dtype=int)
    interior_mask = np.ones(original_mesh.vertex_count, dtype=bool)
    interior_mask[boundary_indices] = False
    boundary_values = displacement[boundary_indices]
    interior_values = displacement[interior_mask]
    boundary_average = float(boundary_values.mean()) if boundary_values.size else 0.0
    interior_average = float(interior_values.mean()) if interior_values.size else 0.0
    return {
        "boundary_count": int(boundary_values.size),
        "boundary_average": boundary_average,
        "interior_average": interior_average,
        "boundary_moved": bool(np.any(boundary_values > 1.0e-6)),
    }


def _render_compact_metric_strip(
    original_mesh: MeshData,
    active_mesh: MeshData,
    controls: dict[str, object],
) -> None:
    """Render the 3 key metrics + a look-for hint inside the sticky viewer column."""
    metrics = compare_meshes(original_mesh, active_mesh, smoothing_iterations=0)
    rough_change = _percent_change(
        compute_roughness_energy(original_mesh)["mean"],
        compute_roughness_energy(active_mesh)["mean"],
    )
    columns = st.columns(3)
    columns[0].metric(
        "Roughness change",
        _format_percent(rough_change) if rough_change is not None else "N/A",
        help=ROUGHNESS_CAPTION + " Baseline: source original -> viewer state.",
    )
    columns[1].metric(
        "AABB diagonal change",
        _format_percent(metrics["bounding_box_percent_change"])
        if metrics["bounding_box_percent_change"] is not None
        else "N/A",
        help=(
            "Axis-aligned bounding-box diagonal versus the source original. "
            "Negative = smaller. It is orientation-sensitive and is a size proxy, "
            "not a full shape or volume measure."
        ),
    )
    columns[2].metric(
        "Avg vertex movement",
        _format_value(metrics["average_displacement"])
        if metrics["average_displacement"] is not None
        else "N/A",
        help="Mean distance each vertex moved from the source original (length units).",
    )
    if controls["smoothing_mode"] == "Local / soft smoothing":
        hint = "Look for: only the orange nonzero-weight region can move; pinned boundaries and every zero-weight vertex stay put."
    elif controls["smoothing_method"] == TAUBIN:
        hint = "Look for: on a pair that passes the gain check, roughness dropping while the AABB change stays small."
    elif controls["noise_enabled"]:
        hint = "Look for: the surface getting spiky and roughness jumping up as noise is added."
    else:
        hint = "Look for: the preview pulling inside the original wireframe as iterations rise."
    st.caption(hint + " With 1 iteration or a small lambda the change is real but subtle.")


def _render_metric_cards(original_mesh: MeshData, active_mesh: MeshData) -> None:
    """Render the secondary metric cards for the visual playground."""
    st.subheader("More metrics")
    st.caption("Baseline for every card: source original -> current viewer state.")
    metrics = compare_meshes(original_mesh, active_mesh, smoothing_iterations=0)
    original = metrics["original"]
    current = metrics["current"]
    topology_changed = (
        original["vertex_count"] != current["vertex_count"]
        or original["face_count"] != current["face_count"]
        or original["unique_edge_count"] != current["unique_edge_count"]
    )

    if metrics["surface_area_percent_change"] is None:
        area_value = "N/A"
        area_text = "Surface area needs usable faces."
    else:
        area_value = _format_percent(metrics["surface_area_percent_change"])
        area_text = "Area can change for many reasons (smoothing, shrinkage, noise); it is not a direct 'detail removed' score."

    topology_value = "Yes" if topology_changed else "No"
    topology_text = "Vertex/face/edge counts only; the card does not compare face-index lists. These operations reuse the existing faces."

    _metric_card("Surface area change", area_value, area_text)
    _metric_card("Topology counts changed?", topology_value, topology_text)
    boundary_motion = _boundary_motion_summary(original_mesh, active_mesh)
    if boundary_motion is not None:
        boundary_value = "Yes" if boundary_motion["boundary_moved"] else "No"
        boundary_text = (
            "Yes means at least one source-boundary vertex moved more than 1e-6 mesh units. "
            f"Boundary avg {_format_value(boundary_motion['boundary_average'])} mesh units; "
            f"interior avg {_format_value(boundary_motion['interior_average'])} mesh units."
        )
        _metric_card("Boundary moved?", boundary_value, boundary_text)


def _render_playground(working_mesh: MeshData, viewer_options: dict[str, object]) -> tuple[MeshData, dict[str, object]]:
    """Render the visual-first playground tab.

    The center column is sticky and contains the viewer PLUS the compact metric
    strip and look-for hint, so the change -> see -> understand loop stays on
    screen even when the student scrolls down to the lower controls.
    """
    original_mesh = st.session_state[ORIGINAL_MESH_KEY]
    left_column, center_column, right_column = st.columns([0.28, 0.47, 0.25], gap="large")

    with left_column:
        controls = _render_playground_controls(working_mesh)
        active_mesh, preview_info = _build_preview_mesh(working_mesh, controls)
        _render_commit_controls(working_mesh, active_mesh, controls, preview_info)

    with center_column:
        st.markdown('<div class="sticky-preview-marker"></div>', unsafe_allow_html=True)
        _render_playground_viewer(
            original_mesh,
            active_mesh,
            controls,
            viewer_options,
            preview_info,
        )
        _render_compact_metric_strip(original_mesh, active_mesh, controls)

    with right_column:
        _render_dynamic_explanation(working_mesh, controls, preview_info)
        _render_metric_cards(original_mesh, active_mesh)

    return active_mesh, controls


def _render_advanced_metrics_tab(mesh: MeshData) -> None:
    """Render detailed committed-mesh metrics and summary."""
    st.subheader("Advanced Metrics")
    st.caption(
        "All tables here compare the source original with the committed working "
        "mesh. Playground cards show the live preview instead."
    )
    _render_smoothing_metrics(
        st.session_state[ORIGINAL_MESH_KEY],
        mesh,
        st.session_state[SMOOTHING_STEPS_KEY],
    )
    _render_smoothing_history()
    _render_learning_summary(mesh)


def _render_flash_message() -> None:
    """Show and clear the one-shot message set by action callbacks."""
    flash = st.session_state.pop(FLASH_MESSAGE_KEY, None)
    if not flash:
        return
    kind, text = flash
    renderer = getattr(st, str(kind), st.info)
    renderer(str(text))


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
        "then inspect the math and metrics when needed. New here? Start with the "
        "'See shrinkage' preset in the Playground."
    )

    with st.sidebar:
        base_mesh, source_key = _render_mesh_source_sidebar()

    _sync_working_mesh(base_mesh, source_key)
    if st.session_state.pop(RESET_REQUESTED_KEY, False):
        _reset_experiment()

    working_mesh = _working_mesh()
    with st.sidebar:
        viewer_options = _render_viewer_sidebar(working_mesh)

    # Section navigation renders only the selected section (unlike st.tabs,
    # which executed every tab body - including hidden 3D viewers - on every
    # rerun and spammed the console with zero-size WebGL warnings).
    section = st.radio(
        "Section",
        LEARNING_SECTIONS,
        key=ACTIVE_SECTION_KEY,
        horizontal=True,
        label_visibility="collapsed",
    )
    _render_flash_message()

    if section == "Playground":
        _render_playground(working_mesh, viewer_options)
    elif section == "Method Comparison":
        _render_method_comparison_lab(_working_mesh())
    elif section == "Step Inspector":
        _render_step_inspector(_working_mesh())
    elif section == "Guided Learning":
        _render_guided_learning_tab()
    elif section == "Student Exercises":
        _render_student_exercises()
    else:
        _render_advanced_metrics_tab(_working_mesh())


if __name__ == "__main__":
    main()
