"""Mesh operations for normal visualization and Laplacian smoothing."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

from .mesh_core import MeshData, compute_unique_edges, create_mesh_data, invalid_mesh


EPSILON = 1.0e-12

# Global smoothing methods exposed in the UI and the comparison lab.
UNIFORM_LAPLACIAN = "Uniform Laplacian"
TAUBIN = "Taubin"
COTANGENT_LAPLACIAN = "Cotangent-weighted Laplacian"
GLOBAL_SMOOTHING_METHODS = [UNIFORM_LAPLACIAN, TAUBIN, COTANGENT_LAPLACIAN]

# Noise modes for the noisy-mesh experiment.
NOISE_ALONG_NORMALS = "Along vertex normals"
NOISE_RANDOM_3D = "Random 3D displacement"
NOISE_MODES = [NOISE_ALONG_NORMALS, NOISE_RANDOM_3D]


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


@dataclass(frozen=True)
class SmoothingResult:
    """Result of a global smoothing method, including support status."""

    mesh: MeshData
    method: str
    supported: bool
    note: str = ""


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


# ---------------------------------------------------------------------------
# Adjacency helpers shared by the smoothing methods, roughness, and inspector.
# ---------------------------------------------------------------------------


def build_adjacency_lists(mesh: MeshData) -> list[list[int]]:
    """Return one-ring neighbor indices as sorted lists (stable ordering)."""
    return [sorted(neighbors) for neighbors in build_vertex_adjacency(mesh)]


def is_triangle_mesh(mesh: MeshData) -> bool:
    """Return True when every face of a valid mesh is a triangle."""
    return bool(mesh.valid and mesh.faces and set(mesh.face_lengths) == {3})


# ---------------------------------------------------------------------------
# Roughness / smoothness energy (Phase 2)
# ---------------------------------------------------------------------------


def compute_roughness_energy(mesh: MeshData) -> dict[str, float | int | None]:
    """Measure how far each vertex sits from the average of its neighbors.

    For every vertex with at least one neighbor the local roughness is
    ``||v - mean(neighbors)||``. The mesh roughness energy is the mean of these
    per-vertex values. Isolated vertices (no neighbors) are skipped. When no
    vertex has a neighbor the metric is undefined and the values are ``None``.
    """
    result: dict[str, float | int | None] = {
        "mean": None,
        "max": None,
        "rms": None,
        "vertex_count_used": 0,
    }
    if not mesh.valid or mesh.vertex_count == 0:
        return result

    adjacency = build_adjacency_lists(mesh)
    vertices = mesh.vertices
    per_vertex: list[float] = []
    for vertex_index, neighbors in enumerate(adjacency):
        if not neighbors:
            continue
        neighbor_average = vertices[neighbors].mean(axis=0)
        per_vertex.append(float(np.linalg.norm(vertices[vertex_index] - neighbor_average)))

    if not per_vertex:
        return result

    values = np.asarray(per_vertex, dtype=float)
    result["mean"] = float(values.mean())
    result["max"] = float(values.max())
    result["rms"] = float(np.sqrt(np.mean(values**2)))
    result["vertex_count_used"] = int(values.size)
    return result


# ---------------------------------------------------------------------------
# Noisy-mesh experiment (Phase 1)
# ---------------------------------------------------------------------------


def characteristic_length(mesh: MeshData) -> float:
    """Return a representative length scale (median edge length) for a mesh."""
    if not mesh.valid or mesh.vertex_count == 0:
        return 1.0
    edges = compute_unique_edges(mesh.faces)
    if edges:
        lengths = [
            float(np.linalg.norm(mesh.vertices[a] - mesh.vertices[b])) for a, b in edges
        ]
        finite = [length for length in lengths if np.isfinite(length) and length > EPSILON]
        if finite:
            return float(np.median(finite))
    # Fall back to a fraction of the bounding-box diagonal.
    diagonal = float(np.linalg.norm(mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)))
    return max(EPSILON, diagonal * 0.1)


def add_noise(
    mesh: MeshData,
    strength: float,
    seed: int,
    mode: str = NOISE_ALONG_NORMALS,
) -> MeshData:
    """Displace vertices to simulate geometric roughness, preserving topology.

    ``strength`` (0..1) scales displacement relative to the median edge length so
    noise stays proportional to mesh resolution. Displacement is reproducible for
    a given ``seed``. In normal mode vertices move along their vertex normals; if
    normals are degenerate the affected vertices fall back to random 3D offsets.
    Every displacement is clamped so noise cannot explode the mesh.
    """
    if not mesh.valid or mesh.vertex_count == 0:
        return clone_mesh(mesh)

    safe_strength = float(np.clip(strength, 0.0, 1.0))
    scale = characteristic_length(mesh)
    amplitude = safe_strength * scale
    max_displacement = 0.5 * scale  # hard clamp: at most half an edge length

    rng = np.random.default_rng(int(seed))
    vertices = mesh.vertices.astype(float, copy=True)
    count = mesh.vertex_count

    if mode == NOISE_ALONG_NORMALS:
        normals = compute_vertex_normals(mesh, weighting="area-weighted")
        normal_lengths = np.linalg.norm(normals, axis=1)
        degenerate = normal_lengths <= EPSILON
        # Gaussian magnitude along the normal for the well-defined vertices.
        magnitudes = rng.normal(loc=0.0, scale=amplitude, size=count)
        magnitudes = np.clip(magnitudes, -max_displacement, max_displacement)
        displacement = normals * magnitudes[:, None]
        # Fallback: random 3D offset for vertices with degenerate normals.
        if np.any(degenerate):
            random_offsets = rng.normal(loc=0.0, scale=amplitude, size=(count, 3))
            random_offsets = _clamp_row_norms(random_offsets, max_displacement)
            displacement[degenerate] = random_offsets[degenerate]
    else:
        random_offsets = rng.normal(loc=0.0, scale=amplitude, size=(count, 3))
        displacement = _clamp_row_norms(random_offsets, max_displacement)

    noisy = vertices + displacement
    return copy_with_vertices(mesh, noisy, name=mesh.name)


def _clamp_row_norms(vectors: np.ndarray, max_norm: float) -> np.ndarray:
    """Clamp each row vector so its length does not exceed ``max_norm``."""
    lengths = np.linalg.norm(vectors, axis=1)
    scale = np.ones_like(lengths)
    over = lengths > max_norm
    scale[over] = max_norm / np.maximum(lengths[over], EPSILON)
    return vectors * scale[:, None]


# ---------------------------------------------------------------------------
# Taubin smoothing (Phase 4)
# ---------------------------------------------------------------------------


def taubin_smooth(
    mesh: MeshData,
    iterations: int,
    lam: float,
    mu: float,
    preserve_boundary: bool = True,
) -> MeshData:
    """Taubin lambda/mu smoothing to reduce shrinkage from plain averaging.

    Each iteration applies a positive uniform-Laplacian step with factor ``lam``
    followed by a negative correction step with factor ``mu`` (mu < 0). The
    negative step counteracts the inward pull of ordinary Laplacian smoothing so
    the mesh keeps its size while still relaxing roughness.
    """
    if not mesh.valid:
        return clone_mesh(mesh)

    safe_iterations = max(0, int(iterations))
    lam = float(lam)
    mu = float(mu)
    vertices = mesh.vertices.astype(float, copy=True)
    adjacency = build_adjacency_lists(mesh)
    boundary_vertices = find_boundary_vertices(mesh) if preserve_boundary else set()

    for _ in range(safe_iterations):
        vertices = _uniform_laplacian_step(vertices, adjacency, boundary_vertices, lam)
        vertices = _uniform_laplacian_step(vertices, adjacency, boundary_vertices, mu)

    return copy_with_vertices(mesh, vertices)


def _uniform_laplacian_step(
    vertices: np.ndarray,
    adjacency: list[list[int]],
    boundary_vertices: set[int],
    factor: float,
) -> np.ndarray:
    """One uniform-Laplacian update: v += factor * (neighbor_avg - v)."""
    next_vertices = vertices.copy()
    for vertex_index, neighbors in enumerate(adjacency):
        if vertex_index in boundary_vertices or not neighbors:
            continue
        neighbor_average = vertices[neighbors].mean(axis=0)
        next_vertices[vertex_index] = (
            vertices[vertex_index] + factor * (neighbor_average - vertices[vertex_index])
        )
    return next_vertices


# ---------------------------------------------------------------------------
# Cotangent-weighted Laplacian smoothing (Phase 5)
# ---------------------------------------------------------------------------


def cotangent_weight_map(mesh: MeshData) -> dict[int, dict[int, float]]:
    """Build clamped cotangent edge weights per vertex for a triangle mesh.

    For an edge (i, j) the weight is ``0.5 * (cot(alpha) + cot(beta))`` where
    alpha and beta are the angles opposite the edge in the two incident
    triangles (one triangle on a boundary edge). Cotangents are computed as
    ``dot(a, b) / ||cross(a, b)||`` with a guard against degenerate triangles.
    Negative weights (from obtuse triangles) are clamped to zero so the weighted
    average stays inside the neighbor hull and smoothing cannot explode.
    """
    weights: dict[tuple[int, int], float] = defaultdict(float)
    if not is_triangle_mesh(mesh):
        return {}

    vertices = mesh.vertices
    for face in mesh.faces:
        a, b, c = int(face[0]), int(face[1]), int(face[2])
        # Angle at each vertex contributes a cotangent to the opposite edge.
        weights[_edge_key(b, c)] += 0.5 * _safe_cotangent(vertices, a, b, c)
        weights[_edge_key(a, c)] += 0.5 * _safe_cotangent(vertices, b, a, c)
        weights[_edge_key(a, b)] += 0.5 * _safe_cotangent(vertices, c, a, b)

    neighbor_weights: dict[int, dict[int, float]] = defaultdict(dict)
    for (i, j), weight in weights.items():
        clamped = weight if np.isfinite(weight) and weight > 0.0 else 0.0
        neighbor_weights[i][j] = clamped
        neighbor_weights[j][i] = clamped
    return neighbor_weights


def _edge_key(a: int, b: int) -> tuple[int, int]:
    """Return an undirected edge key with the smaller index first."""
    return (a, b) if a < b else (b, a)


def _safe_cotangent(vertices: np.ndarray, apex: int, end_a: int, end_b: int) -> float:
    """Cotangent of the angle at ``apex`` in triangle (apex, end_a, end_b)."""
    edge_a = vertices[end_a] - vertices[apex]
    edge_b = vertices[end_b] - vertices[apex]
    cross_norm = float(np.linalg.norm(np.cross(edge_a, edge_b)))
    if cross_norm <= EPSILON:
        return 0.0
    return float(np.dot(edge_a, edge_b)) / cross_norm


def cotangent_smooth(
    mesh: MeshData,
    iterations: int,
    strength: float,
    preserve_boundary: bool = True,
) -> SmoothingResult:
    """Geometry-aware Laplacian smoothing using clamped cotangent weights.

    Only defined for triangle meshes. Returns a :class:`SmoothingResult` whose
    ``supported`` flag is False (with an explanatory note and an unchanged mesh)
    when the mesh is not triangle-only, so callers never produce wrong geometry
    silently.
    """
    if not mesh.valid:
        return SmoothingResult(clone_mesh(mesh), COTANGENT_LAPLACIAN, False, "Mesh is not valid.")
    if not is_triangle_mesh(mesh):
        return SmoothingResult(
            clone_mesh(mesh),
            COTANGENT_LAPLACIAN,
            False,
            "Cotangent smoothing currently supports triangle meshes only. "
            "Try Low-poly sphere or pyramid.obj.",
        )

    safe_iterations = max(0, int(iterations))
    safe_strength = float(np.clip(strength, 0.0, 1.0))
    vertices = mesh.vertices.astype(float, copy=True)
    weight_map = cotangent_weight_map(mesh)
    boundary_vertices = find_boundary_vertices(mesh) if preserve_boundary else set()

    for _ in range(safe_iterations):
        next_vertices = vertices.copy()
        for vertex_index, neighbor_weights in weight_map.items():
            if vertex_index in boundary_vertices or not neighbor_weights:
                continue
            weight_sum = sum(neighbor_weights.values())
            if weight_sum <= EPSILON:
                continue
            target = np.zeros(3, dtype=float)
            for neighbor, weight in neighbor_weights.items():
                target += weight * vertices[neighbor]
            target /= weight_sum
            next_vertices[vertex_index] = (
                vertices[vertex_index] + safe_strength * (target - vertices[vertex_index])
            )
        vertices = next_vertices

    return SmoothingResult(copy_with_vertices(mesh, vertices), COTANGENT_LAPLACIAN, True, "")


# ---------------------------------------------------------------------------
# Unified global-smoothing dispatcher (Phase 3)
# ---------------------------------------------------------------------------


def apply_global_smoothing(
    mesh: MeshData,
    method: str,
    iterations: int,
    lam: float,
    mu: float = -0.53,
    preserve_boundary: bool = True,
) -> SmoothingResult:
    """Dispatch to a global smoothing method by name, reporting support status.

    ``lam`` is used as the smoothing strength for uniform/cotangent methods and
    as the positive Taubin factor. Unsupported method/mesh combinations return a
    :class:`SmoothingResult` with ``supported=False`` and an explanatory note
    rather than raising, so the UI can warn without crashing.
    """
    if method == UNIFORM_LAPLACIAN:
        smoothed = laplacian_smooth(
            mesh, iterations=iterations, strength=lam, preserve_boundary=preserve_boundary
        )
        return SmoothingResult(smoothed, UNIFORM_LAPLACIAN, True, "")
    if method == TAUBIN:
        smoothed = taubin_smooth(
            mesh,
            iterations=iterations,
            lam=lam,
            mu=mu,
            preserve_boundary=preserve_boundary,
        )
        return SmoothingResult(smoothed, TAUBIN, True, "")
    if method == COTANGENT_LAPLACIAN:
        return cotangent_smooth(
            mesh,
            iterations=iterations,
            strength=lam,
            preserve_boundary=preserve_boundary,
        )
    return SmoothingResult(clone_mesh(mesh), method, False, f"Unknown smoothing method: {method}.")


# ---------------------------------------------------------------------------
# Smoothing step inspector (Phase 7)
# ---------------------------------------------------------------------------


def inspect_uniform_step(
    mesh: MeshData,
    vertex_index: int,
    lam: float,
) -> dict[str, object]:
    """Return the one-step uniform-Laplacian computation for a single vertex."""
    safe_index = _clamp_vertex_index(mesh, vertex_index)
    adjacency = build_adjacency_lists(mesh)
    neighbors = adjacency[safe_index] if safe_index < len(adjacency) else []
    current = mesh.vertices[safe_index].astype(float)
    info: dict[str, object] = {
        "vertex_index": safe_index,
        "current_position": current,
        "neighbors": neighbors,
        "neighbor_positions": mesh.vertices[neighbors].astype(float) if neighbors else np.empty((0, 3)),
        "valence": len(neighbors),
        "lambda": float(lam),
    }
    if not neighbors:
        info["neighbor_average"] = None
        info["displacement"] = None
        info["predicted_position"] = current
        return info

    neighbor_average = mesh.vertices[neighbors].mean(axis=0)
    delta = neighbor_average - current
    info["neighbor_average"] = neighbor_average
    info["displacement"] = delta
    info["predicted_position"] = current + float(lam) * delta
    return info


def inspect_cotangent_step(
    mesh: MeshData,
    vertex_index: int,
    strength: float,
) -> dict[str, object]:
    """Return the one-step cotangent-weighted computation for a single vertex."""
    safe_index = _clamp_vertex_index(mesh, vertex_index)
    current = mesh.vertices[safe_index].astype(float)
    info: dict[str, object] = {
        "vertex_index": safe_index,
        "current_position": current,
        "supported": is_triangle_mesh(mesh),
        "strength": float(strength),
    }
    if not is_triangle_mesh(mesh):
        info["note"] = (
            "Cotangent weights are defined for triangle meshes only. "
            "Try Low-poly sphere or pyramid.obj."
        )
        return info

    weight_map = cotangent_weight_map(mesh)
    neighbor_weights = weight_map.get(safe_index, {})
    neighbors = sorted(neighbor_weights.keys())
    weights = np.asarray([neighbor_weights[n] for n in neighbors], dtype=float)
    weight_sum = float(weights.sum())
    info["neighbors"] = neighbors
    info["weights"] = weights
    info["weight_sum"] = weight_sum
    if not neighbors or weight_sum <= EPSILON:
        info["normalized_weights"] = np.zeros(len(neighbors))
        info["weighted_target"] = current
        info["predicted_position"] = current
        info["note"] = "No positive cotangent weights; vertex would not move."
        return info

    normalized = weights / weight_sum
    weighted_target = (mesh.vertices[neighbors] * normalized[:, None]).sum(axis=0)
    info["normalized_weights"] = normalized
    info["weighted_target"] = weighted_target
    info["predicted_position"] = current + float(strength) * (weighted_target - current)
    return info


def inspect_local_step(
    mesh: MeshData,
    vertex_index: int,
    center_index: int,
    radius: int,
    strength: float,
    falloff_type: str = "linear",
) -> dict[str, object]:
    """Return the one-step local/soft-smoothing computation for a single vertex."""
    base = inspect_uniform_step(mesh, vertex_index, lam=strength)
    soft = compute_soft_selection_weights(
        mesh, center_index=center_index, radius=radius, falloff_type=falloff_type
    )
    safe_index = base["vertex_index"]
    local_weight = float(soft.weights[safe_index]) if safe_index < soft.weights.size else 0.0
    graph_distance = float(soft.distances[safe_index]) if safe_index < soft.distances.size else float("inf")
    base["center_vertex"] = soft.center_index
    base["graph_distance_from_center"] = graph_distance
    base["local_weight"] = local_weight
    delta = base.get("displacement")
    current = base["current_position"]
    if delta is None:
        base["effective_movement"] = None
        base["predicted_position"] = current
    else:
        effective = float(strength) * local_weight * np.asarray(delta)
        base["effective_movement"] = effective
        base["predicted_position"] = current + effective
    return base


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
