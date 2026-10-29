import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--video', required=True)
    parser.add_argument('--qa-dir', default='qa-video')
    args = parser.parse_args()
    root = Path(args.root)
    video = Path(args.video)
    out = root / 'final-film'
    qa = out / args.qa_dir
    qa.mkdir(exist_ok=True)
    probe = run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format',
                 '-of', 'json', str(video)], capture_output=True, text=True)
    (qa / 'ffprobe.json').write_text(probe.stdout)
    decode = run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'],
                 capture_output=True, text=True)
    (qa / 'decode-errors.txt').write_text(decode.stderr)
    if decode.stderr.strip():
        raise RuntimeError(f'Video decode reported errors: {decode.stderr}')
    loudness = run(['ffmpeg', '-hide_banner', '-i', str(video),
                    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
                    '-f', 'null', '-'], capture_output=True, text=True)
    (qa / 'loudness.txt').write_text(loudness.stderr)
    frames = qa / 'samples'
    frames.mkdir(exist_ok=True)
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video),
         '-vf', 'fps=1/20,scale=384:216', '-q:v', '2', str(frames / 'sample-%03d.jpg')])
    paths = sorted(frames.glob('sample-*.jpg'))
    font = ImageFont.truetype(ca.LATIN, 16)
    columns = 4
    cell_w, cell_h = 400, 254
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * cell_w, rows * cell_h), (7, 9, 6))
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        image = Image.open(path).convert('RGB')
        x, y = (i % columns) * cell_w, (i // columns) * cell_h
        sheet.paste(image, (x + 8, y + 30))
        draw.text((x + 10, y + 6), f'{i * 20:03d}s', font=font, fill=ca.PAPER)
    sheet.save(qa / 'full-film-sheet.jpg', quality=94, subsampling=0)
    report = {'decode_ok': True, 'sample_count': len(paths), 'video': str(video)}
    (qa / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
