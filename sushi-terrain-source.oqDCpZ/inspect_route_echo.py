import bpy
from bpy_extras.object_utils import world_to_camera_view

scene = bpy.context.scene
head = bpy.data.objects['苏轼 | traveling light']
print('HEAD ACTION', head.animation_data.action if head.animation_data else None)
print('CAMERA ACTION', scene.camera.animation_data.action if scene.camera.animation_data else None)
action = head.animation_data.action
if hasattr(action,'fcurves'):
    for curve in action.fcurves:
        if curve.data_path == 'location':
            print('LOCATION CURVE',curve.array_index,'KEYS',len(curve.keyframe_points),
                  [(round(k.co.x,1),tuple(round(v,4) for v in k.co.y)) for k in []])
            print('KEYFRAMES',[(round(k.co.x,1),round(k.co.y,4)) for k in curve.keyframe_points if k.co.x <= 205])
else:
    print('ACTION HAS NO LEGACY FCURVES')
for frame in [1,120,160,165,166,170,172,173,178,183,185,189,190,192,193]:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    p = world_to_camera_view(scene,scene.camera,head.location)
    print('FRAME',frame,'HEAD',tuple(round(v,4) for v in head.location),
          'CAM',tuple(round(v,4) for v in scene.camera.location),
          'SCREEN',round(p.x*1280,2),round((1-p.y)*720,2),round(p.z,3),flush=True)
