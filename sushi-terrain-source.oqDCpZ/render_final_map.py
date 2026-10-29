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
FINAL_OFFSET = Vector((5.0, -21.0, 27.0))


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def smooth_route(waypoints, geo):
    points = [Vector(lonlat) for lonlat in waypoints]
    result = []
    for i in range(len(points) - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(len(points) - 1, i + 2)]
        for j in range(32):
            t = j / 32
            p = .5 * ((2 * p1) + (-p0 + p2) * t +
                      (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                      (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
            result.append(geo(p.x, p.y, .09))
    result.append(geo(points[-1].x, points[-1].y, .09))
    return result


def smooth_camera_route(route, radius=6):
    # The traveler remains attached to real terrain. Only the camera path is
    # smoothed, removing high-frequency DEM bumps that read as handheld jitter.
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
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=0)
    parser.add_argument('--raw-dir', default='raw')
    parser.add_argument('--frames', type=int, nargs='+')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = Path(args.root)
    out = root / 'final-film'
    raw_dir = out / args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    timeline = json.loads((out / 'timeline.json').read_text())
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

    def geo(lon, lat, lift=.08):
        px, py = geo_pixel(lon, lat)
        return Vector(((px - (cols - 1) / 2) * mpp / mpu,
                       ((rows - 1) / 2 - py) * mpp / mpu,
                       height(px, py) + lift))

    scene = bpy.context.scene
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 20
    scene.view_settings.exposure = .2
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 24
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

    places = {name: geo(*lonlat) for name, lonlat in timeline['sites'].items()}
    routes = {}
    camera_routes = {}
    chapters = []
    cursor = 1
    for chapter in timeline['chapters']:
        waypoints = [timeline['sites'][name] for name in chapter['waypoints']]
        routes[chapter['id']] = smooth_route(waypoints, geo)
        camera_routes[chapter['id']] = smooth_camera_route(routes[chapter['id']])
        travel_frames = round(chapter['travel_s'] * 24)
        hold_frames = round(chapter['hold_s'] * 24)
        item = dict(chapter)
        item.update({
            'start_frame': cursor,
            'travel_frames': travel_frames,
            'hold_frames': hold_frames,
            'travel_end': cursor + travel_frames - 1,
            'end_frame': cursor + travel_frames + hold_frames - 1,
            'arrival_year': chapter.get('arrival_year', chapter['year_end']),
        })
        chapters.append(item)
        cursor = item['end_frame'] + 1
    total_frames = cursor - 1
    scene.frame_start = 1
    scene.frame_end = total_frames
    projection = {
        'width': 1280,
        'height': 720,
        'render_width': args.width,
        'render_height': args.height,
        'fps': 24,
        'opening_frames': timeline['opening_frames'],
        'total_frames': total_frames,
        'arrivals': {name: 1 for name in timeline['previous_sites']},
        'chapters': chapters,
        'frames': {},
    }
    for chapter in chapters:
        if chapter['travel_frames'] == 0:
            for name in chapter['waypoints'][1:]:
                projection['arrivals'].setdefault(name, chapter['start_frame'])
    china_center = geo(105.5, 29.0, 0)

    for chapter in chapters:
        route = routes[chapter['id']]
        camera_route = camera_routes[chapter['id']]
        start = chapter['start_frame']
        travel_frames = chapter['travel_frames']
        hold_frames = chapter['hold_frames']
        final_start = chapter['travel_end'] + round(chapter.get('final_title_after_s', 999) * 24)
        for frame in range(start, chapter['end_frame'] + 1):
            scene.frame_set(frame)
            local = frame - start + 1
            moving = False
            if local <= travel_frames:
                t = (local - 1) / max(1, travel_frames - 1)
                eased = smooth(t)
                pos = eased * (len(route) - 1)
                index = min(int(pos), len(route) - 2)
                co = route_point(route, pos)
                cam_co = route_point(camera_route, pos)
                ahead = route_point(camera_route, min(pos + 8, len(camera_route) - 1))
                depart = smooth(t / .12)
                arrive = smooth((t - .80) / .20)
                offset = HOLD_OFFSET.lerp(TRAVEL_OFFSET, depart).lerp(HOLD_OFFSET, arrive)
                target = cam_co.lerp(ahead, .22 * depart * (1 - arrive))
                camera.location = cam_co + offset
                camera.data.lens = 50
                year = round(chapter['year_start'] +
                             (chapter['arrival_year'] - chapter['year_start']) * t)
                moving = 1 < local < travel_frames
                for i, name in enumerate(chapter['waypoints'][1:], 1):
                    if name not in projection['arrivals'] and pos >= i * 32:
                        projection['arrivals'][name] = frame
            else:
                h = (local - travel_frames - 1) / max(1, hold_frames - 1)
                co = route[-1]
                offset = HOLD_OFFSET + Vector((.16 * math.sin(2 * math.pi * h),
                                               .12 * math.sin(math.pi * h),
                                               .08 * math.sin(math.pi * h)))
                target = co
                camera.location = co + offset
                camera.data.lens = 50
                year = round(chapter['arrival_year'] +
                             (chapter['year_end'] - chapter['arrival_year']) * h)
                if frame >= final_start:
                    q = (frame - final_start) / max(1, chapter['end_frame'] - final_start)
                    e = smooth(q)
                    final_location = china_center + FINAL_OFFSET
                    camera.location = (co + offset).lerp(final_location, e)
                    target = co.lerp(china_center, e)
                    camera.data.lens = 50 - 5 * e
            look_at(camera, target)
            head.location = co
            camera.keyframe_insert(data_path='location', frame=frame)
            camera.keyframe_insert(data_path='rotation_euler', frame=frame)
            camera.data.keyframe_insert(data_path='lens', frame=frame)
            head.keyframe_insert(data_path='location', frame=frame)
            bpy.context.view_layer.update()
            item = {
                'chapter': chapter['id'],
                'year': year,
                'moving': moving,
                'current': chapter['waypoints'][-1],
                'camera': [round(value, 6) for value in camera.location],
                'camera_target': [round(value, 6) for value in target],
                'head': [],
                'labels': {},
            }
            p = world_to_camera_view(scene, camera, co)
            item['head'] = [round(p.x * 1280, 2), round((1 - p.y) * 720, 2), round(p.z, 3)]
            item['trail'] = []
            if moving:
                for step in range(15):
                    trail_progress = max(0.0, eased - .16) + (eased - max(0.0, eased - .16)) * step / 14
                    trail_pos = trail_progress * (len(route) - 1)
                    trail_index = min(int(trail_pos), len(route) - 2)
                    trail_co = route[trail_index].lerp(route[trail_index + 1], trail_pos - trail_index)
                    tp = world_to_camera_view(scene, camera, trail_co)
                    item['trail'].append([round(tp.x * 1280, 2), round((1 - tp.y) * 720, 2), round(tp.z, 3)])
            for name, point in places.items():
                p = world_to_camera_view(scene, camera, point)
                item['labels'][name] = [round(p.x * 1280, 2), round((1 - p.y) * 720, 2), round(p.z, 3)]
            projection['frames'][str(frame)] = item
        print(f"PROJECTED {chapter['id']} {start}-{chapter['end_frame']}", flush=True)

    (out / 'projection.json').write_text(json.dumps(projection, ensure_ascii=False, separators=(',', ':')))
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'sushi-life-map.blend'))

    if args.project_only:
        frames = []
    elif args.frames:
        frames = args.frames
    elif args.proof:
        frames = []
        for chapter in chapters:
            frames.append(chapter['start_frame'] + chapter['travel_frames'] // 2)
            frames.append(chapter['travel_end'] + max(1, chapter['hold_frames'] // 2))
        frames.append(total_frames)
    else:
        frames = range(max(1, args.start), min(total_frames, args.end or total_frames) + 1)
    for frame in frames:
        path = raw_dir / f'frame-{frame:04d}.png'
        if path.exists() and not args.proof:
            continue
        scene.frame_set(frame)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if frame % 240 == 0:
            print(f'RENDERED {frame}/{total_frames}', flush=True)
    print(f'FINAL MAP {"PROOFS" if args.proof else "ANIMATION"} COMPLETE: {total_frames} frames', flush=True)


if __name__ == '__main__':
    main()
