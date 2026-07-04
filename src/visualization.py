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
        opacity=0.78,
        show_edges=False,
        smooth_shading=False,
    )
    plotter.add_mesh(
        original_polydata,
        style="wireframe",
        color="#111827",
        line_width=2,
    )

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
