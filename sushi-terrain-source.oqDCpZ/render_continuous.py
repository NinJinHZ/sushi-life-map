import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

R=6378137.0
WAYPOINTS=[('眉山',103.848,30.075),('成都',104.066,30.573),('剑门关',105.565,32.207),('广元',105.844,32.435),('汉中',107.023,33.067)]
parser=argparse.ArgumentParser()
parser.add_argument('--root',required=True)
parser.add_argument('--proof',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(args.root)
out=root/'opening-v2'
meta=json.loads((root/'sichuan-metadata.json').read_text())
elevation=np.load(root/'sichuan-elevation.npy')
rows,cols=elevation.shape
z=meta['zoom'];tx0,ty0=meta['tiles'][0],meta['tiles'][1]
world_pixels=256*(2**z)
mpp=2*math.pi*R/world_pixels
mpu=50000;exagg=6


def geo_pixel(lon,lat):
    return ((lon+180)/360*world_pixels-tx0*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*world_pixels-ty0*256)


def height(px,py):
    px=min(max(px,0),cols-1.001);py=min(max(py,0),rows-1.001)
    x0,y0=int(px),int(py);dx,dy=px-x0,py-y0
    h=elevation[y0,x0]*(1-dx)*(1-dy)+elevation[y0,x0+1]*dx*(1-dy)+elevation[y0+1,x0]*(1-dx)*dy+elevation[y0+1,x0+1]*dx*dy
    return max(float(h),0)/mpu*exagg


def geo(lon,lat,lift=.10):
    px,py=geo_pixel(lon,lat)
    return Vector(((px-(cols-1)/2)*mpp/mpu,((rows-1)/2-py)*mpp/mpu,height(px,py)+lift))


P={name:geo(lon,lat) for name,lon,lat in WAYPOINTS}
route_geo=[]
for i in range(len(WAYPOINTS)-1):
    _,a,b=WAYPOINTS[i];_,c,d=WAYPOINTS[i+1]
    for j in range(24):
        t=j/24;route_geo.append((a*(1-t)+c*t,b*(1-t)+d*t))
route_geo.append((WAYPOINTS[-1][1],WAYPOINTS[-1][2]))
route_scene=[geo(lon,lat,.12) for lon,lat in route_geo]

scene=bpy.context.scene
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.fps=24;scene.frame_start=1;scene.frame_end=288
if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=24
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.compression=20
scene.view_settings.exposure=.2
camera=scene.camera
camera.data.lens=50

route=bpy.data.objects.get('眉山出蜀行迹 | approximate historical road')
route.data.bevel_depth=.018
route.data.bevel_factor_end=0
route.data.keyframe_insert(data_path='bevel_factor_end',frame=1)
route.data.keyframe_insert(data_path='bevel_factor_end',frame=120)
route.data.bevel_factor_end=1
route.data.keyframe_insert(data_path='bevel_factor_end',frame=264)
route.data.keyframe_insert(data_path='bevel_factor_end',frame=288)

# A bright head travels with the growing route; the companions are composited later.
gold=bpy.data.materials.get('Warm gold route')
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.095,location=P['眉山'])
head=bpy.context.object;head.name='苏轼 | traveling light';head.data.materials.append(gold)
for frame in range(1,289,3):
    if frame<120:
        co=P['眉山'];scale=1
    else:
        progress=min(1,(frame-120)/144)
        pos=progress*(len(route_scene)-1);idx=min(int(pos),len(route_scene)-2);t=pos-idx
        co=route_scene[idx].lerp(route_scene[idx+1],t);scale=1
    head.location=co;head.scale=(scale,scale,scale)
    head.keyframe_insert(data_path='location',frame=frame)
head.location=P['眉山'];head.keyframe_insert(data_path='location',frame=1)

