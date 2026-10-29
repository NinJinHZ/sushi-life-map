import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--name', required=True)
parser.add_argument('--frames', type=int, default=48)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
root = Path(args.root)
scene = bpy.context.scene
camera = scene.camera
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = args.frames
if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 16
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 20

marker = bpy.data.objects.get('眉山')
target = marker.location.copy() if marker else Vector((0,0,0))
start_location = camera.location.copy()
start_rotation = camera.rotation_euler.copy()
amount = {'china': .20, 'sichuan': .30, 'meishan': .25}[args.name]
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

frames_dir = root / 'frames' / args.name
frames_dir.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(frames_dir / 'frame-')
scene.frame_set(1)
bpy.ops.render.render(animation=True)
print(f'ANIMATION COMPLETE: {args.name} {args.frames} frames')
