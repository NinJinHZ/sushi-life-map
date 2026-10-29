import argparse
import concurrent.futures
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image


def fetch(job):
    z, x, y, directory = job
    path = directory / f'{z}-{x}-{y}.jpg'
    if path.exists() and path.stat().st_size > 1000:
        return
    url = f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
    request = urllib.request.Request(url, headers={'User-Agent': 'SuShiTerrainResearch/0.2'})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            temporary = path.with_suffix('.download')
            temporary.write_bytes(data)
            with Image.open(temporary) as image:
                image.verify()
            temporary.replace(path)
            return
        except Exception as error:
            last = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'Failed {url}: {last}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-metadata', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--zoom', type=int, default=8)
    args = parser.parse_args()
    source = json.loads(Path(args.source_metadata).read_text())
    old_z = source['zoom']
    scale = 2 ** (args.zoom - old_z)
    if scale < 1:
        raise ValueError('New zoom must not be lower than source zoom')
    x0, y0, x1, y1 = source['tiles']
    x0, y0, x1, y1 = x0 * scale, y0 * scale, (x1 + 1) * scale - 1, (y1 + 1) * scale - 1
    root = Path(args.out)
    if root.exists() and any(root.iterdir()):
        print('Resuming existing high-resolution imagery directory', flush=True)
    tiles = root / 'tiles'
    tiles.mkdir(parents=True, exist_ok=True)
    jobs = [(args.zoom, x, y, tiles) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for completed, _ in enumerate(pool.map(fetch, jobs), 1):
            if completed % 200 == 0:
                print(f'DOWNLOADED {completed}/{len(jobs)}', flush=True)
    width, height = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    texture = Image.new('RGB', (width, height))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            path = tiles / f'{args.zoom}-{x}-{y}.jpg'
            with Image.open(path) as tile:
                texture.paste(tile.convert('RGB'), ((x - x0) * 256, (y - y0) * 256))
    prefix = source.get('name', 'china')
    destination = root / f'{prefix}-satellite-z{args.zoom}.jpg'
    texture.save(destination, quality=95, subsampling=0)
    metadata = dict(source)
    metadata.update({'zoom': args.zoom, 'tiles': [x0, y0, x1, y1], 'size': [width, height]})
    (root / f'{prefix}-metadata-z{args.zoom}.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f'HIGH-RESOLUTION IMAGERY READY: {destination} {width}x{height}', flush=True)


if __name__ == '__main__':
    main()
