import argparse
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--proof', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
root = Path(args.root)
scene = bpy.context.scene
route = bpy.data.objects['眉山出蜀行迹 | approximate historical road']
route.data.bevel_depth = .009
material = bpy.data.materials['Warm gold route']
for node in material.node_tree.nodes:
    if node.type == 'EMISSION':
        node.inputs['Color'].default_value = (.78, .48, .16, 1)
        node.inputs['Strength'].default_value = 1.45
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 20
if args.proof:
    out = root / 'opening-v2' / 'archive-raw-proofs'
    out.mkdir(exist_ok=True)
    for frame in (132, 216, 288):
        scene.frame_set(frame)
        scene.render.filepath = str(out / f'raw-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
else:
    scene.frame_start = 120
    scene.frame_end = 288
    scene.frame_set(120)
    scene.render.filepath = str(root / 'opening-v2' / 'raw' / 'frame-')
    bpy.ops.render.render(animation=True)
print('ARCHIVAL ROUTE REFINEMENT COMPLETE', flush=True)
