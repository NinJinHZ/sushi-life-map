import argparse
import concurrent.futures
import io
import json
import math
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image


def lon_to_tile(lon, z):
    return int(math.floor((lon + 180.0) / 360.0 * (2 ** z)))


def lat_to_tile(lat, z):
    r = math.radians(lat)
    return int(math.floor((1.0 - math.asinh(math.tan(r)) / math.pi) / 2.0 * (2 ** z)))


def tile_to_lon(x, z):
    return x / (2 ** z) * 360.0 - 180.0


def tile_to_lat(y, z):
    n = math.pi - 2.0 * math.pi * y / (2 ** z)
    return math.degrees(math.atan(math.sinh(n)))


def fetch(url, path):
    if path.exists() and path.stat().st_size > 1000:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "SuShiTerrainResearch/0.1"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            path.write_bytes(data)
            return
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed {url}: {last}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--bounds", nargs=4, type=float, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = Path(args.out)
    dem_dir = root / f"{args.name}-dem"
    img_dir = root / f"{args.name}-imagery"
    dem_dir.mkdir(exist_ok=True)
    img_dir.mkdir(exist_ok=True)
    west, south, east, north = args.bounds
    z = args.z
    x0, x1 = lon_to_tile(west, z), lon_to_tile(east, z)
    y0, y1 = lat_to_tile(north, z), lat_to_tile(south, z)
    jobs = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            dem_path = dem_dir / f"{z}-{x}-{y}.png"
            img_path = img_dir / f"{z}-{x}-{y}.jpg"
            jobs.append((f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png", dem_path))
            jobs.append((f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", img_path))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda job: fetch(*job), jobs))

    width, height = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    texture = Image.new("RGB", (width, height))
    elevation = np.zeros((height, width), dtype=np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            px, py = (x - x0) * 256, (y - y0) * 256
            dem = np.asarray(Image.open(dem_dir / f"{z}-{x}-{y}.png").convert("RGB"), dtype=np.float32)
            elevation[py:py+256, px:px+256] = dem[:, :, 0] * 256.0 + dem[:, :, 1] + dem[:, :, 2] / 256.0 - 32768.0
            tile = Image.open(img_dir / f"{z}-{x}-{y}.jpg").convert("RGB")
            texture.paste(tile, (px, py))

    texture.save(root / f"{args.name}-satellite.jpg", quality=94)
    np.save(root / f"{args.name}-elevation.npy", elevation)
    metadata = {
        "name": args.name,
        "zoom": z,
        "tiles": [x0, y0, x1, y1],
        "bounds": [tile_to_lon(x0, z), tile_to_lat(y1 + 1, z), tile_to_lon(x1 + 1, z), tile_to_lat(y0, z)],
        "requested_bounds": args.bounds,
        "size": [width, height],
        "elevation_min": float(elevation.min()),
        "elevation_max": float(elevation.max()),
        "sources": {
            "elevation": "Mapzen elevation tiles, Terrarium encoding, AWS elevation-tiles-prod",
            "imagery": "Esri World Imagery"
        }
    }
    (root / f"{args.name}-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
