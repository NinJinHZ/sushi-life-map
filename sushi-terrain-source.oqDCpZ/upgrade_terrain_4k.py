import argparse
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np


def make_tile_mesh(name, vertices, xi, yi, gx0, gy0, gx1, gy1, box, material):
    nx = gx1 - gx0 + 1
    ny = gy1 - gy0 + 1
    tile_vertices = np.ascontiguousarray(vertices[gy0:gy1 + 1, gx0:gx1 + 1].reshape(-1, 3))
    quad_rows = np.arange(ny - 1, dtype=np.int32)[:, None]
    quad_cols = np.arange(nx - 1, dtype=np.int32)[None, :]
    base = (quad_rows * nx + quad_cols).ravel()
    loop_vertices = np.stack([base, base + 1, base + 1 + nx, base + nx], axis=1).ravel()
    quad_count = len(base)

    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(tile_vertices))
    mesh.vertices.foreach_set('co', tile_vertices.ravel())
    mesh.loops.add(len(loop_vertices))
    mesh.loops.foreach_set('vertex_index', loop_vertices)
    mesh.polygons.add(quad_count)
    mesh.polygons.foreach_set('loop_start', np.arange(quad_count, dtype=np.int32) * 4)
    mesh.polygons.foreach_set('loop_total', np.full(quad_count, 4, dtype=np.int32))
    mesh.polygons.foreach_set('use_smooth', np.ones(quad_count, dtype=bool))

    left, top, right, bottom = box
    local_u = (xi[gx0:gx1 + 1] - left) / (right - left - 1)
    local_v = 1.0 - (yi[gy0:gy1 + 1] - top) / (bottom - top - 1)
    rr, cc = np.divmod(loop_vertices, nx)
    uv_coordinates = np.column_stack((local_u[cc], local_v[rr])).astype(np.float32)
    uv = mesh.uv_layers.new(name='SatelliteUV')
    uv.data.foreach_set('uv', uv_coordinates.ravel())
    mesh.materials.append(material)
    mesh.update(calc_edges=True)
    return mesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terrain-dir', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cols', type=int, default=1800)
    parser.add_argument('--rows', type=int, default=1350)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    terrain = Path(args.terrain_dir)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite existing 4K scene: {output}')
    metadata = json.loads((terrain / 'china-metadata.json').read_text())
    texture_metadata = json.loads((terrain / 'satellite-tiles' / 'metadata.json').read_text())
    if texture_metadata['mesh_grid'] != [args.cols, args.rows]:
        raise ValueError('Texture tiles were built for a different mesh grid')
    elevation = np.load(terrain / 'china-elevation.npy', mmap_mode='r')
    rows_full, cols_full = elevation.shape
    if [cols_full, rows_full] != metadata['size']:
        raise ValueError('DEM dimensions do not match source metadata')

    # A strided sample retains the real DEM while keeping the 16GB machine
    # below its memory ceiling. The source itself remains at full resolution.
    xi = np.linspace(0, cols_full - 1, args.cols).astype(np.int32)
    yi = np.linspace(0, rows_full - 1, args.rows).astype(np.int32)
    dem = np.asarray(elevation[np.ix_(yi, xi)], dtype=np.float32)
    z = metadata['zoom']
    world_pixels = 256 * (2 ** z)
    meters_per_pixel = 2 * np.pi * 6378137.0 / world_pixels
    meters_per_unit = 200000
    exaggeration = 12
    xs = (xi - (cols_full - 1) / 2) * meters_per_pixel / meters_per_unit
    ys = ((rows_full - 1) / 2 - yi) * meters_per_pixel / meters_per_unit
    heights = np.maximum(dem, -120) / meters_per_unit * exaggeration
    xx, yy = np.meshgrid(xs, ys)
    vertices = np.stack([xx, yy, heights], axis=-1).astype(np.float32)

    old_obj = bpy.data.objects.get('china | real elevation')
    if old_obj is None:
        raise RuntimeError('The existing national terrain object is missing')
    old_mesh = old_obj.data
    if not old_mesh.materials:
        raise RuntimeError('The original terrain material is missing')
    original_material = old_mesh.materials[0]
    collections = old_obj.users_collection
    matrix = old_obj.matrix_world.copy()
    changed_nodes = 0
    total_vertices = 0
    total_polygons = 0
    x_split = args.cols // 2
    y_split = args.rows // 2
    ranges = {
        'x0-y0': (0, 0, x_split, y_split),
        'x1-y0': (x_split, 0, args.cols - 1, y_split),
        'x0-y1': (0, y_split, x_split, args.rows - 1),
        'x1-y1': (x_split, y_split, args.cols - 1, args.rows - 1),
    }
    for name, (gx0, gy0, gx1, gy1) in ranges.items():
        tile_info = texture_metadata['tiles'][name]
        material = original_material.copy()
        material.name = f'china-4k | {name}'
        image = bpy.data.images.load(tile_info['path'], check_existing=False)
        image.name = f'china-satellite-z9 | {name}'
        image.filepath = '//' + os.path.relpath(tile_info['path'], output.parent)
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                node.image = image
                changed_nodes += 1
        mesh = make_tile_mesh(f'china-4k | real DEM z9 | {name}', vertices, xi, yi,
                              gx0, gy0, gx1, gy1, tile_info['box'], material)
        obj = bpy.data.objects.new(f'china | real elevation | {name}', mesh)
        for collection in collections:
            collection.objects.link(obj)
        obj.matrix_world = matrix
        total_vertices += len(mesh.vertices)
        total_polygons += len(mesh.polygons)

    bpy.data.objects.remove(old_obj, do_unlink=True)
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    if changed_nodes != 4:
        raise RuntimeError(f'Expected four satellite texture updates, got {changed_nodes}')

    scene = bpy.context.scene
    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.resolution_percentage = 100
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 32
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report = {
        'source_zoom': z,
        'source_size': metadata['size'],
        'source_dem': str(terrain / 'china-elevation.npy'),
        'source_texture_tiles': texture_metadata['tiles'],
        'mesh_vertices': total_vertices,
        'mesh_polygons': total_polygons,
        'mesh_grid': [args.cols, args.rows],
        'texture_layout': '2x2; every texture dimension is below the 16384px GPU limit',
        'render_size': [3840, 2160],
        'texture_nodes_updated': changed_nodes,
        'sampled_elevation_min': float(dem.min()),
        'sampled_elevation_max': float(dem.max()),
        'output': str(output),
    }
    (output.parent / 'terrain-4k-build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
