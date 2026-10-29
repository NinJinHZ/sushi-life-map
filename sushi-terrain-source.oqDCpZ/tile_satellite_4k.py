import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = 600_000_000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terrain-dir', required=True)
    parser.add_argument('--cols', type=int, default=1800)
    parser.add_argument('--rows', type=int, default=1350)
    args = parser.parse_args()
    root = Path(args.terrain_dir)
    source_path = root / 'china-satellite.jpg'
    source = Image.open(source_path).convert('RGB')
    width, height = source.size
    xi = np.linspace(0, width - 1, args.cols).astype(np.int32)
    yi = np.linspace(0, height - 1, args.rows).astype(np.int32)
    split_x = int(xi[args.cols // 2])
    split_y = int(yi[args.rows // 2])
    boxes = {
        'x0-y0': (0, 0, split_x + 1, split_y + 1),
        'x1-y0': (split_x, 0, width, split_y + 1),
        'x0-y1': (0, split_y, split_x + 1, height),
        'x1-y1': (split_x, split_y, width, height),
    }
    out = root / 'satellite-tiles'
    out.mkdir(exist_ok=True)
    metadata = {
        'source': str(source_path),
        'source_size': [width, height],
        'mesh_grid': [args.cols, args.rows],
        'split_source_pixel': [split_x, split_y],
        'tiles': {},
    }
    for name, box in boxes.items():
        path = out / f'{name}.jpg'
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite existing texture tile: {path}')
        tile = source.crop(box)
        if max(tile.size) > 16384:
            raise ValueError(f'Texture tile exceeds GPU limit: {name} {tile.size}')
        tile.save(path, quality=96, subsampling=0)
        metadata['tiles'][name] = {'box': box, 'size': list(tile.size), 'path': str(path)}
        print(f'{name}: {box} {tile.size}', flush=True)
    (out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print('FOUR FULL-DETAIL SATELLITE TILES READY', flush=True)


if __name__ == '__main__':
    main()
