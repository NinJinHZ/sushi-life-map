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
FALL_END = 52
PROOF_FRAMES = [240, 312, 396, 432]

parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--out', default='route-study')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
root = Path(args.root)
out = root / args.out
out.mkdir(exist_ok=True)
(out / 'raw').mkdir(exist_ok=True)

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


def smooth_route():
    points = [Vector((lon, lat)) for _, lon, lat in WAYPOINTS]
    result = []
    for i in range(len(points)-1):
        p0 = points[max(0,i-1)]
        p1 = points[i]
        p2 = points[i+1]
        p3 = points[min(len(points)-1,i+2)]
        for j in range(32):
            t = j / 32
            p = .5 * ((2*p1) + (-p0+p2)*t +
                      (2*p0-5*p1+4*p2-p3)*t*t +
                      (-p0+3*p1-3*p2+p3)*t*t*t)
            result.append(geo(p.x,p.y,.11))
    result.append(geo(WAYPOINTS[-1][1],WAYPOINTS[-1][2],.11))
    return result


def emission_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*color,1)
    emission.inputs['Strength'].default_value = strength
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
    return mat


route_scene = smooth_route()
scene = bpy.context.scene
original = bpy.data.objects.get('眉山出蜀行迹 | approximate historical road')
if original:
    original.hide_render = True

tail_mats = [
    emission_material('Route echo | tail near',(.78,.56,.25),1.05),
    emission_material('Route echo | tail middle',(.72,.50,.23),.62),
    emission_material('Route echo | tail far',(.62,.43,.21),.30),
]
head_mat = emission_material('Route echo | traveler',(.86,.65,.32),1.3)

# The route exists only while traveling; arrived places remain as named sites.
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

# Three weakening segments make a tail that decays instead of a second solid line.
tail_specs = [
    ('近',0,.07,.0048,tail_mats[0]),
    ('中',.07,.15,.0040,tail_mats[1]),
    ('远',.15,.25,.0032,tail_mats[2]),
]
for label,recent,oldest,depth,material in tail_specs:
    curve = bpy.data.curves.new(f'Route echo | {label}尾','CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = depth
    curve.bevel_resolution = 3
    spline = curve.splines.new('POLY')
    spline.points.add(len(route_scene)-1)
    for point,co in zip(spline.points,route_scene):
        point.co = (*co,1)
    tail = bpy.data.objects.new(f'行迹 | {label}亮尾',curve)
    scene.collection.objects.link(tail)
    curve.materials.append(material)
    for frame in range(1,END+1,4):
        if frame < BIRTH_END:
            start = end = 0
        else:
            progress = min(1,(frame-BIRTH_END)/(ROUTE_END-BIRTH_END))
            start = max(0,progress-oldest)
            end = max(0,progress-recent)
        curve.bevel_factor_start = start
        curve.bevel_factor_end = end
        curve.keyframe_insert(data_path='bevel_factor_start',frame=frame)
        curve.keyframe_insert(data_path='bevel_factor_end',frame=frame)
    emission = next(node for node in material.node_tree.nodes if node.type == 'EMISSION')
    strength = emission.inputs['Strength']
    strength.keyframe_insert(data_path='default_value',frame=ROUTE_END)
    strength.default_value = 0
    strength.keyframe_insert(data_path='default_value',frame=ROUTE_END+24)

head = bpy.data.objects['苏轼 | traveling light']
head.animation_data_clear()
head.hide_render = True
head.data.materials.clear()
head.data.materials.append(head_mat)
head.scale = (.72,.72,.72)
for frame in range(1,END+1):
    if frame <= FALL_END:
        progress = (frame-1)/(FALL_END-1)
        lift = 4.2*(1-progress)**1.6
        co = route_scene[0] + Vector((0,0,lift))
    elif frame < BIRTH_END:
        co = route_scene[0]
    else:
        progress = min(1,(frame-BIRTH_END)/(ROUTE_END-BIRTH_END))
        pos = progress*(len(route_scene)-1)
        index = min(int(pos),len(route_scene)-2)
        co = route_scene[index].lerp(route_scene[index+1],pos-index)
    head.location = co
    head.keyframe_insert(data_path='location',frame=frame)

projection = json.loads((root/'opening-v3'/'projection.json').read_text())
projection['fall_end'] = FALL_END
for frame in range(1,END+1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    p = world_to_camera_view(scene,scene.camera,head.location)
    projection['frames'][str(frame)]['head'] = [round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
(out/'projection.json').write_text(json.dumps(projection,ensure_ascii=False,separators=(',',':')))

scene.frame_set(312)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'route-echo.blend'))
for frame in PROOF_FRAMES:
    scene.frame_set(frame)
    scene.render.filepath = str(out/'raw'/f'frame-{frame:04d}.png')
    bpy.ops.render.render(write_still=True)
print('ROUTE ECHO PROOFS COMPLETE',flush=True)
