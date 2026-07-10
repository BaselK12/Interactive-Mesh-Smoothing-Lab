"""Algorithm regression tests for the audit fixes (AUD-003/004/009/014/015/016)."""

from __future__ import annotations

import numpy as np
import pytest

from src.mesh_core import MeshData, create_mesh_data
from src.mesh_ops import (
    add_noise,
    compute_roughness_energy,
    compute_soft_selection_weights,
    cotangent_smooth,
    find_boundary_vertices,
    inspect_cotangent_step,
    inspect_uniform_step,
    laplacian_smooth,
    laplacian_smooth_local,
    taubin_smooth,
    taubin_stability,
)
from src.sample_meshes import create_low_poly_sphere, create_plane_grid, create_cube


# ---------------------------------------------------------------------------
# Zero-effect actions (AUD-015 / AUD-016)
# ---------------------------------------------------------------------------


def test_zero_lambda_uniform_moves_nothing():
    sphere = create_low_poly_sphere()
    smoothed = laplacian_smooth(sphere, iterations=10, strength=0.0)
    assert np.allclose(smoothed.vertices, sphere.vertices)


def test_zero_strength_noise_moves_nothing():
    sphere = create_low_poly_sphere()
    noisy = add_noise(sphere, strength=0.0, seed=42)
    assert np.allclose(noisy.vertices, sphere.vertices)


def test_noise_is_deterministic_per_seed():
    sphere = create_low_poly_sphere()
    first = add_noise(sphere, strength=0.35, seed=42)
    second = add_noise(sphere, strength=0.35, seed=42)
    different = add_noise(sphere, strength=0.35, seed=43)
    assert np.allclose(first.vertices, second.vertices)
    assert not np.allclose(first.vertices, different.vertices)


# ---------------------------------------------------------------------------
# Boundary pinning and the Step Inspector (AUD-004)
# ---------------------------------------------------------------------------


def test_boundary_vertices_stay_pinned_during_smoothing():
    grid = create_plane_grid()
    boundary = sorted(find_boundary_vertices(grid))
    smoothed = laplacian_smooth(grid, iterations=5, strength=0.5, preserve_boundary=True)
    assert np.allclose(smoothed.vertices[boundary], grid.vertices[boundary])


def test_inspector_pinned_boundary_predicts_no_motion():
    grid = create_plane_grid()
    info = inspect_uniform_step(grid, vertex_index=0, lam=0.5, preserve_boundary=True)
    assert info["is_boundary_vertex"] is True
    assert info["pinned"] is True
    assert np.allclose(info["predicted_position"], grid.vertices[0])
    # The prediction must match what the smoother actually does.
    smoothed = laplacian_smooth(grid, iterations=1, strength=0.5, preserve_boundary=True)
    assert np.allclose(smoothed.vertices[0], info["predicted_position"])


def test_inspector_unpinned_matches_smoother_step():
    grid = create_plane_grid()
    interior = 12  # center vertex of the 5x5 grid
    info = inspect_uniform_step(grid, vertex_index=interior, lam=0.5, preserve_boundary=True)
    assert info["pinned"] is False
    smoothed = laplacian_smooth(grid, iterations=1, strength=0.5, preserve_boundary=True)
    assert np.allclose(smoothed.vertices[interior], info["predicted_position"])


def test_inspector_boundary_off_predicts_motion():
    grid = create_plane_grid()
    info = inspect_uniform_step(grid, vertex_index=0, lam=0.5, preserve_boundary=False)
    assert info["pinned"] is False
    assert not np.allclose(info["predicted_position"], grid.vertices[0])
    smoothed = laplacian_smooth(grid, iterations=1, strength=0.5, preserve_boundary=False)
    assert np.allclose(smoothed.vertices[0], info["predicted_position"])


def test_cotangent_inspector_honors_pinning():
    sphere = create_low_poly_sphere()  # closed: no boundary anywhere
    info = inspect_cotangent_step(sphere, vertex_index=0, strength=0.5, preserve_boundary=True)
    assert info["is_boundary_vertex"] is False
    assert info["pinned"] is False


