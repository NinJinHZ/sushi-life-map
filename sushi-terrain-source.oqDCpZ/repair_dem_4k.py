import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terrain-dir', required=True)
    parser.add_argument('--max-valid', type=float, default=9000)
    args = parser.parse_args()
    root = Path(args.terrain_dir)
    path = root / 'china-elevation.npy'
    elevation = np.load(path, mmap_mode='r+')
    repairs = []
    for row in range(0, elevation.shape[0], 256):
        block = np.asarray(elevation[row:row + 256])
        ys, xs = np.where(block > args.max_valid)
        for local_y, x in zip(ys, xs):
            y = row + int(local_y)
            x = int(x)
            original = float(elevation[y, x])
            neighborhood = np.asarray(elevation[max(0, y - 2):y + 3, max(0, x - 2):x + 3])
            valid = neighborhood[np.isfinite(neighborhood) & (neighborhood <= args.max_valid)]
            if not valid.size:
                raise RuntimeError(f'No valid neighbors for DEM pixel {(x, y)}')
            replacement = float(np.median(valid))
            elevation[y, x] = replacement
            repairs.append({'x': x, 'y': y, 'original_m': original, 'replacement_m': replacement})
    elevation.flush()

    minimum = float('inf')
    maximum = float('-inf')
    for row in range(0, elevation.shape[0], 256):
        block = np.asarray(elevation[row:row + 256])
        if not np.isfinite(block).all():
            raise RuntimeError('DEM contains non-finite values')
        minimum = min(minimum, float(block.min()))
        maximum = max(maximum, float(block.max()))
    metadata_path = root / 'china-metadata.json'
    metadata = json.loads(metadata_path.read_text())
    metadata['elevation_min'] = minimum
    metadata['elevation_max'] = maximum
    metadata['dem_repairs'] = len(repairs)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    report = {
        'source': str(path),
        'threshold_m': args.max_valid,
        'method': 'median of valid 5x5 neighborhood; raw downloaded tiles preserved',
        'repairs': repairs,
        'elevation_min': minimum,
        'elevation_max': maximum,
    }
    (root / 'dem-repair.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
