"""Release-QA regressions that exercise the remaining required behavior.

These tests intentionally combine small numerical checks with Streamlit's real
``AppTest`` harness.  The latter catches state/UI wiring failures that a pure
geometry test cannot see.
"""

from __future__ import annotations

import numpy as np

from streamlit.testing.v1 import AppTest

from src.mesh_core import create_mesh_data
from src.mesh_ops import (
    cotangent_smooth,
    inspect_local_step,
    laplacian_smooth,
    laplacian_smooth_local,
)
from src.sample_meshes import create_low_poly_sphere, create_plane_grid


APP = "app.py"
TIMEOUT = 60


def _make() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception
    return at


def _element(elements, label: str):
    matches = [element for element in elements if element.label == label]
    assert matches, f"element not found: {label!r}"
    return matches[0]


def _run(at: AppTest) -> AppTest:
    at.run()
    assert not at.exception
    return at


def test_uniform_formula_uses_the_old_neighbor_average_synchronously():
    """One Uniform step must implement v + lambda * (mean(N(v)) - v)."""
    triangle = create_mesh_data(
        vertices=[[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
        faces=[[0, 1, 2]],
        name="triangle",
        source="test",
    )

    result = laplacian_smooth(
        triangle, iterations=1, strength=0.25, preserve_boundary=False
    )

    # Vertex 0 sees the original positions of vertices 1 and 2, whose mean is
    # (1, 1, 0), so a quarter step ends at (0.25, 0.25, 0).
    assert np.allclose(result.vertices[0], [0.25, 0.25, 0.0])


def test_cotangent_supported_triangle_mesh_moves_without_changing_topology():
    sphere = create_low_poly_sphere()

    result = cotangent_smooth(sphere, iterations=1, strength=0.25)

    assert result.supported is True
    assert not np.allclose(result.mesh.vertices, sphere.vertices)
    assert result.mesh.vertex_count == sphere.vertex_count
    assert result.mesh.face_count == sphere.face_count
    assert result.mesh.unique_edges == sphere.unique_edges


def test_local_step_inspector_matches_the_actual_local_algorithm():
    """The reported graph weight/effective move must predict one local step."""
    grid = create_plane_grid()
    vertices = grid.vertices.copy()
    vertices[12, 2] = 0.5
    bumped = create_mesh_data(vertices, grid.faces, name="bumped grid", source="test")

    info = inspect_local_step(
        bumped,
        vertex_index=12,
        center_index=12,
        radius=3,
        strength=0.5,
        falloff_type="smoothstep",
        preserve_boundary=True,
    )
    result = laplacian_smooth_local(
        bumped,
        iterations=1,
        strength=0.5,
        center_index=12,
        radius=3,
        falloff_type="smoothstep",
        preserve_boundary=True,
    )

    assert info["graph_distance_from_center"] == 0.0
    assert info["local_weight"] == 1.0
    assert np.allclose(result.vertices[12], info["predicted_position"])


def test_source_switch_keeps_the_step_inspector_index_valid():
    at = _make()
    at.session_state["sample_mesh"] = "Low-poly sphere"
    _run(at)
    at.session_state["active_learning_section"] = "Step Inspector"
    _run(at)
    _element(at.slider, "Vertex index to inspect").set_value(41)
    _run(at)
    assert at.session_state["inspect_vertex_index"] == 41

    # Switching to the eight-vertex cube must not leave the old sphere index
    # behind.  The app deliberately resets it to zero, which is valid.
    at.session_state["sample_mesh"] = "Cube"
    _run(at)
    assert 0 <= at.session_state["inspect_vertex_index"] < 8
    assert _element(at.slider, "Vertex index to inspect").value == 0


def test_invalid_obj_upload_safely_falls_back_to_the_cube():
    at = _make()
    _element(at.radio, "Choose source").set_value("Upload OBJ file")
    _run(at)
    assert len(at.file_uploader) == 1

    at.file_uploader[0].set_value(("invalid.obj", b"not an OBJ mesh", "text/plain"))
    _run(at)

    assert at.session_state["working_mesh"].name == "Cube"
    assert at.session_state["original_mesh"].name == "Cube"
    assert any("did not contain usable mesh faces" in str(item.value) for item in at.error)


def test_viewer_controls_are_disabled_when_the_view_cannot_use_them():
    at = _make()
    _element(at.selectbox, "Playground view").set_value("Overlay")
    _run(at)

    assert _element(at.selectbox, "Display mode").disabled
    assert _element(at.checkbox, "Show face normals").disabled
    assert _element(at.checkbox, "Show vertex normals").disabled
    assert _element(at.slider, "Normal length").disabled

    _element(at.selectbox, "Playground view").set_value("Side-by-side")
    _run(at)
    assert not _element(at.selectbox, "Display mode").disabled
    assert _element(at.checkbox, "Show face normals").disabled
    assert _element(at.checkbox, "Show vertex normals").disabled


def test_noise_settings_are_contextually_disabled_until_noise_is_enabled():
    at = _make()
    assert _element(at.checkbox, "Noise enabled").value is False
    assert _element(at.slider, "Noise strength").disabled
    assert _element(at.number_input, "Noise seed").disabled
    assert _element(at.selectbox, "Noise mode").disabled

    _element(at.checkbox, "Noise enabled").set_value(True)
    _run(at)
    assert not _element(at.slider, "Noise strength").disabled
    assert not _element(at.number_input, "Noise seed").disabled
    assert not _element(at.selectbox, "Noise mode").disabled


def test_method_comparison_never_mutates_either_live_mesh_state():
    at = _make()
    working_before = at.session_state["working_mesh"].vertices.copy()
    original_before = at.session_state["original_mesh"].vertices.copy()

    at.session_state["active_learning_section"] = "Method Comparison"
    _run(at)
    _element(at.button, "Run comparison from the selected input").click()
    _run(at)

    assert at.session_state["method_comparison_rows"]
    assert np.array_equal(at.session_state["working_mesh"].vertices, working_before)
    assert np.array_equal(at.session_state["original_mesh"].vertices, original_before)


def test_taubin_zero_lambda_is_exposed_as_an_unstable_negative_only_pass():
    """Unlike Uniform lambda=0, Taubin's negative mu pass still moves vertices."""
    at = _make()
    at.session_state["smoothing_method"] = "Taubin"
    at.session_state["smoothing_strength"] = 0.0
    at.session_state["smoothing_iterations"] = 1
    _run(at)

    warnings = " ".join(str(item.value) for item in at.warning)
    assert "Unstable Taubin pair" in warnings
