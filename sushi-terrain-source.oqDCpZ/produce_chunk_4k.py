import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)
    parser.add_argument('--blender', default='/Applications/Blender.app/Contents/MacOS/Blender')
    args = parser.parse_args()
    root = Path(args.root)
    scripts = Path(__file__).resolve().parent
    final = root / 'final-film'
    terrain = root / 'terrain-4k-z9'
    render = [
        args.blender, '-b', str(final / 'sushi-life-map-4k.blend'), '--python-exit-code', '1',
        '--python', str(scripts / 'render_final_map_4k.py'), '--',
        '--root', str(root), '--terrain-dir', str(terrain),
        '--start', str(args.start), '--end', str(args.end),
    ]
    compose = [
        sys.executable, '-I', str(scripts / 'compose_final_map.py'),
        '--root', str(root), '--projection-file', 'projection-4k.json',
        '--sources-name', '事实与来源-V4K.md', '--raw-dir', 'raw-4k',
        '--composed-dir', 'composed-4k', '--start', str(args.start), '--end', str(args.end),
        '--resume', '--follow',
    ]
    print(f'4K CHUNK START: {args.start}-{args.end}', flush=True)
    render_process = subprocess.Popen(render)
    compose_process = subprocess.Popen(compose)
    try:
        render_code = render_process.wait()
        if render_code:
            compose_process.terminate()
        compose_code = compose_process.wait()
    except BaseException:
        render_process.terminate()
        compose_process.terminate()
        raise
    if render_code or compose_code:
        raise RuntimeError(f'Chunk failed: render={render_code}, compose={compose_code}')
    print(f'4K CHUNK VERIFIED BY PROCESSES: {args.start}-{args.end}', flush=True)


if __name__ == '__main__':
    main()
