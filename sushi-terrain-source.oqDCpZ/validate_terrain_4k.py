import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

# The generated national mosaic is 592,445,440 pixels. Keep a finite ceiling
# just above that known size rather than disabling Pillow's safety check.
Image.MAX_IMAGE_PIXELS = 600_000_000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terrain-dir', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    root = Path(args.terrain_dir)
    metadata = json.loads((root / 'china-metadata.json').read_text())
    x0, y0, x1, y1 = metadata['tiles']
    expected_width = (x1 - x0 + 1) * 256
    expected_height = (y1 - y0 + 1) * 256
    elevation = np.load(root / 'china-elevation.npy', mmap_mode='r')
    satellite = Image.open(root / 'china-satellite.jpg')
    satellite_size = list(satellite.size)
    satellite.verify()

    errors = []
    required_tiles = [352, 160, 463, 239]
    if not (x0 <= required_tiles[0] and y0 <= required_tiles[1]
            and x1 >= required_tiles[2] and y1 >= required_tiles[3]):
        errors.append(f'Tile coverage {metadata["tiles"]} does not cover the original national scene')
    if list(elevation.shape) != [expected_height, expected_width]:
        errors.append(f'DEM shape {elevation.shape} != {(expected_height, expected_width)}')
    if satellite_size != [expected_width, expected_height]:
        errors.append(f'Satellite size {satellite_size} != {[expected_width, expected_height]}')

    tile_count = (x1 - x0 + 1) * (y1 - y0 + 1)
    checked = {'dem': 0, 'imagery': 0}
    for kind, directory, suffix in [('dem', 'china-dem', 'png'), ('imagery', 'china-imagery', 'jpg')]:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                path = root / directory / f"{metadata['zoom']}-{x}-{y}.{suffix}"
                try:
                    with Image.open(path) as tile:
                        if tile.size != (256, 256):
                            raise ValueError(f'Unexpected tile size {tile.size}')
                        tile.verify()
                    checked[kind] += 1
                except Exception as exc:
                    errors.append(f'{path.name}: {exc}')

    finite = True
    minimum = float('inf')
    maximum = float('-inf')
    for row in range(0, elevation.shape[0], 256):
        block = np.asarray(elevation[row:row + 256])
        finite = finite and bool(np.isfinite(block).all())
        minimum = min(minimum, float(block.min()))
        maximum = max(maximum, float(block.max()))
    if not finite:
        errors.append('DEM contains non-finite values')
    if maximum > 9000:
        errors.append(f'DEM contains implausible elevations above 9000m: {maximum}')

    report = {
        'source': str(root),
        'zoom': metadata['zoom'],
        'geographic_bounds': metadata['bounds'],
        'expected_tiles_each': tile_count,
        'checked_tiles': checked,
        'dem_shape': list(elevation.shape),
        'satellite_size': satellite_size,
        'dem_dtype': str(elevation.dtype),
        'dem_min_m': minimum,
        'dem_max_m': maximum,
        'finite_dem': finite,
        'error_count': len(errors),
        'errors': errors[:100],
        'passed': not errors and checked == {'dem': tile_count, 'imagery': tile_count},
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
