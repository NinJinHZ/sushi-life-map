import argparse
import json
from pathlib import Path


def contiguous(directory, prefix, suffix, total):
    count = 0
    for frame in range(1, total + 1):
        if not (directory / f'{prefix}-{frame:04d}.{suffix}').exists():
            break
        count = frame
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    final = root / 'final-film'
    opening = root / 'opening-v3' / 'direct-4k'
    report = {
        'raw_contiguous': contiguous(final / 'raw-4k', 'frame', 'png', 7320),
        'raw_total_files': len(list((final / 'raw-4k').glob('frame-*.png'))),
        'composed_contiguous': contiguous(final / 'composed-4k', 'frame', 'jpg', 7320),
        'composed_total_files': len(list((final / 'composed-4k').glob('frame-*.jpg'))),
        'opening_raw_contiguous': contiguous(opening / 'raw-4k', 'frame', 'png', 432),
        'opening_composed_contiguous': contiguous(opening / 'final', 'frame', 'jpg', 432),
        'opening_21s_contiguous': contiguous(opening / 'final-21s', 'frame', 'jpg', 504),
        'final_frames_contiguous': contiguous(final / 'final-frames-4k', 'frame', 'jpg', 7824),
        'targets': {'national': 7320, 'opening': 432, 'opening_total': 504, 'film': 7824},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
