"""Mesh operations for normal visualization and Laplacian smoothing."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

from .mesh_core import MeshData, compute_unique_edges, create_mesh_data, invalid_mesh


EPSILON = 1.0e-12


@dataclass(frozen=True)
class FaceNormalData:
    """Face centers, unit normals, and polygon areas."""

    centers: np.ndarray
    normals: np.ndarray
    areas: np.ndarray


@dataclass(frozen=True)
class SoftSelectionData:
    """Graph distances and local smoothing weights from a center vertex."""

    center_index: int
    radius: int
    falloff_type: str
    distances: np.ndarray
    weights: np.ndarray


def copy_with_vertices(mesh: MeshData, vertices: np.ndarray, name: str | None = None) -> MeshData:
    """Return a mesh copy with the same faces and source but different vertices."""
    return create_mesh_data(
        vertices=vertices,
        faces=mesh.faces,
        name=name or mesh.name,
        source=mesh.source,
    )


def clone_mesh(mesh: MeshData) -> MeshData:
    """Return a deep copy of a mesh wrapper."""
    if not mesh.valid:
        return invalid_mesh(mesh.error_message, name=mesh.name, source=mesh.source)
    return create_mesh_data(
        vertices=mesh.vertices.copy(),
        faces=[face.copy() for face in mesh.faces],
        name=mesh.name,
        source=mesh.source,
    )


def compute_face_normals(mesh: MeshData) -> FaceNormalData:
    """Compute face centers and safely normalized polygon face normals.

    For polygons with more than three vertices, the area vector is accumulated
    from a triangle fan rooted at the first vertex. The resulting normal follows
    the face winding order. Degenerate faces receive a zero normal.
    """
    centers = np.zeros((mesh.face_count, 3), dtype=float)
    normals = np.zeros((mesh.face_count, 3), dtype=float)
    areas = np.zeros(mesh.face_count, dtype=float)

    if not mesh.valid:
        return FaceNormalData(centers=centers, normals=normals, areas=areas)

    for face_index, face in enumerate(mesh.faces):
        face_vertices = mesh.vertices[np.asarray(face, dtype=int)]
        centers[face_index] = face_vertices.mean(axis=0)
        if len(face) < 3:
            continue

        origin = face_vertices[0]
        area_vector = np.zeros(3, dtype=float)
        for vertex_index in range(1, len(face) - 1):
            edge_a = face_vertices[vertex_index] - origin
            edge_b = face_vertices[vertex_index + 1] - origin
            area_vector += np.cross(edge_a, edge_b)

        length = float(np.linalg.norm(area_vector))
        if length <= EPSILON:
            continue
        normals[face_index] = area_vector / length
        areas[face_index] = 0.5 * length

    return FaceNormalData(centers=centers, normals=normals, areas=areas)


def compute_vertex_normals(mesh: MeshData, weighting: str = "average") -> np.ndarray:
    """Estimate vertex normals by averaging incident face normals.

    ``average`` gives each nondegenerate incident face equal influence.
    ``area-weighted`` multiplies each face normal by polygon area before the
    final normalization. Isolated vertices and degenerate-only vertices receive
    a zero normal.
    """
    vertex_normals = np.zeros((mesh.vertex_count, 3), dtype=float)
    if not mesh.valid:
        return vertex_normals

    face_data = compute_face_normals(mesh)
    use_area_weighting = weighting == "area-weighted"

    for face_index, face in enumerate(mesh.faces):
        face_normal = face_data.normals[face_index]
        if np.linalg.norm(face_normal) <= EPSILON:
            continue
        weight = face_data.areas[face_index] if use_area_weighting else 1.0
        for vertex_index in face:
            vertex_normals[vertex_index] += face_normal * weight

    return _normalize_rows(vertex_normals)


def build_vertex_adjacency(mesh: MeshData) -> list[set[int]]:
    """Build one-ring vertex adjacency from polygon face boundary edges."""
    adjacency = [set() for _ in range(mesh.vertex_count)]
    for edge_start, edge_end in compute_unique_edges(mesh.faces):
        adjacency[edge_start].add(edge_end)
        adjacency[edge_end].add(edge_start)
    return adjacency


def find_boundary_vertices(mesh: MeshData) -> set[int]:
    """Return vertices touching edges that belong to exactly one face."""
    edge_counts: dict[tuple[int, int], int] = defaultdict(int)
    for face in mesh.faces:
        for edge_start, edge_end in _face_edges(face):
            edge_counts[tuple(sorted((edge_start, edge_end)))] += 1

    boundary_vertices: set[int] = set()
    for (edge_start, edge_end), count in edge_counts.items():
        if count == 1:
            boundary_vertices.update((edge_start, edge_end))
    return boundary_vertices


def laplacian_smooth(
    mesh: MeshData,
    iterations: int,
    strength: float,
    preserve_boundary: bool = True,
) -> MeshData:
    """Smooth vertex positions by moving each vertex toward neighbor average.

    The update formula is:
    ``new_position = old_position + strength * (neighbor_average - old_position)``.
    Connectivity is reused unchanged, so face count and edge count are preserved.
    Boundary vertices are detected from one-face edges and can be held fixed.
    """
    if not mesh.valid:
        return clone_mesh(mesh)

    safe_iterations = max(0, int(iterations))
    safe_strength = float(np.clip(strength, 0.0, 1.0))
    vertices = mesh.vertices.astype(float, copy=True)
    adjacency = build_vertex_adjacency(mesh)
    boundary_vertices = find_boundary_vertices(mesh) if preserve_boundary else set()

    for _ in range(safe_iterations):
        next_vertices = vertices.copy()
        for vertex_index, neighbors in enumerate(adjacency):
            if vertex_index in boundary_vertices or not neighbors:
                continue
            neighbor_average = vertices[list(neighbors)].mean(axis=0)
            next_vertices[vertex_index] = (
                vertices[vertex_index]
                + safe_strength * (neighbor_average - vertices[vertex_index])
            )
        vertices = next_vertices

    return copy_with_vertices(mesh, vertices)


def compute_soft_selection_weights(
    mesh: MeshData,
    center_index: int,
    radius: int,
    falloff_type: str = "linear",
) -> SoftSelectionData:
    """Compute graph-distance soft-selection weights from a center vertex."""
    safe_center = _clamp_vertex_index(mesh, center_index)
    safe_radius = max(0, int(radius))
    distances = graph_distances_from_vertex(mesh, safe_center)
    weights = np.zeros(mesh.vertex_count, dtype=float)

    if not mesh.valid or mesh.vertex_count == 0:
        return SoftSelectionData(
            center_index=safe_center,
            radius=safe_radius,
            falloff_type=falloff_type,
            distances=distances,
            weights=weights,
        )

    if safe_radius == 0:
        weights[safe_center] = 1.0
    else:
        reachable = np.isfinite(distances)
        within_radius = reachable & (distances <= safe_radius)
        t = np.zeros(mesh.vertex_count, dtype=float)
        t[within_radius] = np.clip(distances[within_radius] / safe_radius, 0.0, 1.0)
        if falloff_type == "smoothstep":
            smooth = 3.0 * t**2 - 2.0 * t**3
            weights[within_radius] = 1.0 - smooth[within_radius]
        else:
            weights[within_radius] = np.maximum(0.0, 1.0 - t[within_radius])

    weights[weights <= EPSILON] = 0.0
    return SoftSelectionData(
        center_index=safe_center,
        radius=safe_radius,
        falloff_type="smoothstep" if falloff_type == "smoothstep" else "linear",
        distances=distances,
        weights=weights,
    )


def graph_distances_from_vertex(mesh: MeshData, center_index: int) -> np.ndarray:
    """Return unweighted one-ring graph distances from one vertex."""
    distances = np.full(mesh.vertex_count, np.inf, dtype=float)
    if not mesh.valid or mesh.vertex_count == 0:
        return distances

    safe_center = _clamp_vertex_index(mesh, center_index)
    adjacency = build_vertex_adjacency(mesh)
    distances[safe_center] = 0.0
    queue: deque[int] = deque([safe_center])

    while queue:
        vertex_index = queue.popleft()
        next_distance = distances[vertex_index] + 1.0
        for neighbor in adjacency[vertex_index]:
            if np.isfinite(distances[neighbor]):
                continue
            distances[neighbor] = next_distance
            queue.append(neighbor)

    return distances


def laplacian_smooth_local(
    mesh: MeshData,
    iterations: int,
    strength: float,
    center_index: int,
    radius: int,
    falloff_type: str = "linear",
    preserve_boundary: bool = True,
) -> MeshData:
    """Apply neighbor-average smoothing with graph-distance soft weights."""
    if not mesh.valid:
        return clone_mesh(mesh)

    safe_iterations = max(0, int(iterations))
    safe_strength = float(np.clip(strength, 0.0, 1.0))
    vertices = mesh.vertices.astype(float, copy=True)
    adjacency = build_vertex_adjacency(mesh)
    boundary_vertices = find_boundary_vertices(mesh) if preserve_boundary else set()
    soft_selection = compute_soft_selection_weights(
        mesh,
        center_index=center_index,
        radius=radius,
        falloff_type=falloff_type,
    )

    for _ in range(safe_iterations):
        next_vertices = vertices.copy()
        for vertex_index, neighbors in enumerate(adjacency):
            local_weight = soft_selection.weights[vertex_index]
            if (
                vertex_index in boundary_vertices
                or not neighbors
                or local_weight <= EPSILON
            ):
                continue
            neighbor_average = vertices[list(neighbors)].mean(axis=0)
            next_vertices[vertex_index] = (
                vertices[vertex_index]
                + safe_strength * local_weight * (neighbor_average - vertices[vertex_index])
            )
        vertices = next_vertices

    return copy_with_vertices(mesh, vertices)


def affected_soft_selection_vertices(
    mesh: MeshData,
    center_index: int,
    radius: int,
    falloff_type: str = "linear",
    preserve_boundary: bool = True,
) -> dict[str, int | float | str]:
    """Return a compact summary of the local smoothing affected region."""
    soft_selection = compute_soft_selection_weights(
        mesh,
        center_index=center_index,
        radius=radius,
        falloff_type=falloff_type,
    )
    nonzero = soft_selection.weights > EPSILON
    boundary_vertices = find_boundary_vertices(mesh) if preserve_boundary else set()
    movable_nonzero = [
        vertex_index
        for vertex_index, is_nonzero in enumerate(nonzero)
        if is_nonzero and vertex_index not in boundary_vertices
    ]
    included_distances = soft_selection.distances[nonzero]
    finite_included = included_distances[np.isfinite(included_distances)]
    max_distance = float(finite_included.max()) if finite_included.size else 0.0

    return {
        "center_vertex": soft_selection.center_index,
        "radius": soft_selection.radius,
        "falloff": soft_selection.falloff_type,
        "affected_vertices": int(nonzero.sum()),
        "movable_affected_vertices": len(movable_nonzero),
        "max_graph_distance_included": max_distance,
    }


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    """Safely normalize each vector row, leaving near-zero rows unchanged."""
    normalized = np.zeros_like(vectors, dtype=float)
    lengths = np.linalg.norm(vectors, axis=1)
    nonzero = lengths > EPSILON
    normalized[nonzero] = vectors[nonzero] / lengths[nonzero, None]
    return normalized


def _face_edges(face: list[int]) -> list[tuple[int, int]]:
    """Return directed boundary edges for one polygon face."""
    return [
        (int(face[index]), int(face[(index + 1) % len(face)]))
        for index in range(len(face))
        if face[index] != face[(index + 1) % len(face)]
    ]


def _clamp_vertex_index(mesh: MeshData, vertex_index: int) -> int:
    """Clamp a vertex index to the valid mesh range."""
    if mesh.vertex_count <= 0:
        return 0
    return int(np.clip(int(vertex_index), 0, mesh.vertex_count - 1))
