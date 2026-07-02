"""Core mesh representation, topology helpers, and OBJ loading."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

import numpy as np
import trimesh


MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@dataclass
class MeshData:
    """Small mesh wrapper shared by loading, statistics, and visualization code."""

    vertices: np.ndarray
    faces: list[list[int]]
    name: str
    source: str
    valid: bool = True
    error_message: str = ""

    @property
    def vertex_count(self) -> int:
        """Return the number of vertices."""
        return int(self.vertices.shape[0]) if self.vertices.ndim == 2 else 0

    @property
    def face_count(self) -> int:
        """Return the number of polygon faces."""
        return len(self.faces)

    @property
    def face_lengths(self) -> list[int]:
        """Return the number of vertices used by each face."""
        return [len(face) for face in self.faces]

    @property
    def unique_edges(self) -> set[tuple[int, int]]:
        """Return undirected unique edges derived from polygon face loops."""
        return compute_unique_edges(self.faces)

    @property
    def mesh_type(self) -> str:
        """Classify the mesh by polygon face size."""
        if not self.valid or not self.faces:
            return "unknown/unsupported"

        lengths = set(self.face_lengths)
        if lengths == {3}:
            return "triangle mesh"
        if lengths == {4}:
            return "quad mesh"
        return "mixed polygon mesh"

    def statistics(self) -> dict[str, int | str]:
        """Return the statistics shown in the app sidebar."""
        return {
            "vertices": self.vertex_count,
            "faces": self.face_count,
            "unique_edges": len(self.unique_edges),
            "mesh_type": self.mesh_type,
        }


def create_mesh_data(
    vertices: Iterable[Iterable[float]],
    faces: Iterable[Iterable[int]],
    name: str,
    source: str,
) -> MeshData:
    """Create a validated mesh from vertex and face arrays."""
    try:
        vertex_array = _coerce_vertices(vertices)
        face_list = _coerce_faces(faces)
        _validate_faces(vertex_array, face_list)
        return MeshData(
            vertices=vertex_array,
            faces=face_list,
            name=name,
            source=source,
            valid=True,
        )
    except ValueError as exc:
        return invalid_mesh(str(exc), name=name, source=source)


def invalid_mesh(message: str, name: str = "Invalid mesh", source: str = "unknown") -> MeshData:
    """Create an invalid mesh result that can be safely shown in the UI."""
    return MeshData(
        vertices=np.empty((0, 3), dtype=float),
        faces=[],
        name=name,
        source=source,
        valid=False,
        error_message=message,
    )


def compute_unique_edges(faces: Iterable[Iterable[int]]) -> set[tuple[int, int]]:
    """Compute undirected unique edges from the boundary loop of every face."""
    edges: set[tuple[int, int]] = set()
    for raw_face in faces:
        face = [int(index) for index in raw_face]
        if len(face) < 2:
            continue
        for index, start in enumerate(face):
            end = face[(index + 1) % len(face)]
            if start == end:
                continue
            edges.add(tuple(sorted((start, end))))
    return edges


def load_obj_mesh(file_bytes: bytes, file_name: str) -> MeshData:
    """Load an uploaded OBJ file with Trimesh and convert it to MeshData."""
    if not file_name.lower().endswith(".obj"):
        return invalid_mesh("Only .obj files are supported.", name=file_name, source="upload")
    if not file_bytes:
        return invalid_mesh("The uploaded OBJ file is empty.", name=file_name, source="upload")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return invalid_mesh(
            "The uploaded OBJ file is larger than the 15 MB safety limit.",
            name=file_name,
            source="upload",
        )

    try:
        loaded = trimesh.load(
            BytesIO(file_bytes),
            file_type="obj",
            process=False,
            force="scene",
        )
        mesh = _scene_to_trimesh(loaded)
        if mesh is None or mesh.vertices.size == 0 or mesh.faces.size == 0:
            return invalid_mesh(
                "The uploaded OBJ did not contain usable mesh faces.",
                name=file_name,
                source="upload",
            )
        return create_mesh_data(
            vertices=mesh.vertices,
            faces=mesh.faces,
            name=file_name,
            source="upload",
        )
    except Exception as exc:
        return invalid_mesh(
            f"Could not load OBJ file: {exc}",
            name=file_name,
            source="upload",
        )


def _scene_to_trimesh(loaded: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh | None:
    """Return one Trimesh from a Trimesh or a Scene of compatible meshes."""
    if isinstance(loaded, trimesh.Trimesh):
        return loaded

    if isinstance(loaded, trimesh.Scene):
        meshes = [
            geometry
            for geometry in loaded.geometry.values()
            if isinstance(geometry, trimesh.Trimesh) and geometry.faces.size > 0
        ]
        if not meshes:
            return None
        return trimesh.util.concatenate(meshes)

    return None


def _coerce_vertices(vertices: Iterable[Iterable[float]]) -> np.ndarray:
    """Convert vertices to a finite Nx3 float array."""
    vertex_array = np.asarray(vertices, dtype=float)
    if vertex_array.ndim != 2 or vertex_array.shape[0] == 0:
        raise ValueError("Mesh vertices must be a non-empty 2D array.")
    if vertex_array.shape[1] < 3:
        raise ValueError("Mesh vertices must have at least three coordinates.")
    vertex_array = vertex_array[:, :3]
    if not np.isfinite(vertex_array).all():
        raise ValueError("Mesh vertices must contain only finite coordinates.")
    return vertex_array


def _coerce_faces(faces: Iterable[Iterable[int]]) -> list[list[int]]:
    """Convert faces to a list of polygon index loops."""
    face_list = [[int(index) for index in face] for face in faces]
    if not face_list:
        raise ValueError("Mesh faces must be non-empty.")
    if any(len(face) < 3 for face in face_list):
        raise ValueError("Every mesh face must use at least three vertices.")
    return face_list


def _validate_faces(vertices: np.ndarray, faces: list[list[int]]) -> None:
    """Validate face indices against the vertex array."""
    vertex_count = vertices.shape[0]
    for face in faces:
        for index in face:
            if index < 0 or index >= vertex_count:
                raise ValueError("Mesh face indices are outside the vertex array.")