arrivals={}
for i,(name,lon,lat) in enumerate(WAYPOINTS):
    if name=='眉山':
        arrivals[name]=1
        continue
    arrival=120+round(i*24/(len(route_scene)-1)*144)
    arrivals[name]=arrival
    marker=bpy.data.objects.get(name)
    if marker is None:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=.075,location=P[name])
        marker=bpy.context.object;marker.name=name;marker.data.materials.append(gold)
    marker.scale=(.001,.001,.001);marker.keyframe_insert(data_path='scale',frame=1);marker.keyframe_insert(data_path='scale',frame=max(1,arrival-8))
    marker.scale=(1.15,1.15,1.15);marker.keyframe_insert(data_path='scale',frame=arrival)
    marker.scale=(1,1,1);marker.keyframe_insert(data_path='scale',frame=arrival+6)

mid=sum(P.values(),Vector())/len(P)
# The camera follows the moving head during travel, then opens to a full-route view.
for frame in range(120,265,8):
    progress=min(1,(frame-120)/144)
    pos=progress*(len(route_scene)-1);idx=min(int(pos),len(route_scene)-2);t=pos-idx
    current=route_scene[idx].lerp(route_scene[idx+1],t)
    ahead=route_scene[min(idx+8,len(route_scene)-1)]
    offset=Vector((2.8+3.0*progress,-4.2-5.0*progress,3.8+4.0*progress))
    target=current.lerp(ahead,.32)
    scene.frame_set(frame);camera.location=current+offset
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.keyframe_insert(data_path='location',frame=frame);camera.keyframe_insert(data_path='rotation_euler',frame=frame)
for frame,loc,target in [
    (1,P['眉山']+Vector((1.2,-1.8,1.6)),P['眉山']),
    (72,P['眉山']+Vector((1.8,-2.8,2.4)),P['眉山'].lerp(P['成都'],.12)),
    (120,P['眉山']+Vector((2.8,-4.2,3.8)),P['眉山'].lerp(P['成都'],.5)),
    (288,mid+Vector((0,-12,14)),mid),
]:
    scene.frame_set(frame);camera.location=loc
    camera.rotation_euler=(target-loc).to_track_quat('-Z','Y').to_euler()
    camera.keyframe_insert(data_path='location',frame=frame);camera.keyframe_insert(data_path='rotation_euler',frame=frame)
for frame,lens in [(1,50),(264,50),(288,45)]:
    camera.data.lens=lens;camera.data.keyframe_insert(data_path='lens',frame=frame)

# Screen-space lights are added in post so their size and glow stay consistent.
head.hide_render=True
for name in P:
    marker=bpy.data.objects.get(name)
    if marker:marker.hide_render=True

sun=bpy.data.objects.get('Late afternoon relief light')
if sun:
    for frame,energy in [(1,1.25),(120,1.7),(220,2.2),(288,1.9)]:
        sun.data.energy=energy;sun.data.keyframe_insert(data_path='energy',frame=frame)
world=scene.world
if world and world.use_nodes:
    bg=world.node_tree.nodes.get('Background')
    for frame,strength in [(1,.28),(120,.38),(220,.5),(288,.42)]:
        bg.inputs['Strength'].default_value=strength;bg.inputs['Strength'].keyframe_insert(data_path='default_value',frame=frame)

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'sichuan-continuous.blend'))
projection={'width':1280,'height':720,'arrivals':arrivals,'frames':{}}
for frame in range(1,289):
    scene.frame_set(frame);bpy.context.view_layer.update()
    item={'labels':{},'head':[]}
    for name in P:
        p=world_to_camera_view(scene,camera,P[name])
        item['labels'][name]=[round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
    p=world_to_camera_view(scene,camera,head.location)
    item['head']=[round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3)]
    projection['frames'][str(frame)]=item
(out/'projection.json').write_text(json.dumps(projection,ensure_ascii=False,separators=(',',':')))

if args.proof:
    for frame in [1,72,132,216,288]:
        scene.frame_set(frame);scene.render.filepath=str(out/'proofs'/f'raw-{frame:04d}.png');bpy.ops.render.render(write_still=True)
else:
    scene.frame_set(1);scene.render.filepath=str(out/'raw'/'frame-');bpy.ops.render.render(animation=True)
print('CONTINUOUS SCENE COMPLETE', 'PROOF' if args.proof else 'ANIMATION')
