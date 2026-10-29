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
WAYPOINTS = [('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067)]
BIRTH_END = 192
ROUTE_END = 384
END = 432
parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--proof', action='store_true')
parser.add_argument('--raw-dir', default='raw')
parser.add_argument('--blend-name', default='sichuan-archival-18s.blend')
parser.add_argument('--projection-name', default='projection.json')
parser.add_argument('--hires-imagery')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
root = Path(args.root)
out = root / 'opening-v3'
out.mkdir(exist_ok=True)
raw_dir = out / args.raw_dir
raw_dir.mkdir(exist_ok=True)
(out / 'proofs').mkdir(exist_ok=True)
meta = json.loads((root / 'sichuan-metadata.json').read_text())
elevation = np.load(root / 'sichuan-elevation.npy')
rows, cols = elevation.shape
z = meta['zoom']
tx0, ty0 = meta['tiles'][0], meta['tiles'][1]
world_pixels = 256 * (2 ** z)
mpp = 2 * math.pi * R / world_pixels
mpu = 50000
exagg = 6


def geo_pixel(lon, lat):
    return ((lon + 180) / 360 * world_pixels - tx0 * 256,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * world_pixels - ty0 * 256)


def height(px, py):
    px = min(max(px, 0), cols - 1.001)
    py = min(max(py, 0), rows - 1.001)
    x0, y0 = int(px), int(py)
    dx, dy = px - x0, py - y0
    h = (elevation[y0,x0] * (1-dx) * (1-dy) + elevation[y0,x0+1] * dx * (1-dy) +
         elevation[y0+1,x0] * (1-dx) * dy + elevation[y0+1,x0+1] * dx * dy)
    return max(float(h), 0) / mpu * exagg


def geo(lon, lat, lift=.10):
    px, py = geo_pixel(lon, lat)
    return Vector(((px - (cols-1)/2) * mpp/mpu,
                   ((rows-1)/2 - py) * mpp/mpu, height(px,py) + lift))


P = {name: geo(lon,lat) for name,lon,lat in WAYPOINTS}
route_geo = []
for i in range(len(WAYPOINTS)-1):
    _, a, b = WAYPOINTS[i]
    _, c, d = WAYPOINTS[i+1]
    for j in range(24):
        t = j / 24
        route_geo.append((a*(1-t)+c*t, b*(1-t)+d*t))
route_geo.append((WAYPOINTS[-1][1], WAYPOINTS[-1][2]))
route_scene = [geo(lon,lat,.12) for lon,lat in route_geo]

scene = bpy.context.scene
if args.hires_imagery:
    image = bpy.data.images.get('sichuan-satellite.jpg')
    if image is None:
        raise RuntimeError('Sichuan satellite image not found in Blender project')
    image.filepath = bpy.path.relpath(str(Path(args.hires_imagery).resolve()))
    image.reload()
    print(f'SICHUAN HIRES TEXTURE: {tuple(image.size)} {image.filepath}', flush=True)
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = END
if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):
    scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 20
scene.view_settings.exposure = .2
camera = scene.camera
camera.animation_data_clear()
camera.data.animation_data_clear()
camera.data.lens = 50

route = bpy.data.objects['眉山出蜀行迹 | approximate historical road']
route.hide_render = True
route.data.animation_data_clear()
route.data.bevel_depth = .009
route.data.bevel_factor_end = 0
route.data.keyframe_insert(data_path='bevel_factor_end', frame=1)
route.data.keyframe_insert(data_path='bevel_factor_end', frame=BIRTH_END)
route.data.bevel_factor_end = 1
route.data.keyframe_insert(data_path='bevel_factor_end', frame=ROUTE_END)
route.data.keyframe_insert(data_path='bevel_factor_end', frame=END)

gold = bpy.data.materials['Warm gold route']
for node in gold.node_tree.nodes:
    if node.type == 'EMISSION':
        node.inputs['Color'].default_value = (.78,.48,.16,1)
        node.inputs['Strength'].default_value = 1.45

bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=.095, location=P['眉山'])
head = bpy.context.object
head.name = '苏轼 | traveling light'
head.data.materials.append(gold)
for frame in range(1,END+1,4):
    if frame < BIRTH_END:
        co = P['眉山']
    else:
        progress = min(1,(frame-BIRTH_END)/(ROUTE_END-BIRTH_END))
        pos = progress * (len(route_scene)-1)
        idx = min(int(pos),len(route_scene)-2)
        t = pos-idx
        co = route_scene[idx].lerp(route_scene[idx+1],t)
    head.location = co
    head.keyframe_insert(data_path='location',frame=frame)
