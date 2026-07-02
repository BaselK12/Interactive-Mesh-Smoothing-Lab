"""Built-in sample meshes used by the Streamlit app."""

from __future__ import annotations

import math

import numpy as np
import trimesh

from .mesh_core import MeshData, create_mesh_data


def sample_mesh_names() -> list[str]:
    """Return sample mesh names in UI order."""
    return ["Cube", "Plane/grid", "Low-poly sphere", "Cylinder"]


def create_sample_mesh(name: str) -> MeshData:
    """Create one built-in sample mesh by name."""
    factories = {
        "Cube": create_cube,
        "Plane/grid": create_plane_grid,
        "Low-poly sphere": create_low_poly_sphere,
        "Cylinder": create_cylinder,
    }
    return factories.get(name, create_cube)()


def create_cube() -> MeshData:
    """Create a quad-faced cube."""
    vertices = np.array(
        [
            [-0.5, -0.5, -0.5],
            [0.5, -0.5, -0.5],
            [0.5, 0.5, -0.5],
            [-0.5, 0.5, -0.5],
            [-0.5, -0.5, 0.5],
            [0.5, -0.5, 0.5],
            [0.5, 0.5, 0.5],
            [-0.5, 0.5, 0.5],
        ],
        dtype=float,
    )
    faces = [
        [0, 3, 2, 1],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
    ]
    return create_mesh_data(vertices, faces, name="Cube", source="built-in")


def create_plane_grid(subdivisions: int = 4, size: float = 2.0) -> MeshData:
    """Create a flat quad grid in the XY plane."""
    steps = subdivisions + 1
    half_size = size / 2.0
    coordinates = np.linspace(-half_size, half_size, steps)
    vertices = np.array([[x, y, 0.0] for y in coordinates for x in coordinates])

    faces: list[list[int]] = []
    for row in range(subdivisions):
        for col in range(subdivisions):
            lower_left = row * steps + col
            lower_right = lower_left + 1
            upper_left = lower_left + steps
            upper_right = upper_left + 1
            faces.append([lower_left, lower_right, upper_right, upper_left])

    return create_mesh_data(vertices, faces, name="Plane/grid", source="built-in")


def create_low_poly_sphere() -> MeshData:
    """Create a low-poly triangular sphere."""
    sphere = trimesh.creation.icosphere(subdivisions=1, radius=0.75)
    return create_mesh_data(
        vertices=sphere.vertices,
        faces=sphere.faces,
        name="Low-poly sphere",
        source="built-in",
    )


def create_cylinder(radius: float = 0.55, height: float = 1.2, sides: int = 16) -> MeshData:
    """Create a mixed polygon cylinder with quad sides and polygon caps."""
    angles = [2.0 * math.pi * index / sides for index in range(sides)]
    bottom = [[radius * math.cos(angle), radius * math.sin(angle), -height / 2.0] for angle in angles]
    top = [[radius * math.cos(angle), radius * math.sin(angle), height / 2.0] for angle in angles]
    vertices = np.array(bottom + top, dtype=float)

    faces: list[list[int]] = []
    for index in range(sides):
        next_index = (index + 1) % sides
        faces.append([index, next_index, next_index + sides, index + sides])

    bottom_cap = list(reversed(range(sides)))
    top_cap = list(range(sides, 2 * sides))
    faces.extend([bottom_cap, top_cap])

    return create_mesh_data(vertices, faces, name="Cylinder", source="built-in")
