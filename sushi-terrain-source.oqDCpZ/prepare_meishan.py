import bpy
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'sushi-terrain-test.ynv3ob'
for obj in bpy.data.objects:
    if obj.name.startswith('眉山出蜀行迹') or obj.name == '成都':
        obj.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'meishan-opening.blend'))