head.location = P['眉山']
head.keyframe_insert(data_path='location',frame=1)

arrivals = {}
for i,(name,lon,lat) in enumerate(WAYPOINTS):
    if name == '眉山':
        arrivals[name] = 1
        continue
    arrivals[name] = BIRTH_END + round(i*24/(len(route_scene)-1)*(ROUTE_END-BIRTH_END))

mid = sum(P.values(),Vector())/len(P)
for frame in range(BIRTH_END,ROUTE_END+1,12):
    progress = min(1,(frame-BIRTH_END)/(ROUTE_END-BIRTH_END))
    pos = progress * (len(route_scene)-1)
    idx = min(int(pos),len(route_scene)-2)
    t = pos-idx
    current = route_scene[idx].lerp(route_scene[idx+1],t)
    ahead = route_scene[min(idx+8,len(route_scene)-1)]
    offset = Vector((2.8+3.0*progress,-4.2-5.0*progress,3.8+4.0*progress))
    target = current.lerp(ahead,.32)
    scene.frame_set(frame)
    camera.location = current+offset
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.keyframe_insert(data_path='location',frame=frame)
    camera.keyframe_insert(data_path='rotation_euler',frame=frame)
for frame,loc,target in [
    (1,P['眉山']+Vector((1.2,-1.8,1.6)),P['眉山']),
    (96,P['眉山']+Vector((1.55,-2.35,2.05)),P['眉山'].lerp(P['成都'],.07)),
    (BIRTH_END,P['眉山']+Vector((2.8,-4.2,3.8)),P['眉山'].lerp(P['成都'],.5)),
    (END,mid+Vector((0,-12,14)),mid),
]:
    scene.frame_set(frame)
    camera.location = loc
    camera.rotation_euler = (target-loc).to_track_quat('-Z','Y').to_euler()
    camera.keyframe_insert(data_path='location',frame=frame)
    camera.keyframe_insert(data_path='rotation_euler',frame=frame)
for frame,lens in [(1,50),(ROUTE_END,50),(END,45)]:
    camera.data.lens = lens
    camera.data.keyframe_insert(data_path='lens',frame=frame)

head.hide_render = True
for name in P:
    marker = bpy.data.objects.get(name)
    if marker:
        marker.hide_render = True

sun = bpy.data.objects.get('Late afternoon relief light')
if sun:
    sun.data.animation_data_clear()
    for frame,energy in [(1,1.25),(BIRTH_END,1.7),(336,2.2),(END,1.9)]:
        sun.data.energy = energy
        sun.data.keyframe_insert(data_path='energy',frame=frame)
world = scene.world
if world and world.use_nodes:
    world.node_tree.animation_data_clear()
    bg = world.node_tree.nodes.get('Background')
    for frame,strength in [(1,.28),(BIRTH_END,.38),(336,.5),(END,.42)]:
        bg.inputs['Strength'].default_value = strength
        bg.inputs['Strength'].keyframe_insert(data_path='default_value',frame=frame)

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out / args.blend_name))
projection = {'width':1280,'height':720,'arrivals':arrivals,'frames':{}}
for frame in range(1,END+1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    item = {'labels':{},'head':[]}
    for name in P:
        p = world_to_camera_view(scene,camera,P[name])
        item['labels'][name] = [round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
    p = world_to_camera_view(scene,camera,head.location)
    item['head'] = [round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
    projection['frames'][str(frame)] = item
(out / args.projection_name).write_text(json.dumps(projection,ensure_ascii=False,separators=(',',':')))

if args.proof:
    for frame in [36,120,204,312,396,432]:
        scene.frame_set(frame)
        scene.render.filepath = str(out/'proofs'/f'raw-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
else:
    scene.frame_set(1)
    scene.render.filepath = str(raw_dir / 'frame-')
    bpy.ops.render.render(animation=True)
print('18-SECOND ARCHIVAL SCENE COMPLETE', 'PROOF' if args.proof else 'ANIMATION', flush=True)
