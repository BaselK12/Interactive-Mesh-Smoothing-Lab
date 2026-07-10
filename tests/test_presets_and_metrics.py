"""Preset and metric regression tests for the audit fixes (AUD-002/018)."""

from __future__ import annotations

import numpy as np
import trimesh

from src.mesh_core import create_mesh_data
from src.mesh_metrics import compute_shape_metrics, percent_change
from src.mesh_ops import add_noise, compute_roughness_energy, taubin_smooth
from src.sample_meshes import create_low_poly_sphere


def _diag(mesh) -> float:
    return float(np.linalg.norm(mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)))


def test_remove_noise_preset_actually_denoises():
    """AUD-002 regression: the shipped preset values must reduce roughness.

    The preset is: noisy Low-poly sphere (strength 0.35, seed 42) smoothed by
    Taubin with lambda=0.5, mu=-0.53, 10 iterations. The old lambda=0.35 made
    the sphere ROUGHER (+6.6%) and LARGER (+24% AABB) than the noisy input.
    """
    clean = create_low_poly_sphere()
    noisy = add_noise(clean, strength=0.35, seed=42)
    smoothed = taubin_smooth(noisy, iterations=10, lam=0.5, mu=-0.53, preserve_boundary=True)

    rough_noisy = compute_roughness_energy(noisy)["mean"]
    rough_smoothed = compute_roughness_energy(smoothed)["mean"]
    # Roughness must drop meaningfully versus the noisy stage (measured ~-19%).
    assert rough_smoothed < rough_noisy * 0.90

    # Size must stay close to the noisy input (measured ~-8%).
    size_change = abs(_diag(smoothed) - _diag(noisy)) / _diag(noisy)
    assert size_change < 0.15

    # And the result must not be rougher than the clean mesh by more than a hair.
    rough_clean = compute_roughness_energy(clean)["mean"]
    assert rough_smoothed < rough_clean * 1.05


def test_app_preset_uses_the_validated_taubin_pair():
    import app  # safe: module-level code only defines constants/functions

    from src.mesh_ops import taubin_stability

    assert app.TAUBIN_STABLE_LAMBDA == 0.5
    assert taubin_stability(app.TAUBIN_STABLE_LAMBDA, app.TAUBIN_DEFAULT_MU)["stable"]


# ---------------------------------------------------------------------------
# Volume trust gate (AUD-018)
# ---------------------------------------------------------------------------

_TET_FACES = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
_TET_VERTICES = [
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]


def test_volume_reported_for_consistent_tetrahedron():
    tet = create_mesh_data(_TET_VERTICES, _TET_FACES, name="tet", source="test")
    metrics = compute_shape_metrics(tet)
    assert metrics["volume"] is not None
    assert abs(metrics["volume"] - 1.0 / 6.0) < 1.0e-9


def test_volume_gated_for_inconsistent_winding():
    """A watertight tet with one flipped face used to report volume 2.1667 (real: 0.1667)."""
    faces = [list(face) for face in _TET_FACES]
    faces[2] = faces[2][::-1]
    shifted = (np.asarray(_TET_VERTICES) + np.array([2.0, 2.0, 2.0])).tolist()
    bad = create_mesh_data(shifted, faces, name="bad-tet", source="test")
    probe = trimesh.Trimesh(vertices=np.asarray(shifted), faces=np.asarray(faces), process=False)
    assert probe.is_watertight and not probe.is_winding_consistent
    metrics = compute_shape_metrics(bad)
    assert metrics["volume"] is None


def test_volume_gated_for_cancelling_components():
    """Two disjoint, oppositely wound tets used to report volume 0 (real total: 1/3)."""
    verts = np.vstack([np.asarray(_TET_VERTICES), np.asarray(_TET_VERTICES) + np.array([3.0, 0.0, 0.0])])
    flipped = [list(reversed([i + 4 for i in face])) for face in _TET_FACES]
    faces = [list(face) for face in _TET_FACES] + flipped
    two = create_mesh_data(verts.tolist(), faces, name="two-tets", source="test")
    metrics = compute_shape_metrics(two)
    assert metrics["volume"] is None


def test_percent_change_guards():
    assert percent_change(None, 1.0) is None
    assert percent_change(0.0, 1.0) is None
    assert percent_change(2.0, 3.0) == 50.0
