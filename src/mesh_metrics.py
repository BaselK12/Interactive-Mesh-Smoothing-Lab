"""Geometry metrics for smoothing observation and shrinkage tracking."""

from __future__ import annotations

import numpy as np
import trimesh

from .mesh_core import MeshData


EPSILON = 1.0e-12


def compare_meshes(
    original: MeshData,
    current: MeshData,
    smoothing_iterations: int,
) -> dict[str, object]:
    """Compare original and current meshes for the lecture metrics panel."""
    original_shape = compute_shape_metrics(original)
    current_shape = compute_shape_metrics(current)
    average_displacement, max_displacement = compute_vertex_displacement(
        original,
        current,
    )

    return {
        "smoothing_iterations": int(smoothing_iterations),
        "original": original_shape,
        "current": current_shape,
        "average_displacement": average_displacement,
        "max_displacement": max_displacement,
        "bounding_box_percent_change": percent_change(
            original_shape["bounding_box_diagonal"],
            current_shape["bounding_box_diagonal"],
        ),
        "surface_area_percent_change": percent_change(
            original_shape["surface_area"],
            current_shape["surface_area"],
        ),
        "volume_percent_change": percent_change(
            original_shape["volume"],
            current_shape["volume"],
        ),
    }


def compute_shape_metrics(mesh: MeshData) -> dict[str, int | float | bool | None]:
    """Compute topology counts and geometric size measurements for one mesh."""
    metrics: dict[str, int | float | bool | None] = {
        "vertex_count": mesh.vertex_count,
        "face_count": mesh.face_count,
        "unique_edge_count": len(mesh.unique_edges) if mesh.valid else 0,
        "bounding_box_diagonal": None,
        "surface_area": None,
        "volume": None,
        "is_watertight": False,
    }

    if not mesh.valid or mesh.vertex_count == 0:
        return metrics

    metrics["bounding_box_diagonal"] = _bounding_box_diagonal(mesh.vertices)

    trimesh_mesh = _to_trimesh(mesh)
    if trimesh_mesh is None:
        return metrics

    metrics["surface_area"] = _finite_float(trimesh_mesh.area)
    metrics["is_watertight"] = bool(trimesh_mesh.is_watertight)
    if metrics["is_watertight"]:
        metrics["volume"] = _finite_float(abs(float(trimesh_mesh.volume)))

    return metrics


def compute_vertex_displacement(
    original: MeshData,
    current: MeshData,
) -> tuple[float | None, float | None]:
    """Return average and max vertex displacement, or N/A-compatible None."""
    if (
        not original.valid
        or not current.valid
        or original.vertex_count == 0
        or original.vertex_count != current.vertex_count
    ):
        return None, None

    distances = np.linalg.norm(current.vertices - original.vertices, axis=1)
    return _finite_float(distances.mean()), _finite_float(distances.max())


def percent_change(original: object, current: object) -> float | None:
    """Return percent change from original to current, or None when undefined."""
    if original is None or current is None:
        return None

    try:
        original_value = float(original)
        current_value = float(current)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(original_value) or not np.isfinite(current_value):
        return None
    if abs(original_value) <= EPSILON:
        return None
    return 100.0 * (current_value - original_value) / original_value


def _bounding_box_diagonal(vertices: np.ndarray) -> float | None:
    """Return the diagonal length of the axis-aligned bounding box."""
    if vertices.size == 0:
        return None
    minimum = vertices.min(axis=0)
    maximum = vertices.max(axis=0)
    return _finite_float(np.linalg.norm(maximum - minimum))


def _to_trimesh(mesh: MeshData) -> trimesh.Trimesh | None:
    """Convert polygon mesh data to a triangle mesh for area and volume metrics."""
    triangles = _triangulate_faces(mesh.faces)
    if not triangles:
        return None

    try:
        return trimesh.Trimesh(
            vertices=mesh.vertices,
            faces=np.asarray(triangles, dtype=np.int64),
            process=False,
        )
    except Exception:
        return None


def _triangulate_faces(faces: list[list[int]]) -> list[list[int]]:
    """Triangulate polygon faces with a simple fan, preserving geometry only."""
    triangles: list[list[int]] = []
    for face in faces:
        if len(face) < 3:
            continue
        for index in range(1, len(face) - 1):
            triangles.append([int(face[0]), int(face[index]), int(face[index + 1])])
    return triangles


def _finite_float(value: object) -> float | None:
    """Convert finite numeric values to float and reject NaN/inf."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result
