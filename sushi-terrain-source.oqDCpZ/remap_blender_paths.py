import argparse
import sys
from pathlib import Path

import bpy


OLD_DOWNLOADS = Path.home() / 'Downloads'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    project = Path(args.project_root)
    replacements = {
        str(OLD_DOWNLOADS / 'sushi-terrain-test.ynv3ob'): str(project / 'sushi-terrain-test.ynv3ob'),
        str(OLD_DOWNLOADS / 'sushi-terrain-source.oqDCpZ'): str(project / 'sushi-terrain-source.oqDCpZ'),
        str(OLD_DOWNLOADS / 'sushi-map-keyframes.RwTxdn'): str(project / 'sushi-map-keyframes.RwTxdn'),
    }
    changed = []

    def remap(owner):
        path = getattr(owner, 'filepath', '')
        if not path:
            return
        for old, new in replacements.items():
            if path == old or path.startswith(old + '/'):
                owner.filepath = new + path[len(old):]
                changed.append((path, owner.filepath))
                return

    for group_name in ('images', 'fonts', 'sounds', 'libraries', 'cache_files', 'volumes', 'movieclips'):
        for owner in getattr(bpy.data, group_name, []):
            remap(owner)
    for scene in bpy.data.scenes:
        remap(scene.render)

    if changed:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(f'REMAPPED {bpy.data.filepath}: {len(changed)} paths', flush=True)
    for old, new in changed:
        print(f'  {old} -> {new}', flush=True)


if __name__ == '__main__':
    main()