# ---------------------------------------------------------------------------
# Taubin stability (AUD-002 / AUD-009)
# ---------------------------------------------------------------------------


def test_taubin_recommended_pair_is_stable():
    assert taubin_stability(0.5, -0.53)["stable"] is True


@pytest.mark.parametrize("lam,mu", [(0.35, -0.53), (0.05, -0.95), (0.0, -0.95)])
def test_taubin_bad_pairs_flagged_unstable(lam, mu):
    assert taubin_stability(lam, mu)["stable"] is False


def test_taubin_stable_pair_limits_size_change_on_sphere():
    sphere = create_low_poly_sphere()
    smoothed = taubin_smooth(sphere, iterations=10, lam=0.5, mu=-0.53)

    def diag(mesh):
        return float(np.linalg.norm(mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)))

    change = abs(diag(smoothed) - diag(sphere)) / diag(sphere)
    assert change < 0.10  # measured ~3.1%


# ---------------------------------------------------------------------------
# Local falloff semantics (AUD-014)
# ---------------------------------------------------------------------------


def test_falloff_identical_at_radius_two():
    grid = create_plane_grid()
    linear = compute_soft_selection_weights(grid, center_index=12, radius=2, falloff_type="linear")
    smooth = compute_soft_selection_weights(grid, center_index=12, radius=2, falloff_type="smoothstep")
    assert np.allclose(linear.weights, smooth.weights)


def _bumped_grid():
    """A plane grid with a center bump so smoothing has a feature to relax."""
    grid = create_plane_grid()
    vertices = grid.vertices.copy()
    distances = np.linalg.norm(vertices[:, :2], axis=1)
    vertices[:, 2] += 0.5 * np.exp(-((distances / 0.6) ** 2))
    return create_mesh_data(vertices, grid.faces, name="bumped", source="test")


def test_falloff_differs_at_radius_three():
    grid = _bumped_grid()
    linear = compute_soft_selection_weights(grid, center_index=12, radius=3, falloff_type="linear")
    smooth = compute_soft_selection_weights(grid, center_index=12, radius=3, falloff_type="smoothstep")
    assert not np.allclose(linear.weights, smooth.weights)
    geometry_linear = laplacian_smooth_local(
        grid, iterations=5, strength=0.6, center_index=12, radius=3, falloff_type="linear"
    )
    geometry_smooth = laplacian_smooth_local(
        grid, iterations=5, strength=0.6, center_index=12, radius=3, falloff_type="smoothstep"
    )
    assert not np.allclose(geometry_linear.vertices, geometry_smooth.vertices)


def test_outer_ring_has_zero_weight():
    grid = create_plane_grid()
    selection = compute_soft_selection_weights(grid, center_index=12, radius=2, falloff_type="linear")
    at_radius = np.isclose(selection.distances, 2.0)
    assert at_radius.any()
    assert np.all(selection.weights[at_radius] == 0.0)


# ---------------------------------------------------------------------------
# Roughness metric semantics (AUD-003)
# ---------------------------------------------------------------------------


def test_roughness_is_scale_dependent_documented_behavior():
    sphere = create_low_poly_sphere()
    half = create_mesh_data(
        vertices=sphere.vertices * 0.5,
        faces=sphere.faces,
        name="half",
        source="test",
    )
    full_value = compute_roughness_energy(sphere)["mean"]
    half_value = compute_roughness_energy(half)["mean"]
    assert half_value == pytest.approx(full_value * 0.5, rel=1.0e-9)


def test_flat_grid_roughness_is_nonzero_boundary_effect():
    grid = create_plane_grid()
    assert compute_roughness_energy(grid)["mean"] > 0.0


# ---------------------------------------------------------------------------
# Honest unsupported handling (AUD-019 / scenario 4)
# ---------------------------------------------------------------------------


def test_cotangent_unsupported_on_quads_returns_unchanged_mesh():
    cube = create_cube()
    result = cotangent_smooth(cube, iterations=5, strength=0.5)
    assert result.supported is False
    assert result.note
    assert np.allclose(result.mesh.vertices, cube.vertices)
