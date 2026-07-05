"""PyVista visualization helpers for Streamlit rendering."""

from __future__ import annotations

from io import StringIO

import numpy as np

from .mesh_core import MeshData
from .mesh_ops import compute_face_normals, compute_vertex_normals


DISPLAY_MODES = [
    "Solid shaded mesh",
    "Wireframe",
    "Points/vertices",
    "Wireframe + shaded mesh",
]


def mesh_to_pyvista(mesh: MeshData):
    """Convert MeshData to a PyVista PolyData object."""
    import pyvista as pv

    faces = []
    for face in mesh.faces:
        faces.extend([len(face), *face])

    return pv.PolyData(mesh.vertices, np.asarray(faces, dtype=np.int64))


def make_plotter(
    mesh: MeshData,
    display_mode: str,
    background_color: str = "white",
    show_axes: bool = True,
    show_face_normals: bool = False,
    show_vertex_normals: bool = False,
    normal_length: float = 0.25,
    vertex_normal_weighting: str = "average",
    window_size: tuple[int, int] = (820, 560),
):
    """Create a PyVista plotter for the selected display mode."""
    import pyvista as pv

    plotter = pv.Plotter(window_size=window_size, border=False)
    plotter.set_background(background_color)
    polydata = mesh_to_pyvista(mesh)

    if display_mode == "Solid shaded mesh":
        plotter.add_mesh(
            polydata,
            color="#8fb3d9",
            show_edges=False,
            smooth_shading=False,
        )
    elif display_mode == "Wireframe":
        plotter.add_mesh(
            polydata,
            style="wireframe",
            color="#243b53",
            line_width=2,
        )
    elif display_mode == "Points/vertices":
        plotter.add_points(
            polydata.points,
            color="#c2410c",
            point_size=12,
            render_points_as_spheres=True,
        )
    elif display_mode == "Wireframe + shaded mesh":
        plotter.add_mesh(
            polydata,
            color="#8fb3d9",
            show_edges=True,
            edge_color="#1f2933",
            line_width=1,
            smooth_shading=False,
        )
    else:
        plotter.add_mesh(polydata, color="#8fb3d9", smooth_shading=False)

    _add_normal_overlays(
        plotter,
        mesh,
        show_face_normals=show_face_normals,
        show_vertex_normals=show_vertex_normals,
        normal_length=normal_length,
        vertex_normal_weighting=vertex_normal_weighting,
    )

    if show_axes:
        plotter.add_axes(line_width=2)

    plotter.view_isometric()
    plotter.reset_camera()
    return plotter


def make_overlay_plotter(
    original_mesh: MeshData,
    current_mesh: MeshData,
    background_color: str = "white",
    show_axes: bool = True,
    window_size: tuple[int, int] = (820, 560),
):
    """Create a comparison plotter with original wireframe over current mesh."""
    import pyvista as pv

    plotter = pv.Plotter(window_size=window_size, border=False)
    plotter.set_background(background_color)

    current_polydata = mesh_to_pyvista(current_mesh)
    original_polydata = mesh_to_pyvista(original_mesh)
    plotter.add_mesh(
        current_polydata,
        color="#8fb3d9",
        opacity=0.72,
        show_edges=True,
        edge_color="#2563eb",
        line_width=1,
        smooth_shading=False,
    )
    plotter.add_mesh(
        original_polydata,
        style="wireframe",
        color="#111827",
        line_width=2,
    )
    _add_displacement_lines(plotter, original_mesh, current_mesh)

    if show_axes:
        plotter.add_axes(line_width=2)

    plotter.view_isometric()
    plotter.reset_camera()
    return plotter


