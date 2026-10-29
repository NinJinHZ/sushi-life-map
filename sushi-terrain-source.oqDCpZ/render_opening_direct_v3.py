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
HOLD_OFFSET = Vector((1.45, -2.15, 2.35))
TRAVEL_OFFSET = Vector((3.4, -5.8, 6.4))
BIRTH_END = 192
ROUTE_END = 384
END = 432


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def smooth_camera_route(route, radius=6):
    result = []
    for i in range(len(route)):
        weighted = Vector((0, 0, 0))
        total = 0.0
        for j in range(max(0, i - radius), min(len(route), i + radius + 1)):
            weight = math.exp(-((j - i) / 2.4) ** 2)
            weighted += route[j] * weight
            total += weight
        result.append(weighted / total)
    result[0] = route[0].copy()
    result[-1] = route[-1].copy()
    return result


def route_point(route, position):
    position = max(0.0, min(position, len(route) - 1))
    index = min(int(position), len(route) - 2)
    return route[index].lerp(route[index + 1], position - index)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--proof', action='store_true')
    parser.add_argument('--project-only', action='store_true')
    parser.add_argument('--raw-dir', default='raw')
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    parser.add_argument('--frames', type=int, nargs='+')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = Path(args.root)
    out = root / 'opening-v3' / 'direct-v3'
    raw_dir = out / args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    (out / 'proofs').mkdir(exist_ok=True)
    meta = json.loads((root / 'china-metadata.json').read_text())
    elevation = np.load(root / 'china-elevation.npy')
    rows, cols = elevation.shape
    z = meta['zoom']
    tx0, ty0 = meta['tiles'][0], meta['tiles'][1]
    world_pixels = 256 * (2 ** z)
    mpp = 2 * math.pi * R / world_pixels
    mpu = 200000
    exagg = 12

    def geo_pixel(lon, lat):
        return ((lon + 180) / 360 * world_pixels - tx0 * 256,
                (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * world_pixels - ty0 * 256)

    def height(px, py):
        px = min(max(px, 0), cols - 1.001)
        py = min(max(py, 0), rows - 1.001)
        x0, y0 = int(px), int(py)
        dx, dy = px - x0, py - y0
        h = (elevation[y0, x0] * (1 - dx) * (1 - dy) +
             elevation[y0, x0 + 1] * dx * (1 - dy) +
             elevation[y0 + 1, x0] * (1 - dx) * dy +
             elevation[y0 + 1, x0 + 1] * dx * dy)
        return max(float(h), 0) / mpu * exagg

    def geo(lon, lat, lift=.09):
        px, py = geo_pixel(lon, lat)
        return Vector(((px - (cols - 1) / 2) * mpp / mpu,
                       ((rows - 1) / 2 - py) * mpp / mpu,
                       height(px, py) + lift))

    places = {'眉山': geo(103.848, 30.075), '汴京': geo(114.35, 34.8)}
    route = []
    for i in range(96):
        t = i / 96
        # A single geographic journey with no narrative stop between Meishan and Bianjing.
        route.append(geo(103.848 + (114.35 - 103.848) * t,
                         30.075 + (34.8 - 30.075) * t))
    route.append(places['汴京'].copy())
    camera_route = smooth_camera_route(route)

    scene = bpy.context.scene
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = END
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 20
    scene.view_settings.exposure = .2
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 24
    timeline = json.loads((root / 'final-film' / 'timeline.json').read_text())
    for obj in scene.objects:
        if obj.type == 'CURVE' or obj.name in timeline['sites']:
            obj.hide_render = True
    sun = bpy.data.objects.get('Late afternoon relief light')
    if sun:
        sun.data.animation_data_clear()
        sun.data.energy = 2.0
    if scene.world and scene.world.use_nodes:
        scene.world.node_tree.animation_data_clear()
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .40

    camera = scene.camera
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.data.lens = 50
    head = bpy.data.objects.get('苏轼 | traveling light')
    if head is None:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.12)
        head = bpy.context.object
        head.name = '苏轼 | traveling light'
    head.animation_data_clear()
    head.hide_render = True
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    projection = {
        'width': 1280, 'height': 720,
        'render_width': args.width, 'render_height': args.height,
        'fps': 24, 'fall_end': 52,
        'arrivals': {'眉山': 1, '汴京': ROUTE_END},
        'frames': {},
    }

    for frame in range(1, END + 1):
        scene.frame_set(frame)
        if frame <= BIRTH_END:
            co = places['眉山']
            h = (frame - 1) / (BIRTH_END - 1)
            offset = HOLD_OFFSET + Vector((.16 * math.sin(2 * math.pi * h),
                                           .12 * math.sin(math.pi * h),
                                           .08 * math.sin(math.pi * h)))
            camera.location = co + offset
            target = co
        elif frame <= ROUTE_END:
            t = (frame - BIRTH_END) / (ROUTE_END - BIRTH_END)
            eased = smooth(t)
            pos = eased * (len(route) - 1)
            co = route_point(route, pos)
            cam_co = route_point(camera_route, pos)
            ahead = route_point(camera_route, min(pos + 8, len(camera_route) - 1))
            depart = smooth(t / .12)
            arrive = smooth((t - .80) / .20)
            offset = HOLD_OFFSET.lerp(TRAVEL_OFFSET, depart).lerp(HOLD_OFFSET, arrive)
            target = cam_co.lerp(ahead, .22 * depart * (1 - arrive))
            camera.location = cam_co + offset
        else:
            co = places['汴京']
            h = (frame - ROUTE_END - 1) / (END - ROUTE_END - 1)
            offset = HOLD_OFFSET + Vector((.16 * math.sin(2 * math.pi * h),
                                           .12 * math.sin(math.pi * h),
                                           .08 * math.sin(math.pi * h)))
            camera.location = co + offset
            target = co
        camera.data.lens = 50
        look_at(camera, target)
        head.location = co
        camera.keyframe_insert(data_path='location', frame=frame)
        camera.keyframe_insert(data_path='rotation_euler', frame=frame)
        camera.data.keyframe_insert(data_path='lens', frame=frame)
        head.keyframe_insert(data_path='location', frame=frame)
        bpy.context.view_layer.update()
        item = {'labels': {}, 'head': [],
                'camera': [round(value, 6) for value in camera.location],
                'camera_target': [round(value, 6) for value in target]}
        for name, point in places.items():
            p = world_to_camera_view(scene, camera, point)
            item['labels'][name] = [round(p.x * 1280, 2), round((1 - p.y) * 720, 2), round(p.z, 3)]
        p = world_to_camera_view(scene, camera, co)
        item['head'] = [round(p.x * 1280, 2), round((1 - p.y) * 720, 2), round(p.z, 3)]
        projection['frames'][str(frame)] = item
        if frame % 72 == 0:
            print(f'DIRECT OPENING PROJECTED {frame}/{END}', flush=True)

    (out / 'projection.json').write_text(json.dumps(projection, ensure_ascii=False, separators=(',', ':')))
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'opening-direct-v3.blend'))
    frames = [] if args.project_only else (args.frames or ([36, 120, 204, 312, 396, 432] if args.proof else range(1, END + 1)))
    for frame in frames:
        path = (out / 'proofs' / f'raw-{frame:04d}.png') if args.proof else raw_dir / f'frame-{frame:04d}.png'
        if path.exists() and not args.proof:
            continue
        scene.frame_set(frame)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    print('DIRECT MEISHAN-BIANJING OPENING COMPLETE', flush=True)


if __name__ == '__main__':
    main()
