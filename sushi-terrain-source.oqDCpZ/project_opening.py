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
ROUTES = {
    'china': [('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067),('长安',108.94,34.34),('洛阳',112.45,34.62),('汴京',114.35,34.80)],
    'sichuan': [('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067)],
    'meishan': [('眉山',103.848,30.075),('成都',104.066,30.573)],
}
LABELS = {
    'china': {'眉山','长安','洛阳','汴京'},
    'sichuan': {'眉山','成都','剑门关','广元','汉中'},
    'meishan': {'眉山','成都'},
}


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--name', required=True)
parser.add_argument('--frames', type=int, default=48)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
root = Path(args.root)
meta = json.loads((root / f"{args.name}-metadata.json").read_text())
elevation = np.load(root / f"{args.name}-elevation.npy")
rows, cols = elevation.shape
z = meta['zoom']
tile_x0, tile_y0 = meta['tiles'][0], meta['tiles'][1]
world_pixels = 256 * (2 ** z)
meters_per_pixel = 2 * math.pi * R / world_pixels
settings = {'china':(200000,12,.20),'sichuan':(50000,6,.30),'meishan':(20000,4,.25)}[args.name]
mpu, exaggeration, amount = settings


def geo_to_pixel(lon, lat):
    px = (lon + 180.0) / 360.0 * world_pixels - tile_x0 * 256
    py = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * world_pixels - tile_y0 * 256
    return px, py


def sample_height(px, py):
    px = min(max(px, 0), cols - 1.001)
    py = min(max(py, 0), rows - 1.001)
    x0, y0 = int(px), int(py)
    dx, dy = px-x0, py-y0
    h = (elevation[y0,x0]*(1-dx)*(1-dy)+elevation[y0,x0+1]*dx*(1-dy)+elevation[y0+1,x0]*(1-dx)*dy+elevation[y0+1,x0+1]*dx*dy)
    return max(float(h),0) / mpu * exaggeration


def geo_to_scene(lon, lat, lift=.11):
    px, py = geo_to_pixel(lon, lat)
    x = (px - (cols-1)/2) * meters_per_pixel / mpu
    y = ((rows-1)/2 - py) * meters_per_pixel / mpu
    return Vector((x,y,sample_height(px,py)+lift))


scene = bpy.context.scene
camera = scene.camera
start_location = camera.location.copy()
start_rotation = camera.rotation_euler.copy()
marker = bpy.data.objects.get('眉山')
target = marker.location.copy() if marker else Vector((0,0,0))
end_location = start_location.lerp(target, amount)
scene.frame_set(1)
camera.location = start_location
camera.rotation_euler = start_rotation
camera.keyframe_insert(data_path='location', frame=1)
camera.keyframe_insert(data_path='rotation_euler', frame=1)
scene.frame_set(args.frames)
camera.location = end_location
look_at(camera, target)
camera.keyframe_insert(data_path='location', frame=args.frames)
camera.keyframe_insert(data_path='rotation_euler', frame=args.frames)

route_geo = []
route = ROUTES[args.name]
for index in range(len(route)-1):
    _, lon0, lat0 = route[index]
    _, lon1, lat1 = route[index+1]
    for step in range(24):
        t = step/24
        route_geo.append((lon0*(1-t)+lon1*t,lat0*(1-t)+lat1*t))
route_geo.append((route[-1][1],route[-1][2]))
label_geo = [(label,lon,lat) for label,lon,lat in route if label in LABELS[args.name]]
output = {'width':1280,'height':720,'frames':{}}
for frame in range(1,args.frames+1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    data = {'labels':{},'route':[]}
    for label,lon,lat in label_geo:
        p = world_to_camera_view(scene,camera,geo_to_scene(lon,lat))
        data['labels'][label] = [round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
    for lon,lat in route_geo:
        p = world_to_camera_view(scene,camera,geo_to_scene(lon,lat,.16))
        data['route'].append([round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)])
    output['frames'][str(frame)] = data

path = root/'opening'/'projections'/f"{args.name}.json"
path.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
print(f'PROJECTED {args.name}: {path}')
