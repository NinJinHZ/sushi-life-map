import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

R = 6378137.0


def args_from_blender():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--resolution", type=int, default=1600)
    parser.add_argument("--samples", type=int, default=48)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def emission_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value = (*color, 1)
    emit.inputs['Strength'].default_value = strength
    mat.node_tree.links.new(emit.outputs[0], out.inputs['Surface'])
    return mat


def main():
    args = args_from_blender()
    root = Path(args.root)
    name = args.name
    meta = json.loads((root / f"{name}-metadata.json").read_text())
    elevation = np.load(root / f"{name}-elevation.npy")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    rows_full, cols_full = elevation.shape
    z = meta['zoom']
    tile_x0, tile_y0 = meta['tiles'][0], meta['tiles'][1]
    world_pixels = 256 * (2 ** z)
    meters_per_pixel = 2 * math.pi * R / world_pixels

    settings = {
        'china': {'meters_per_unit': 200000, 'exaggeration': 12, 'max_cols': 700, 'max_rows': 540, 'center': [104.0, 34.5], 'lens': 52, 'route_width': .032, 'marker': .14},
        'sichuan': {'meters_per_unit': 50000, 'exaggeration': 6, 'max_cols': 760, 'max_rows': 640, 'center': [103.7, 30.8], 'lens': 50, 'route_width': .026, 'marker': .10},
        'meishan': {'meters_per_unit': 20000, 'exaggeration': 4, 'max_cols': 700, 'max_rows': 700, 'center': [103.85, 30.08], 'lens': 52, 'route_width': .018, 'marker': .065},
    }[name]
    mpu = settings['meters_per_unit']
    exaggeration = settings['exaggeration']
    cols = min(settings['max_cols'], cols_full)
    rows = min(settings['max_rows'], rows_full)
    xi = np.linspace(0, cols_full - 1, cols).astype(np.int32)
    yi = np.linspace(0, rows_full - 1, rows).astype(np.int32)
    dem = elevation[np.ix_(yi, xi)]

    def pixel_to_scene(px, py):
        return ((px - (cols_full - 1) / 2) * meters_per_pixel / mpu,
                ((rows_full - 1) / 2 - py) * meters_per_pixel / mpu)

    xs = (xi - (cols_full - 1) / 2) * meters_per_pixel / mpu
    ys = ((rows_full - 1) / 2 - yi) * meters_per_pixel / mpu
    heights = np.maximum(dem, -120) / mpu * exaggeration
    xx, yy = np.meshgrid(xs, ys)
    verts = np.stack([xx, yy, heights], axis=-1).reshape(-1, 3).tolist()
    faces = []
    for r in range(rows - 1):
        base = r * cols
        for c in range(cols - 1):
            a = base + c
            faces.append((a, a + 1, a + 1 + cols, a + cols))

    mesh = bpy.data.meshes.new(f"{name}-real-dem")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"{name} | real elevation", mesh)
    bpy.context.collection.objects.link(obj)
    for poly in mesh.polygons:
        poly.use_smooth = True
    uv = mesh.uv_layers.new(name="SatelliteUV")
    u = xi / (cols_full - 1)
    v = 1.0 - yi / (rows_full - 1)
    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            rr, cc = divmod(vertex_index, cols)
            uv.data[loop_index].uv = (u[cc], v[rr])

    material = bpy.data.materials.new("Desaturated satellite terrain")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .86
    bsdf.inputs['Specular IOR Level'].default_value = .22
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(root / f"{name}-satellite.jpg"))
    hue = nodes.new('ShaderNodeHueSaturation')
    hue.inputs['Saturation'].default_value = .58
    hue.inputs['Value'].default_value = .82
    material.node_tree.links.new(tex.outputs['Color'], hue.inputs['Color'])
    material.node_tree.links.new(hue.outputs['Color'], bsdf.inputs['Base Color'])
    obj.data.materials.append(material)

    # The ocean sits above negative elevations and below real land.
    extent = max(xs.max()-xs.min(), ys.max()-ys.min()) * 2.2
    bpy.ops.mesh.primitive_plane_add(size=extent, location=(0, 0, -0.012))
    ocean = bpy.context.object
    ocean.name = "Dark ocean"
    ocean_mat = bpy.data.materials.new("Ink ocean")
    ocean_mat.diffuse_color = (.012, .033, .046, 1)
    ocean_mat.use_nodes = True
    ocean_bsdf = ocean_mat.node_tree.nodes.get('Principled BSDF')
    ocean_bsdf.inputs['Base Color'].default_value = (.012, .033, .046, 1)
    ocean_bsdf.inputs['Roughness'].default_value = .3
    ocean_bsdf.inputs['Metallic'].default_value = .28
    ocean.data.materials.append(ocean_mat)

    def geo_to_pixel(lon, lat):
        px = (lon + 180.0) / 360.0 * world_pixels - tile_x0 * 256
        lat_r = math.radians(lat)
        py = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * world_pixels - tile_y0 * 256
        return px, py

    def sample_height(px, py):
        px = min(max(px, 0), cols_full - 1.001)
        py = min(max(py, 0), rows_full - 1.001)
        x0, y0 = int(px), int(py)
        dx, dy = px - x0, py - y0
        h = (elevation[y0, x0] * (1-dx) * (1-dy) + elevation[y0, x0+1] * dx * (1-dy) +
             elevation[y0+1, x0] * (1-dx) * dy + elevation[y0+1, x0+1] * dx * dy)
        return max(float(h), 0) / mpu * exaggeration

    def geo_to_scene(lon, lat, lift=.05):
        px, py = geo_to_pixel(lon, lat)
        x, y = pixel_to_scene(px, py)
        return (x, y, sample_height(px, py) + lift)

    routes = {
        'china': [('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067),('长安',108.94,34.34),('洛阳',112.45,34.62),('汴京',114.35,34.80)],
        'sichuan': [('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067)],
        'meishan': [('眉山',103.848,30.075),('成都',104.066,30.573)],
    }[name]
    route_points = []
    for index in range(len(routes)-1):
        _, lon0, lat0 = routes[index]
        _, lon1, lat1 = routes[index+1]
        for step in range(24):
            t = step / 24
            route_points.append(geo_to_scene(lon0*(1-t)+lon1*t, lat0*(1-t)+lat1*t, .06))
    route_points.append(geo_to_scene(routes[-1][1], routes[-1][2], .06))
    curve = bpy.data.curves.new('Historical route approximation', 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 2
    curve.bevel_depth = settings['route_width']
    curve.bevel_resolution = 3
    spline = curve.splines.new('POLY')
    spline.points.add(len(route_points)-1)
    for point, co in zip(spline.points, route_points):
        point.co = (*co, 1)
    route_obj = bpy.data.objects.new("眉山出蜀行迹 | approximate historical road", curve)
    bpy.context.collection.objects.link(route_obj)
    gold = emission_material("Warm gold route", (1.0, .63, .20), 3.2)
    route_obj.data.materials.append(gold)

    markers = []
    for label, lon, lat in routes:
        if label not in ({'china': {'眉山','汴京'}, 'sichuan': {'眉山','剑门关'}, 'meishan': {'眉山','成都'}}[name]):
            continue
        co = geo_to_scene(lon, lat, .11)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=settings['marker'], location=co)
        marker = bpy.context.object
        marker.name = label
        marker.data.materials.append(gold)
        markers.append((label, co))

    world = bpy.data.worlds.new("Night blue world")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.055, .09, .13, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45

    bpy.ops.object.light_add(type='SUN', location=(10, -12, 24))
    sun = bpy.context.object
    sun.name = "Late afternoon relief light"
    sun.data.energy = 2.3
    sun.data.angle = math.radians(12)
    sun.data.color = (1.0, .84, .66)
    sun.rotation_euler = (math.radians(28), math.radians(-24), math.radians(-32))
    bpy.ops.object.light_add(type='AREA', location=(-10, -4, 20))
    fill = bpy.context.object
    fill.name = "Cool sky fill"
    fill.data.energy = 1800
    fill.data.shape = 'DISK'
    fill.data.size = 20
    fill.data.color = (.42, .65, 1.0)
    look_at(fill, (0,0,0))

    center = geo_to_scene(settings['center'][0], settings['center'][1], 0)
    width = xs.max() - xs.min()
    height = ys.max() - ys.min()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "Terrain cinema camera"
    camera.data.lens = settings['lens']
    camera.data.clip_end = 1000
    if name == 'china':
        camera.location = (center[0]+10, center[1]-height*.98, center[2]+width*.92)
        target = center
    elif name == 'sichuan':
        camera.location = (center[0]+7, center[1]-height*.76, center[2]+width*.76)
        target = (center[0],center[1],.35)
    else:
        camera.location = (center[0]+4.5, center[1]-height*.72, center[2]+width*.82)
        target = (center[0],center[1],.3)
    look_at(camera, target)
    scene = bpy.context.scene
    scene.camera = camera
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = args.samples
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = int(args.resolution * 9 / 16)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    scene.view_settings.exposure = .1
    scene.render.filepath = str(root / 'renders' / f"{name}-raw.png")
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(root / f"{name}-terrain.blend"))
    bpy.ops.render.render(write_still=True)

    screen = {}
    for label, co in markers:
        p = world_to_camera_view(scene, camera, Vector(co))
        screen[label] = [p.x * args.resolution, (1-p.y) * int(args.resolution*9/16)]
    (root / 'renders' / f"{name}-markers.json").write_text(json.dumps(screen, ensure_ascii=False, indent=2))
    print(f"RENDERED {name}: {scene.render.filepath}")


main()