def make_step_inspector_plotter(
    mesh: MeshData,
    vertex_index: int,
    neighbors: list[int],
    predicted_position: object | None = None,
    background_color: str = "white",
    show_axes: bool = True,
    window_size: tuple[int, int] = (760, 420),
):
    """Create a visual inspector plotter for one vertex smoothing step."""
    import pyvista as pv

    plotter = pv.Plotter(window_size=window_size, border=False)
    plotter.set_background(background_color)
    polydata = mesh_to_pyvista(mesh)
    plotter.add_mesh(
        polydata,
        color="#dbeafe",
        opacity=0.58,
        show_edges=True,
        edge_color="#64748b",
        line_width=1,
        smooth_shading=False,
    )

    safe_index = int(np.clip(int(vertex_index), 0, max(0, mesh.vertex_count - 1)))
    selected = mesh.vertices[[safe_index]]
    plotter.add_points(
        selected,
        color="#dc2626",
        point_size=18,
        render_points_as_spheres=True,
    )

    valid_neighbors = [int(index) for index in neighbors if 0 <= int(index) < mesh.vertex_count]
    if valid_neighbors:
        plotter.add_points(
            mesh.vertices[np.asarray(valid_neighbors, dtype=int)],
            color="#f59e0b",
            point_size=13,
            render_points_as_spheres=True,
        )

    if predicted_position is not None:
        predicted = np.asarray(predicted_position, dtype=float).reshape(-1)
        if predicted.size >= 3 and np.isfinite(predicted[:3]).all():
            predicted = predicted[:3]
            plotter.add_points(
                predicted.reshape(1, 3),
                color="#16a34a",
                point_size=18,
                render_points_as_spheres=True,
            )
            line_points = np.vstack([selected[0], predicted])
            line_cell = np.asarray([2, 0, 1], dtype=np.int64)
            plotter.add_mesh(pv.PolyData(line_points, lines=line_cell), color="#16a34a", line_width=4)

    if show_axes:
        plotter.add_axes(line_width=2)

    plotter.view_isometric()
    plotter.reset_camera()
    return plotter


def plotter_to_html(plotter) -> str:
    """Convert a PyVista plotter into embeddable Panel/VTK HTML."""
    import panel as pn

    pn.extension("vtk", sizing_mode="stretch_both")
    vtk_pane = pn.pane.VTK(plotter.ren_win)

    with StringIO() as html_buffer:
        vtk_pane.save(html_buffer, title="Interactive Mesh Viewer")
        return html_buffer.getvalue()


def _add_normal_overlays(
    plotter,
    mesh: MeshData,
    show_face_normals: bool,
    show_vertex_normals: bool,
    normal_length: float,
    vertex_normal_weighting: str,
) -> None:
    """Draw selected normal vectors as line segments."""
    if normal_length <= 0.0:
        return

    if show_face_normals:
        face_data = compute_face_normals(mesh)
        face_lines = _line_segments_to_pyvista(
            starts=face_data.centers,
            directions=face_data.normals,
            length=normal_length,
        )
        if face_lines is not None:
            plotter.add_mesh(face_lines, color="#dc2626", line_width=3)

    if show_vertex_normals:
        vertex_normals = compute_vertex_normals(mesh, weighting=vertex_normal_weighting)
        vertex_lines = _line_segments_to_pyvista(
            starts=mesh.vertices,
            directions=vertex_normals,
            length=normal_length,
        )
        if vertex_lines is not None:
            plotter.add_mesh(vertex_lines, color="#2563eb", line_width=2)


def _add_displacement_lines(plotter, original_mesh: MeshData, current_mesh: MeshData) -> None:
    """Draw lines from original to current vertex positions when comparable."""
    import pyvista as pv

    if (
        not original_mesh.valid
        or not current_mesh.valid
        or original_mesh.vertex_count != current_mesh.vertex_count
        or original_mesh.vertex_count == 0
    ):
        return

    displacement = current_mesh.vertices - original_mesh.vertices
    lengths = np.linalg.norm(displacement, axis=1)
    moved = np.flatnonzero(lengths > 1.0e-8)
    if moved.size == 0:
        return
    if moved.size > 500:
        moved = moved[np.linspace(0, moved.size - 1, 500, dtype=int)]

    points = np.empty((moved.size * 2, 3), dtype=float)
    lines = np.empty((moved.size, 3), dtype=np.int64)
    for line_index, vertex_index in enumerate(moved):
        start_point_index = line_index * 2
        points[start_point_index] = original_mesh.vertices[vertex_index]
        points[start_point_index + 1] = current_mesh.vertices[vertex_index]
        lines[line_index] = [2, start_point_index, start_point_index + 1]
    plotter.add_mesh(pv.PolyData(points, lines=lines.ravel()), color="#f97316", line_width=2)


def _line_segments_to_pyvista(starts: np.ndarray, directions: np.ndarray, length: float):
    """Create PyVista line cells from start points and unit directions."""
    import pyvista as pv

    nonzero = np.linalg.norm(directions, axis=1) > 1.0e-12
    if not np.any(nonzero):
        return None

    starts = starts[nonzero]
    ends = starts + directions[nonzero] * float(length)
    segment_count = starts.shape[0]

    points = np.empty((segment_count * 2, 3), dtype=float)
    lines = np.empty((segment_count, 3), dtype=np.int64)
    for index in range(segment_count):
        start_point_index = index * 2
        points[start_point_index] = starts[index]
        points[start_point_index + 1] = ends[index]
        lines[index] = [2, start_point_index, start_point_index + 1]

    return pv.PolyData(points, lines=lines.ravel())
